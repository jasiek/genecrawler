#!/usr/bin/env python3
"""
Heredis SQLite Database Adapter

This module provides an adapter to read person data from a Heredis SQLite database
(.heredis file) and convert it to the same Person format used by the GEDCOM parser.

The adapter allows using a Heredis database as a data source in place of a GEDCOM file.
"""

import sqlite3
import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

# Import the Person class and related utilities from genecrawler
# These must be imported from the main module
try:
    from genecrawler import Person, LocationParser
except ImportError:
    # For testing, allow running standalone with definitions
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
            """Check if person has a connection to Poland"""
            if self.birth_voivodeship or self.death_voivodeship:
                return True
            has_any_location = bool(self.birth_place or self.death_place)
            if not has_any_location:
                return True
            places = [self.birth_place, self.death_place]
            for place in places:
                if place:
                    place_upper = place.upper()
                    if 'POLAND' in place_upper or 'POLSKA' in place_upper or 'POL' in place_upper:
                        return True
            return False

    # Placeholder for LocationParser if not available
    class LocationParser:
        def __init__(self, use_nominatim: bool = False):
            self.use_nominatim = use_nominatim

        def parse_voivodeship(self, place_str: Optional[str]) -> Optional[str]:
            return None


class HeredisAdapter:
    """Adapter to read person data from Heredis SQLite database"""

    # Heredis event type codes
    EVENT_TYPE_MARRIAGE = 1
    EVENT_TYPE_BIRTH = 4
    EVENT_TYPE_DEATH = 12

    # Voivodeship mapping (standardized names)
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
        'MAŁOPOLSKA': 'małopolskie',  # Heredis variation
        'MALOPOLSKIE': 'małopolskie',
        'MALOPOLSKA': 'małopolskie',   # Heredis variation
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
        'WIELKOPOLSKA': 'wielkopolskie',  # Heredis variation
        'GREATER POLAND VOIVODESHIP': 'wielkopolskie',
        'GREATER POLAND': 'wielkopolskie',

        'ZACHODNIOPOMORSKIE': 'zachodniopomorskie',
        'WEST POMERANIAN VOIVODESHIP': 'zachodniopomorskie',
        'WEST POMERANIA': 'zachodniopomorskie',
    }

    def __init__(self, db_path: Path, use_nominatim: bool = False):
        """Initialize Heredis adapter

        Args:
            db_path: Path to the Heredis SQLite database file (.heredis)
            use_nominatim: If True, use Nominatim API for geocoding unknown locations
        """
        self.db_path = db_path
        self.location_parser = LocationParser(use_nominatim=use_nominatim)
        self._conn = None

        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")

    def _open_connection(self) -> sqlite3.Connection:
        """Open read-only connection to the database

        Returns:
            SQLite connection in read-only mode
        """
        if self._conn is None:
            # Open in read-only mode using URI
            db_uri = f"file:{self.db_path}?mode=ro"
            self._conn = sqlite3.connect(db_uri, uri=True)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _close_connection(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        """Context manager entry"""
        self._open_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self._close_connection()

    def parse(self) -> List[Person]:
        """Parse Heredis database and return list of persons

        Returns:
            List of Person objects extracted from the database
        """
        persons = []
        skipped_no_name = 0
        skipped_uncertain = 0

        try:
            conn = self._open_connection()
            cursor = conn.cursor()

            # Query to get all individuals with their basic information
            # Join with Noms to get surname
            query = """
                SELECT
                    i.CodeID,
                    i.Prenoms,
                    n.Nom as Surname,
                    i.XrefMainEventNaissance,
                    i.XrefMainEventDeces,
                    i.XrefPere,
                    i.XrefMere
                FROM Individus i
                JOIN Noms n ON i.XrefNom = n.CodeID
                ORDER BY i.CodeID
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                person, skip_reason = self._extract_person(cursor, row)
                if person:
                    persons.append(person)
                elif skip_reason == 'no_name':
                    skipped_no_name += 1
                elif skip_reason == 'uncertain':
                    skipped_uncertain += 1

            if skipped_no_name > 0:
                print(f"Skipped {skipped_no_name} person(s) without names")
            if skipped_uncertain > 0:
                print(f"Skipped {skipped_uncertain} person(s) with uncertain names (containing '?')")

        except Exception as e:
            print(f"Error parsing Heredis database: {e}")
            raise

        return persons

    def _extract_person(self, cursor: sqlite3.Cursor, row: sqlite3.Row) -> Tuple[Optional[Person], Optional[str]]:
        """Extract person information from database row

        Args:
            cursor: Database cursor for additional queries
            row: Row from Individus table query

        Returns:
            Tuple of (Person, skip_reason) where Person is None if skipped,
            and skip_reason is 'no_name', 'uncertain', or None
        """
        try:
            # Get basic information
            person_id = f"@{row['CodeID']}@"  # Format similar to GEDCOM IDs
            given_name = (row['Prenoms'] or "").strip()
            surname = (row['Surname'] or "").strip()

            # Skip persons without at least a surname or given name
            if not surname and not given_name:
                return None, 'no_name'

            # Skip persons with uncertain names (containing "?")
            if '?' in given_name or '?' in surname:
                return None, 'uncertain'

            # Get birth information
            birth_year = None
            birth_place = None
            birth_voivodeship = None
            if row['XrefMainEventNaissance']:
                birth_year, birth_place, birth_voivodeship = self._get_event_details(
                    cursor, row['XrefMainEventNaissance']
                )

            # Get death information
            death_year = None
            death_place = None
            death_voivodeship = None
            if row['XrefMainEventDeces']:
                death_year, death_place, death_voivodeship = self._get_event_details(
                    cursor, row['XrefMainEventDeces']
                )

            # Get parent names
            father_name = None
            mother_name = None
            if row['XrefPere']:
                father_name = self._get_person_name(cursor, row['XrefPere'])
            if row['XrefMere']:
                mother_name = self._get_person_name(cursor, row['XrefMere'])

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
            print(f"Error extracting person {row['CodeID']}: {e}")
            return None, 'error'

    def _get_event_details(self, cursor: sqlite3.Cursor, event_id: int) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """Get event details (year, place, voivodeship)

        Args:
            cursor: Database cursor
            event_id: Event CodeID

        Returns:
            Tuple of (year, place_string, voivodeship)
        """
        query = """
            SELECT
                e.DateGed,
                e.XrefLieu,
                l.Ville,
                l.Departement,
                l.Region,
                l.Pays
            FROM Evenements e
            LEFT JOIN Lieux l ON e.XrefLieu = l.CodeID
            WHERE e.CodeID = ?
        """

        cursor.execute(query, (event_id,))
        row = cursor.fetchone()

        if not row:
            return None, None, None

        # Extract year from DateGed
        year = self._extract_year(row['DateGed'])

        # Build place string
        place_string = None
        voivodeship = None
        if row['XrefLieu']:
            place_parts = []
            if row['Ville']:
                place_parts.append(row['Ville'])
            if row['Departement']:
                place_parts.append(row['Departement'])
            if row['Region']:
                place_parts.append(row['Region'])
            if row['Pays']:
                place_parts.append(row['Pays'])

            if place_parts:
                place_string = ', '.join(place_parts)

            # Extract voivodeship from Region field or parse from place string
            # In Heredis databases, the Region field often contains the voivodeship
            if row['Region']:
                voivodeship = self._parse_voivodeship_direct(row['Region'])

            # If not found in Region, try parsing the full place string
            if not voivodeship:
                voivodeship = self.location_parser.parse_voivodeship(place_string)

        return year, place_string, voivodeship

    def _parse_voivodeship_direct(self, region_str: str) -> Optional[str]:
        """Parse voivodeship directly from a region string

        This is optimized for Heredis databases where the Region field
        contains voivodeship information.

        Args:
            region_str: Region string from Lieux table

        Returns:
            Standardized voivodeship name or None
        """
        if not region_str:
            return None

        region_upper = region_str.upper().strip()

        # Use the adapter's own voivodeship mapping
        if region_upper in self.VOIVODESHIP_MAPPING:
            return self.VOIVODESHIP_MAPPING[region_upper]

        # Also try LocationParser's mapping if available (for integration with genecrawler)
        if hasattr(self.location_parser, 'VOIVODESHIP_MAPPING'):
            mapping = self.location_parser.VOIVODESHIP_MAPPING
            if region_upper in mapping:
                return mapping[region_upper]

        return None

    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        """Extract year from Heredis date string

        Heredis uses GEDCOM date format (e.g., "20 MAR 1918", "1918")

        Args:
            date_str: Date string from DateGed field

        Returns:
            Year as integer or None
        """
        if not date_str:
            return None

        try:
            # Try to extract 4-digit year
            match = re.search(r'\b(1\d{3}|20\d{2})\b', date_str)
            if match:
                return int(match.group(1))
        except Exception:
            pass

        return None

    def _get_person_name(self, cursor: sqlite3.Cursor, person_id: int) -> Optional[str]:
        """Get person's full name

        Args:
            cursor: Database cursor
            person_id: Person's CodeID

        Returns:
            Full name as "GivenName Surname" or None
        """
        query = """
            SELECT i.Prenoms, n.Nom
            FROM Individus i
            JOIN Noms n ON i.XrefNom = n.CodeID
            WHERE i.CodeID = ?
        """

        cursor.execute(query, (person_id,))
        row = cursor.fetchone()

        if not row:
            return None

        given_name = (row['Prenoms'] or "").strip()
        surname = (row['Nom'] or "").strip()

        # Build full name
        parts = []
        if given_name:
            parts.append(given_name)
        if surname:
            parts.append(surname)

        return ' '.join(parts) if parts else None

    def __del__(self):
        """Cleanup: close connection if still open"""
        self._close_connection()


def main():
    """Example usage of HeredisAdapter"""
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python heredis_adapter.py <path_to_heredis_db>")
        sys.exit(1)

    db_path = Path(sys.argv[1])

    print(f"Reading Heredis database: {db_path}")

    with HeredisAdapter(db_path, use_nominatim=False) as adapter:
        persons = adapter.parse()

    print(f"\nFound {len(persons)} persons in database")

    # Show first 5 persons as examples
    print("\nFirst 5 persons:")
    for i, person in enumerate(persons[:5], 1):
        print(f"\n{i}. {person.given_name} {person.surname} (ID: {person.id})")
        if person.birth_year:
            birth_info = f"   Birth: {person.birth_year}"
            if person.birth_place:
                birth_info += f" in {person.birth_place}"
            if person.birth_voivodeship:
                birth_info += f" [{person.birth_voivodeship}]"
            print(birth_info)
        if person.death_year:
            death_info = f"   Death: {person.death_year}"
            if person.death_place:
                death_info += f" in {person.death_place}"
            if person.death_voivodeship:
                death_info += f" [{person.death_voivodeship}]"
            print(death_info)
        if person.father_name:
            print(f"   Father: {person.father_name}")
        if person.mother_name:
            print(f"   Mother: {person.mother_name}")

    # Show statistics
    with_birth = [p for p in persons if p.birth_year]
    with_death = [p for p in persons if p.death_year]
    with_voivodeship = [p for p in persons if p.birth_voivodeship or p.death_voivodeship]
    with_polish_connection = [p for p in persons if p.has_polish_connection()]

    print(f"\nStatistics:")
    print(f"  Persons with birth year: {len(with_birth)}")
    print(f"  Persons with death year: {len(with_death)}")
    print(f"  Persons with voivodeship: {len(with_voivodeship)}")
    print(f"  Persons with Polish connection: {len(with_polish_connection)}")


if __name__ == "__main__":
    main()
