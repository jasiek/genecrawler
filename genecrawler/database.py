"""
Database management for GeneCrawler.

This module handles storage of matched genealogical records and Nominatim caching.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Person
    from .utils import extract_first_name
else:
    # Import at runtime to avoid circular dependency
    from genecrawler.utils import extract_first_name


class GeneCrawlerDB:
    """Manages integrated SQLite database for GeneCrawler

    This class handles both matched records and Nominatim cache in a single database.
    """

    def __init__(self):
        """Initialize GeneCrawler database"""
        self.db_path = Path.home() / ".genecrawler" / "genecrawler.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database and create all required tables"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create matched_records table
        cursor.execute(
            """
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
        """
        )

        # Create retrieved_records table (stores all retrieved records, not just matches)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS retrieved_records (
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
        """
        )

        # Create nominatim_cache table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS nominatim_cache (
                query TEXT PRIMARY KEY,
                voivodeship TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def get_cached_voivodeship(self, query: str) -> Optional[str]:
        """Get cached voivodeship from database

        Args:
            query: The location query string

        Returns:
            The cached voivodeship (may be None if location not found),
            or a sentinel value '__NOT_CACHED__' if query not in cache
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT voivodeship FROM nominatim_cache WHERE query = ?", (query,)
        )
        result = cursor.fetchone()
        conn.close()

        if result is None:
            return "__NOT_CACHED__"
        return result[0]  # May be None if location wasn't found

    def set_cached_voivodeship(self, query: str, voivodeship: Optional[str]):
        """Store voivodeship in database cache

        Args:
            query: The location query string
            voivodeship: The voivodeship name (or None if not found)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO nominatim_cache (query, voivodeship)
            VALUES (?, ?)
        """,
            (query, voivodeship),
        )
        conn.commit()
        conn.close()


class MatchedRecordsDB(GeneCrawlerDB):
    """Manages SQLite database for storing matched genealogical records

    This is a compatibility wrapper that extends GeneCrawlerDB for backward compatibility.
    """

    def __init__(self):
        """Initialize matched records database"""
        super().__init__()

    def upsert_match(self, person: "Person", result: Dict, source: str):
        """Upsert a matched record to the database

        Args:
            person: The Person from database
            result: The search result dictionary
            source: The source database name (e.g., 'Geneteka')
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if first name and surname match exactly (case-insensitive)
        result_given_name = result.get("given_name", "")
        result_surname = result.get("surname", "")

        if not (result_given_name and result_surname):
            conn.close()
            return False

        # Extract first names for comparison
        person_first_name = extract_first_name(person.given_name)
        result_first_name = extract_first_name(result_given_name)

        if (
            result_first_name.lower().strip() == person_first_name.lower().strip()
            and result_surname.lower().strip() == person.surname.lower().strip()
        ):

            cursor.execute(
                """
                INSERT OR REPLACE INTO matched_records (
                    person_id, person_given_name, person_surname,
                    record_type, source, voivodeship, year, act,
                    result_given_name, result_surname,
                    father_given_name, mother_given_name, mother_surname,
                    parish, locality, link, raw_data, found_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    person.id,
                    person.given_name,
                    person.surname,
                    result.get("type", ""),
                    source,
                    result.get("voivodeship", ""),
                    result.get("year", ""),
                    result.get("act", ""),
                    result_given_name,
                    result_surname,
                    result.get("father_given_name", ""),
                    result.get("mother_given_name", ""),
                    result.get("mother_surname", ""),
                    result.get("parish", ""),
                    result.get("locality", ""),
                    result.get("link", ""),
                    str(result),
                ),
            )

            conn.commit()
            conn.close()
            return True

        conn.close()
        return False
