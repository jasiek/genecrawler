#!/usr/bin/env python3
"""
GeneCrawler - GEDCOM to Genealogical Database Query Tool

This script reads a GEDCOM file and queries multiple Polish genealogical databases
for information about each person in the file:
- Geneteka (geneteka.genealodzy.pl)
- PTG PomGenBaza (www.ptg.gda.pl)
- Poznan Project (poznan-project.psnc.pl)
- BaSIA (www.basia.famula.pl)
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import time
import random
import sqlite3

from ged4py import GedcomReader
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


@dataclass
class Person:
    """Represents a person from GEDCOM file"""
    id: str
    given_name: str
    surname: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    birth_place: Optional[str] = None
    death_place: Optional[str] = None
    birth_voivodeship: Optional[str] = None
    death_voivodeship: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None

    def has_polish_connection(self) -> bool:
        """Check if person has a connection to Poland

        Returns True if:
        - Person has a Polish voivodeship
        - Person has a place name mentioning Poland
        - Person has NO location information at all (assume Poland)
        """
        # If we have a voivodeship, they're definitely in Poland
        if self.birth_voivodeship or self.death_voivodeship:
            return True

        # Check if we have any location information at all
        has_any_location = bool(self.birth_place or self.death_place)

        # If no location information, assume Poland
        if not has_any_location:
            return True

        # If we have location info, check if it mentions Poland
        places = [self.birth_place, self.death_place]
        for place in places:
            if place:
                place_upper = place.upper()
                if 'POLAND' in place_upper or 'POLSKA' in place_upper or 'POL' in place_upper:
                    return True

        # We have location info but it doesn't mention Poland
        return False


@dataclass
class SearchResult:
    """Represents a search result from a genealogical database"""
    source: str
    found: bool
    record_count: int
    details: List[Dict]
    error: Optional[str] = None


class LocationParser:
    """Parses location information and extracts voivodeship"""

    # Mapping of voivodeship names in various formats to standardized names
    VOIVODESHIP_MAPPING = {
        # Polish names (various cases)
        'DOLNOŚLĄSKIE': 'dolnośląskie',
        'DOLNOSLASKIE': 'dolnośląskie',
        'LOWER SILESIAN VOIVODESHIP': 'dolnośląskie',
        'LOWER SILESIA': 'dolnośląskie',

        'KUJAWSKO-POMORSKIE': 'kujawsko-pomorskie',
        'KUYAVIAN-POMERANIAN VOIVODESHIP': 'kujawsko-pomorskie',
        'KUYAVIAN-POMERANIAN': 'kujawsko-pomorskie',

        'LUBELSKIE': 'lubelskie',
        'LUBLIN VOIVODESHIP': 'lubelskie',

        'LUBUSKIE': 'lubuskie',
        'LUBUSZ VOIVODESHIP': 'lubuskie',

        'ŁÓDZKIE': 'łódzkie',
        'ŁODZKIE': 'łódzkie',
        'LODZKIE': 'łódzkie',
        'LODZ VOIVODESHIP': 'łódzkie',

        'MAŁOPOLSKIE': 'małopolskie',
        'MAŁOPOLSKA': 'małopolskie',
        'MALOPOLSKIE': 'małopolskie',
        'MALOPOLSKA': 'małopolskie',
        'LESSER POLAND VOIVODESHIP': 'małopolskie',
        'LESSER POLAND': 'małopolskie',

        'MAZOWIECKIE': 'mazowieckie',
        'MASOVIAN VOIVODESHIP': 'mazowieckie',
        'MASOVIA': 'mazowieckie',

        'OPOLSKIE': 'opolskie',
        'OPOLE VOIVODESHIP': 'opolskie',

        'PODKARPACKIE': 'podkarpackie',
        'SUBCARPATHIAN VOIVODESHIP': 'podkarpackie',
        'SUBCARPATHIA': 'podkarpackie',

        'PODLASKIE': 'podlaskie',
        'PODLASIE': 'podlaskie',
        'PODLACHIA': 'podlaskie',

        'POMORSKIE': 'pomorskie',
        'POMERANIAN VOIVODESHIP': 'pomorskie',
        'POMERANIA': 'pomorskie',

        'ŚLĄSKIE': 'śląskie',
        'SLASKIE': 'śląskie',
        'SILESIAN VOIVODESHIP': 'śląskie',
        'SILESIA': 'śląskie',

        'ŚWIĘTOKRZYSKIE': 'świętokrzyskie',
        'SWIETOKRZYSKIE': 'świętokrzyskie',
        'HOLY CROSS VOIVODESHIP': 'świętokrzyskie',

        'WARMIŃSKO-MAZURSKIE': 'warmińsko-mazurskie',
        'WARMINSKO-MAZURSKIE': 'warmińsko-mazurskie',
        'WARMIAN-MASURIAN VOIVODESHIP': 'warmińsko-mazurskie',

        'WIELKOPOLSKIE': 'wielkopolskie',
        'GREATER POLAND VOIVODESHIP': 'wielkopolskie',
        'GREATER POLAND': 'wielkopolskie',

        'ZACHODNIOPOMORSKIE': 'zachodniopomorskie',
        'WEST POMERANIAN VOIVODESHIP': 'zachodniopomorskie',
        'WEST POMERANIA': 'zachodniopomorskie',
    }

    def __init__(self, use_nominatim: bool = False):
        """Initialize LocationParser

        Args:
            use_nominatim: If True, use Nominatim API as fallback for unknown locations
        """
        self.use_nominatim = use_nominatim
        self.geolocator = None
        if use_nominatim:
            self.geolocator = Nominatim(user_agent="genecrawler/0.1.0")
        self._cache = {}

        # Initialize SQLite database for Nominatim cache
        self.db_path = Path.home() / '.genecrawler' / 'nominatim_cache.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database and create cache table if needed"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nominatim_cache (
                query TEXT PRIMARY KEY,
                voivodeship TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def _get_cached_voivodeship(self, query: str) -> Optional[str]:
        """Get cached voivodeship from database

        Returns:
            The cached voivodeship (may be None if location not found),
            or a sentinel value '__NOT_CACHED__' if query not in cache
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('SELECT voivodeship FROM nominatim_cache WHERE query = ?', (query,))
        result = cursor.fetchone()
        conn.close()

        if result is None:
            return '__NOT_CACHED__'
        return result[0]  # May be None if location wasn't found

    def _set_cached_voivodeship(self, query: str, voivodeship: Optional[str]):
        """Store voivodeship in database cache"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO nominatim_cache (query, voivodeship)
            VALUES (?, ?)
        ''', (query, voivodeship))
        conn.commit()
        conn.close()

    def parse_voivodeship(self, place_str: Optional[str]) -> Optional[str]:
        """Parse voivodeship from GEDCOM place string

        Args:
            place_str: GEDCOM place string in format: Town, Area code, County, Region, Country, Subdivision

        Returns:
            Standardized voivodeship name or None
        """
        if not place_str:
            return None

        # Check cache first
        if place_str in self._cache:
            return self._cache[place_str]

        voivodeship = None

        # First try to extract from GEDCOM place format
        # Format: Town, Area code, County, Region, Country, Subdivision
        parts = [p.strip() for p in place_str.split(',')]

        # Region is usually at index 3
        if len(parts) > 3 and parts[3]:
            region = parts[3].upper()
            if region in self.VOIVODESHIP_MAPPING:
                voivodeship = self.VOIVODESHIP_MAPPING[region]

        # If not found and we have a town name (index 0), try Nominatim
        if not voivodeship and self.use_nominatim and len(parts) > 0 and parts[0]:
            voivodeship = self._query_nominatim(parts[0])

        # Cache result
        self._cache[place_str] = voivodeship
        return voivodeship

    def _query_nominatim(self, town: str) -> Optional[str]:
        """Query Nominatim for voivodeship information

        Args:
            town: Town name to query

        Returns:
            Standardized voivodeship name or None
        """
        if not self.geolocator:
            return None

        query = town

        # Check database cache first
        cached_result = self._get_cached_voivodeship(query)
        if cached_result != '__NOT_CACHED__':
            print(f"    Nominatim lookup: '{query}' (cached)")
            if cached_result:
                print(f"      → Found voivodeship: {cached_result}")
            else:
                print(f"      → Location not found (cached)")
            return cached_result

        try:
            print(f"    Nominatim lookup: '{query}'")
            location = self.geolocator.geocode(query, exactly_one=True, timeout=5)

            voivodeship = None
            if location and location.address:
                chunks = location.address.split(',')
                for c in chunks:
                    if 'województwo' in c:
                        voivodeship = c.split(' ')[1].strip()
                        break

                if voivodeship:
                    print(f"      → Found voivodeship: {voivodeship}")
                    # Store in cache
                    self._set_cached_voivodeship(query, voivodeship)
                    return voivodeship
                else:
                    print(f"      → Location found but no voivodeship in address")
            else:
                print(f"      → Location not found")

            # Store negative result in cache to avoid repeated lookups
            self._set_cached_voivodeship(query, None)

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"      → Nominatim timeout/service error: {e}")
            # Don't cache errors
        except Exception as e:
            # Log unexpected errors but continue
            print(f"      → Nominatim error: {e}")
            # Don't cache errors

        return None


class GedcomParser:
    """Parses GEDCOM files and extracts person information"""

    def __init__(self, gedcom_file: Path, use_nominatim: bool = False):
        self.gedcom_file = gedcom_file
        self.location_parser = LocationParser(use_nominatim=use_nominatim)

    def parse(self) -> List[Person]:
        """Parse GEDCOM file and return list of persons"""
        persons = []
        skipped_no_name = 0
        skipped_uncertain = 0

        try:
            with GedcomReader(str(self.gedcom_file)) as reader:
                for record in reader.records0('INDI'):
                    person, skip_reason = self._extract_person(record)
                    if person:
                        persons.append(person)
                    elif skip_reason == 'no_name':
                        skipped_no_name += 1
                    elif skip_reason == 'uncertain':
                        skipped_uncertain += 1
        except Exception as e:
            print(f"Error parsing GEDCOM file: {e}")
            sys.exit(1)

        if skipped_no_name > 0:
            print(f"Skipped {skipped_no_name} person(s) without names")
        if skipped_uncertain > 0:
            print(f"Skipped {skipped_uncertain} person(s) with uncertain names (containing '?')")

        return persons

    def _extract_person(self, record):
        """Extract person information from GEDCOM record

        Returns:
            Tuple of (Person, skip_reason) where Person is None if skipped,
            and skip_reason is 'no_name', 'uncertain', or None
        """
        try:
            # Get ID
            person_id = record.xref_id

            # Get name using GIVN and SURN sub-tags
            given_name = ""
            surname = ""

            name_records = record.sub_tags('NAME')
            if name_records:
                name_record = name_records[0]

                # Try to get GIVN (given name) sub-tag
                givn_tags = name_record.sub_tags('GIVN')
                if givn_tags:
                    given_name = givn_tags[0].value.strip()

                # Try to get SURN (surname) sub-tag
                surn_tags = name_record.sub_tags('SURN')
                if surn_tags:
                    surname = surn_tags[0].value.strip()

                # Fallback: parse NAME value if GIVN/SURN not available
                if not given_name and not surname and hasattr(name_record, 'value'):
                    full_name = name_record.value
                    # GEDCOM format: Given /Surname/
                    if '/' in full_name:
                        parts = full_name.split('/')
                        given_name = parts[0].strip()
                        surname = parts[1].strip() if len(parts) > 1 else ""
                    else:
                        given_name = full_name.strip()

            # Skip persons without at least a surname or given name
            if not surname and not given_name:
                return None, 'no_name'

            # Skip persons with uncertain names (containing "?")
            if '?' in given_name or '?' in surname:
                return None, 'uncertain'

            # Get birth info
            birth_year = None
            birth_place = None
            birth_voivodeship = None
            if record.sub_tags('BIRT'):
                birt = record.sub_tags('BIRT')[0]
                if birt.sub_tags('DATE'):
                    date_value = birt.sub_tags('DATE')[0].value
                    birth_year = self._extract_year(str(date_value))
                if birt.sub_tags('PLAC'):
                    birth_place = birt.sub_tags('PLAC')[0].value
                    birth_voivodeship = self.location_parser.parse_voivodeship(birth_place)

            # Get death info
            death_year = None
            death_place = None
            death_voivodeship = None
            if record.sub_tags('DEAT'):
                deat = record.sub_tags('DEAT')[0]
                if deat.sub_tags('DATE'):
                    date_value = deat.sub_tags('DATE')[0].value
                    death_year = self._extract_year(str(date_value))
                if deat.sub_tags('PLAC'):
                    death_place = deat.sub_tags('PLAC')[0].value
                    death_voivodeship = self.location_parser.parse_voivodeship(death_place)

            # Get parents info
            father_name = None
            mother_name = None
            if record.sub_tags('FAMC'):
                family_ref = record.sub_tags('FAMC')[0].value
                # Note: We'd need to resolve family references to get parent names
                # This is a simplified version

            return Person(
                id=person_id,
                given_name=given_name,
                surname=surname,
                birth_year=birth_year,
                death_year=death_year,
                birth_place=birth_place,
                death_place=death_place,
                birth_voivodeship=birth_voivodeship,
                death_voivodeship=death_voivodeship,
                father_name=father_name,
                mother_name=mother_name
            ), None
        except Exception as e:
            print(f"Error extracting person: {e}")
            return None, 'error'

    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from GEDCOM date string"""
        try:
            # GEDCOM dates can be in various formats
            # Try to extract 4-digit year
            import re
            match = re.search(r'\b(1\d{3}|20\d{2})\b', date_str)
            if match:
                return int(match.group(1))
        except Exception as e:
            pass
        return None


