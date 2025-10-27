"""
Database management for GeneCrawler.

This module handles storage of matched genealogical records.
"""

import sqlite3
from pathlib import Path
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Person
    from .utils import extract_first_name
else:
    # Import at runtime to avoid circular dependency
    from genecrawler.utils import extract_first_name


class MatchedRecordsDB:
    """Manages SQLite database for storing matched genealogical records"""

    def __init__(self):
        """Initialize matched records database"""
        self.db_path = Path.home() / '.genecrawler' / 'matched_records.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database and create matched_records table"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matched_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id TEXT NOT NULL,
                person_given_name TEXT NOT NULL,
                person_surname TEXT NOT NULL,
                record_type TEXT NOT NULL,
                source TEXT NOT NULL,
                voivodeship TEXT,
                year TEXT,
                act TEXT,
                result_given_name TEXT,
                result_surname TEXT,
                father_given_name TEXT,
                mother_given_name TEXT,
                mother_surname TEXT,
                parish TEXT,
                locality TEXT,
                link TEXT,
                raw_data TEXT,
                found_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(person_id, source, record_type, year, parish, result_given_name, result_surname)
            )
        ''')
        conn.commit()
        conn.close()

    def upsert_match(self, person: 'Person', result: Dict, source: str):
        """Upsert a matched record to the database

        Args:
            person: The Person from database
            result: The search result dictionary
            source: The source database name (e.g., 'Geneteka')
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if first name and surname match exactly (case-insensitive)
        result_given_name = result.get('given_name', '')
        result_surname = result.get('surname', '')

        if not (result_given_name and result_surname):
            conn.close()
            return False

        # Extract first names for comparison
        person_first_name = extract_first_name(person.given_name)
        result_first_name = extract_first_name(result_given_name)

        if (result_first_name.lower().strip() == person_first_name.lower().strip() and
            result_surname.lower().strip() == person.surname.lower().strip()):

            cursor.execute('''
                INSERT OR REPLACE INTO matched_records (
                    person_id, person_given_name, person_surname,
                    record_type, source, voivodeship, year, act,
                    result_given_name, result_surname,
                    father_given_name, mother_given_name, mother_surname,
                    parish, locality, link, raw_data, found_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                person.id,
                person.given_name,
                person.surname,
                result.get('type', ''),
                source,
                result.get('voivodeship', ''),
                result.get('year', ''),
                result.get('act', ''),
                result_given_name,
                result_surname,
                result.get('father_given_name', ''),
                result.get('mother_given_name', ''),
                result.get('mother_surname', ''),
                result.get('parish', ''),
                result.get('locality', ''),
                result.get('link', ''),
                str(result)
            ))

            conn.commit()
            conn.close()
            return True

        conn.close()
        return False
