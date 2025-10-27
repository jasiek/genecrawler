"""
Data models for GeneCrawler.

This module contains the core data structures used throughout the application.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Person:
    """Represents a person from genealogy database"""
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