class GenetekaSearcher:
    """Searches geneteka.genealodzy.pl database"""

    BASE_URL = "https://geneteka.genealodzy.pl"

    # Mapping of standardized voivodeship names to Geneteka codes
    VOIVODESHIP_CODES = {
        'dolnośląskie': '01ds',
        'kujawsko-pomorskie': '02kp',
        'lubelskie': '03lb',
        'lubuskie': '04ls',
        'łódzkie': '05ld',
        'małopolskie': '06mp',
        'mazowieckie': '07mz',
        'opolskie': '08op',
        'podkarpackie': '09pk',
        'podlaskie': '10pl',
        'pomorskie': '11pm',
        'śląskie': '12sl',
        'świętokrzyskie': '13sk',
        'warmińsko-mazurskie': '14wm',
        'wielkopolskie': '15wp',
        'zachodniopomorskie': '16zp',
    }

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search Geneteka database for person"""
        print(f"  Searching Geneteka for {person.given_name} {person.surname}...")

        all_results = []

        # Determine which voivodeships to search
        voivodeship = person.birth_voivodeship or person.death_voivodeship
        if voivodeship and voivodeship in self.VOIVODESHIP_CODES:
            # Search only the identified voivodeship
            voivodeships_to_search = [(voivodeship, self.VOIVODESHIP_CODES[voivodeship])]
            print(f"  Searching in voivodeship: {voivodeship}")
        else:
            # Search all voivodeships
            voivodeships_to_search = list(self.VOIVODESHIP_CODES.items())
            print(f"  No voivodeship identified - searching all {len(voivodeships_to_search)} voivodeships")

        # Search for births, marriages, and deaths
        # Map BDM types to table IDs used in Geneteka results
        record_types = [
            ('B', 'births', 'table_b', person.birth_year, -5, 5),
            ('M', 'marriages', 'table_s', person.birth_year + 25 if person.birth_year else None, -10, 10),
            ('D', 'deaths', 'table_d', person.death_year, -5, 5)
        ]

        for bdm_type, type_name, table_id, base_year, year_before, year_after in record_types:
            print(f"    Searching {type_name}...")

            for voivodeship_name, voivodeship_code in voivodeships_to_search:
                try:
                    # Navigate to main search page
                    page.goto(f"{self.BASE_URL}/index.php?op=gt&lang=pol", timeout=30000)
                    page.wait_for_load_state('domcontentloaded')

                    # Set the BDM (birth/marriage/death) parameter
                    page.evaluate(f"document.querySelector('input[name=\"bdm\"]').value = '{bdm_type}'")

                    # Select voivodeship
                    page.select_option('select[name="w"]', voivodeship_code)

                    # Fill in surname
                    if person.surname:
                        page.fill('input[name="search_lastname"]', person.surname)

                    # Fill in given name
                    if person.given_name:
                        page.fill('input[name="search_name"]', person.given_name)

                    # Fill in date range if available
                    from_year = None
                    to_year = None
                    if base_year:
                        from_year = base_year + year_before
                        to_year = base_year + year_after
                        page.fill('input[name="from_date"]', str(from_year))
                        page.fill('input[name="to_date"]', str(to_year))

                    # Print search parameters
                    print(f"      Parameters: bdm={bdm_type}, voivodeship={voivodeship_code} ({voivodeship_name}), "
                          f"surname={person.surname or 'any'}, given_name={person.given_name or 'any'}, "
                          f"years={from_year or 'any'}-{to_year or 'any'}")

                    # Submit form
                    page.click('input[type="submit"]')
                    page.wait_for_load_state('networkidle', timeout=30000)

                    # Parse results
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Look for result table with specific ID and class
                    result_table = soup.find('table', {'id': table_id, 'class': 'tablesearch'})
                    if result_table:
                        rows = result_table.find_all('tr')[1:]  # Skip header
                        row_count = 0
                        for row in rows:
                            cols = row.find_all('td')

                            # Parse based on record type (different table structures)
                            if bdm_type == 'B' and len(cols) >= 10:
                                # Birth table: Rok, Akt, Imię, Nazwisko, Imię ojca, Imię matki,
                                #              Nazwisko matki, Parafia, Miejscowość, Uwagi
                                scan_link = None
                                if cols[9].find('a', href=True):
                                    for link in cols[9].find_all('a', href=True):
                                        if 'skanoteka' in link['href'] or 'doc' in link.get('target', ''):
                                            scan_link = link['href']
                                            break

                                result = {
                                    'type': type_name,
                                    'voivodeship': voivodeship_name,
                                    'year': cols[0].text.strip(),
                                    'act': cols[1].text.strip(),
                                    'given_name': cols[2].text.strip(),
                                    'surname': cols[3].text.strip(),
                                    'father_given_name': cols[4].text.strip(),
                                    'mother_given_name': cols[5].text.strip(),
                                    'mother_surname': cols[6].text.strip(),
                                    'parish': cols[7].text.strip(),
                                    'locality': cols[8].text.strip(),
                                    'link': scan_link
                                }
                                all_results.append(result)
                                row_count += 1

                            elif (bdm_type == 'M' or bdm_type == 'D') and len(cols) >= 5:
                                # TODO: Marriage and death tables have different structures
                                # For now, use a generic parser
                                result = {
                                    'type': type_name,
                                    'voivodeship': voivodeship_name,
                                    'data': ', '.join([col.text.strip() for col in cols[:5]])
                                }
                                all_results.append(result)
                                row_count += 1

                        if row_count > 0:
                            print(f"      → Found {row_count} result(s) in table {table_id}")

                    # Small delay between searches
                    time.sleep(1)

                except Exception as e:
                    print(f"      Error searching {voivodeship_name}: {e}")

        return SearchResult(
            source="Geneteka",
            found=len(all_results) > 0,
            record_count=len(all_results),
            details=all_results
        )


class PTGSearcher:
    """Searches PTG PomGenBaza database"""

    BASE_URL = "https://www.ptg.gda.pl/language/pl/pomgenbaza/przeszukiwanie-rejestrow-metrykalnych/"

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search PTG database for person"""
        print(f"  Searching PTG PomGenBaza for {person.given_name} {person.surname}...")

        try:
            page.goto(self.BASE_URL, timeout=30000)
            page.wait_for_load_state('networkidle')

            # Fill in search form
            if person.given_name:
                page.fill('input[name="mim"]', person.given_name)

            if person.surname:
                page.fill('input[name="mnz"]', person.surname)

            # Fill in date range if available
            if person.birth_year:
                page.fill('input[name="ode"]', str(person.birth_year - 5))
                page.fill('input[name="doe"]', str(person.birth_year + 5))

            # Submit search
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=30000)

            # Parse results
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for results
            results = []
            result_div = soup.find('div', {'id': 'ptgSearchResults'})
            if result_div:
                rows = result_div.find_all('div', {'class': 'ptg-search-row'})
                for row in rows:
                    result = {
                        'name': row.find('span', {'class': 'name'}).text.strip() if row.find('span', {'class': 'name'}) else '',
                        'year': row.find('span', {'class': 'year'}).text.strip() if row.find('span', {'class': 'year'}) else '',
                        'parish': row.find('span', {'class': 'parish'}).text.strip() if row.find('span', {'class': 'parish'}) else ''
                    }
                    results.append(result)

            return SearchResult(
                source="PTG PomGenBaza",
                found=len(results) > 0,
                record_count=len(results),
                details=results
            )

        except Exception as e:
            return SearchResult(
                source="PTG PomGenBaza",
                found=False,
                record_count=0,
                details=[],
                error=str(e)
            )


