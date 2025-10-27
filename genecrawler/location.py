"""
Location parsing and voivodeship detection for GeneCrawler.

This module handles parsing of location strings and detection of Polish voivodeships.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


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
        """Parse voivodeship from place string

        Args:
            place_str: Place string in format: Town, Area code, County, Region, Country, Subdivision

        Returns:
            Standardized voivodeship name or None
        """
        if not place_str:
            return None

        # Check cache first
        if place_str in self._cache:
            return self._cache[place_str]

        voivodeship = None

        # First try to extract from place format
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
