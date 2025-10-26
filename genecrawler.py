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

from ged4py import GedcomReader
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup


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
    father_name: Optional[str] = None
    mother_name: Optional[str] = None


@dataclass
class SearchResult:
    """Represents a search result from a genealogical database"""
    source: str
    found: bool
    record_count: int
    details: List[Dict]
    error: Optional[str] = None


class GedcomParser:
    """Parses GEDCOM files and extracts person information"""

    def __init__(self, gedcom_file: Path):
        self.gedcom_file = gedcom_file

    def parse(self) -> List[Person]:
        """Parse GEDCOM file and return list of persons"""
        persons = []
        skipped = 0

        try:
            with GedcomReader(str(self.gedcom_file)) as reader:
                for record in reader.records0('INDI'):
                    person = self._extract_person(record)
                    if person:
                        persons.append(person)
                    else:
                        skipped += 1
        except Exception as e:
            print(f"Error parsing GEDCOM file: {e}")
            sys.exit(1)

        if skipped > 0:
            print(f"Skipped {skipped} person(s) without names")

        return persons

    def _extract_person(self, record) -> Optional[Person]:
        """Extract person information from GEDCOM record"""
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
                return None

            # Get birth info
            birth_year = None
            birth_place = None
            if record.sub_tags('BIRT'):
                birt = record.sub_tags('BIRT')[0]
                if birt.sub_tags('DATE'):
                    date_value = birt.sub_tags('DATE')[0].value
                    birth_year = self._extract_year(str(date_value))
                if birt.sub_tags('PLAC'):
                    birth_place = birt.sub_tags('PLAC')[0].value

            # Get death info
            death_year = None
            death_place = None
            if record.sub_tags('DEAT'):
                deat = record.sub_tags('DEAT')[0]
                if deat.sub_tags('DATE'):
                    date_value = deat.sub_tags('DATE')[0].value
                    death_year = self._extract_year(str(date_value))
                if deat.sub_tags('PLAC'):
                    death_place = deat.sub_tags('PLAC')[0].value

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
                father_name=father_name,
                mother_name=mother_name
            )
        except Exception as e:
            print(f"Error extracting person: {e}")
            return None

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

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search Geneteka database for person"""
        print(f"  Searching Geneteka for {person.given_name} {person.surname}...")

        try:
            # Navigate to main search page
            page.goto(f"{self.BASE_URL}/index.php?op=gt&lang=pol", timeout=30000)
            page.wait_for_load_state('networkidle')

            # Fill in search form
            # Select birth records (B) if birth year available, otherwise try all
            if person.birth_year:
                page.select_option('select[name="bdm"]', 'B')

            # Fill in surname
            if person.surname:
                page.fill('input[name="search_lastname"]', person.surname)

            # Fill in given name
            if person.given_name:
                page.fill('input[name="search_name"]', person.given_name)

            # Fill in date range if available
            if person.birth_year:
                page.fill('input[name="from_date"]', str(person.birth_year - 5))
                page.fill('input[name="to_date"]', str(person.birth_year + 5))

            # Submit form
            page.click('input[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=30000)

            # Parse results
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for result table
            results = []
            result_table = soup.find('table', {'class': 'wyniki'})
            if result_table:
                rows = result_table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        result = {
                            'surname': cols[0].text.strip(),
                            'given_name': cols[1].text.strip(),
                            'year': cols[2].text.strip(),
                            'parish': cols[3].text.strip(),
                            'link': cols[4].find('a')['href'] if cols[4].find('a') else None
                        }
                        results.append(result)

            return SearchResult(
                source="Geneteka",
                found=len(results) > 0,
                record_count=len(results),
                details=results
            )

        except Exception as e:
            return SearchResult(
                source="Geneteka",
                found=False,
                record_count=0,
                details=[],
                error=str(e)
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
        print(f"Birth: {person.birth_year}" + (f" in {person.birth_place}" if person.birth_place else ""))
    if person.death_year:
        print(f"Death: {person.death_year}" + (f" in {person.death_place}" if person.death_place else ""))
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

    args = parser.parse_args()

    # Check if GEDCOM file exists
    if not args.gedcom_file.exists():
        print(f"Error: GEDCOM file not found: {args.gedcom_file}")
        sys.exit(1)

    # Parse GEDCOM file
    print(f"Parsing GEDCOM file: {args.gedcom_file}")
    gedcom_parser = GedcomParser(args.gedcom_file)
    persons = gedcom_parser.parse()
    print(f"Found {len(persons)} persons in GEDCOM file")

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
                result = searchers["geneteka"].search(page, person)
                print_search_results(result)

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