class PoznanProjectSearcher:
    """Searches Poznan Project database"""

    BASE_URL = "https://poznan-project.psnc.pl"

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search Poznan Project database for person"""
        print(f"  Searching Poznan Project for {person.given_name} {person.surname}...")

        try:
            page.goto(self.BASE_URL, timeout=30000)
            page.wait_for_load_state('networkidle')

            # Click on extended search
            page.click('a[href="#extendedsearch"]')
            time.sleep(1)

            # Fill in search form
            if person.surname:
                page.fill('input[name="surname"]', person.surname)

            if person.given_name:
                # Groom or bride name
                page.fill('input[name="firstname1"]', person.given_name)

            # Set year range if available
            if person.birth_year:
                # For marriage records, estimate marriage year
                marriage_year = person.birth_year + 25
                page.fill('input[name="yearfrom"]', str(marriage_year - 10))
                page.fill('input[name="yearto"]', str(marriage_year + 10))

            # Submit search
            page.click('button#searchextended')
            page.wait_for_load_state('networkidle', timeout=30000)

            # Parse results
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for results table
            results = []
            result_table = soup.find('table', {'id': 'results'})
            if result_table:
                rows = result_table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        result = {
                            'groom': cols[0].text.strip(),
                            'bride': cols[1].text.strip(),
                            'year': cols[2].text.strip(),
                            'parish': cols[3].text.strip()
                        }
                        results.append(result)

            return SearchResult(
                source="Poznan Project",
                found=len(results) > 0,
                record_count=len(results),
                details=results
            )

        except Exception as e:
            return SearchResult(
                source="Poznan Project",
                found=False,
                record_count=0,
                details=[],
                error=str(e)
            )


class BaSIASearcher:
    """Searches BaSIA database"""

    BASE_URL = "https://www.basia.famula.pl/en/"

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search BaSIA database for person"""
        print(f"  Searching BaSIA for {person.given_name} {person.surname}...")

        try:
            page.goto(self.BASE_URL, timeout=30000)
            page.wait_for_load_state('networkidle')

            # Fill in search form
            if person.given_name:
                page.fill('input[name="firstname"]', person.given_name)

            if person.surname:
                page.fill('input[name="lastname"]', person.surname)

            # Set year range if available
            if person.birth_year:
                page.fill('input[name="yearfrom"]', str(person.birth_year - 5))
                page.fill('input[name="yearto"]', str(person.birth_year + 5))

            # Submit search
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=30000)

            # Parse results
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for results
            results = []
            result_table = soup.find('table', {'class': 'results'})
            if result_table:
                rows = result_table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        result = {
                            'name': cols[0].text.strip(),
                            'year': cols[1].text.strip(),
                            'place': cols[2].text.strip(),
                            'document_type': cols[3].text.strip()
                        }
                        results.append(result)

            return SearchResult(
                source="BaSIA",
                found=len(results) > 0,
                record_count=len(results),
                details=results
            )

        except Exception as e:
            return SearchResult(
                source="BaSIA",
                found=False,
                record_count=0,
                details=[],
                error=str(e)
            )


def print_person_info(person: Person):
    """Print person information"""
    print(f"\n{'='*80}")
    print(f"Person: {person.given_name} {person.surname} (ID: {person.id})")
    if person.birth_year:
        birth_info = f"Birth: {person.birth_year}"
        if person.birth_place:
            birth_info += f" in {person.birth_place}"
        if person.birth_voivodeship:
            birth_info += f" [{person.birth_voivodeship}]"
        print(birth_info)
    if person.death_year:
        death_info = f"Death: {person.death_year}"
        if person.death_place:
            death_info += f" in {person.death_place}"
        if person.death_voivodeship:
            death_info += f" [{person.death_voivodeship}]"
        print(death_info)
    print(f"{'='*80}")


def print_search_results(result: SearchResult):
    """Print search results"""
    print(f"\n{result.source}:")
    if result.error:
        print(f"  Error: {result.error}")
    elif result.found:
        print(f"  Found {result.record_count} record(s):")
        for i, detail in enumerate(result.details[:5], 1):  # Show max 5 results
            print(f"    {i}. ", end="")
            print(", ".join([f"{k}: {v}" for k, v in detail.items() if v]))
        if result.record_count > 5:
            print(f"    ... and {result.record_count - 5} more")
    else:
        print(f"  No records found")


def main():
    parser = argparse.ArgumentParser(
        description="Query Polish genealogical databases for persons in a GEDCOM file"
    )
    parser.add_argument("gedcom_file", type=Path, help="Path to GEDCOM file")
    parser.add_argument("--no-headless", action="store_false", dest="headless",
                       help="Run browser with visible UI (default: headless mode)")
    parser.add_argument("--limit", type=int, help="Limit number of persons to process")
    parser.add_argument("--databases", nargs="+",
                       choices=["geneteka", "ptg", "poznan", "basia", "all"],
                       default=["all"],
                       help="Which databases to query (default: all)")
    parser.add_argument("--use-nominatim", action="store_true",
                       help="Use Nominatim API for geocoding unknown locations (slower)")
    parser.add_argument("--random", action="store_true",
                       help="Randomize the order of persons to process (default: oldest first)")
    parser.add_argument("--gedcom-record", type=str,
                       help="Search only for a specific GEDCOM record by ID (e.g., 7335288 or @7335288@)")

    args = parser.parse_args()

    # Check if GEDCOM file exists
    if not args.gedcom_file.exists():
        print(f"Error: GEDCOM file not found: {args.gedcom_file}")
        sys.exit(1)

    # Parse GEDCOM file
    print(f"Parsing GEDCOM file: {args.gedcom_file}")
    gedcom_parser = GedcomParser(args.gedcom_file, use_nominatim=args.use_nominatim)
    persons = gedcom_parser.parse()
    print(f"Found {len(persons)} persons in GEDCOM file")

    # Filter for specific record if requested
    if args.gedcom_record:
        # Normalize the ID - accept both "7335288" and "@7335288@" formats
        target_id = args.gedcom_record
        if not target_id.startswith('@'):
            target_id = f"@{target_id}"
        if not target_id.endswith('@'):
            target_id = f"{target_id}@"

        matching_persons = [p for p in persons if p.id == target_id]
        if not matching_persons:
            print(f"Error: No person found with ID {target_id}")
            sys.exit(1)

        persons = matching_persons
        print(f"Filtered to specific record: {target_id}")

    # Show voivodeship statistics
    with_voivodeship = [p for p in persons if p.birth_voivodeship is not None]
    if with_voivodeship:
        print(f"Parsed voivodeships for {len(with_voivodeship)} persons")

    # Show Polish connection statistics
    with_polish_connection = [p for p in persons if p.has_polish_connection()]
    print(f"Found {len(with_polish_connection)} persons with Polish connections")

    # Sort or randomize persons (skip if specific record requested)
    if not args.gedcom_record:
        if args.random:
            random.shuffle(persons)
            print(f"Randomized order of persons")
        else:
            # Sort persons by birth year (oldest first), putting those without birth years at the end
            persons.sort(key=lambda p: (p.birth_year is None, p.birth_year or 9999))
            print(f"Sorted persons by birth year (oldest first)")

        if args.limit:
            persons = persons[:args.limit]
            print(f"Limiting to first {args.limit} persons")

    # Determine which databases to search
    databases = args.databases
    if "all" in databases:
        databases = ["geneteka", "ptg", "poznan", "basia"]

    # Initialize searchers
    searchers = {}
    if "geneteka" in databases:
        searchers["geneteka"] = GenetekaSearcher()
    if "ptg" in databases:
        searchers["ptg"] = PTGSearcher()
    if "poznan" in databases:
        searchers["poznan"] = PoznanProjectSearcher()
    if "basia" in databases:
        searchers["basia"] = BaSIASearcher()

    # Search databases
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()

        for person in persons:
            print_person_info(person)

            # Search each database
            if "geneteka" in searchers:
                # Geneteka only works for Poland
                if person.has_polish_connection():
                    result = searchers["geneteka"].search(page, person)
                    print_search_results(result)
                else:
                    print("\nGeneteka:")
                    print("  Skipped (no Polish connection)")

            if "ptg" in searchers:
                result = searchers["ptg"].search(page, person)
                print_search_results(result)

            if "poznan" in searchers:
                result = searchers["poznan"].search(page, person)
                print_search_results(result)

            if "basia" in searchers:
                result = searchers["basia"].search(page, person)
                print_search_results(result)

            # Add a small delay between persons to be respectful to servers
            time.sleep(2)

        browser.close()

    print(f"\n{'='*80}")
    print("Search complete!")


if __name__ == "__main__":
    main()
