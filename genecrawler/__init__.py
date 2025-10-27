"""
GeneCrawler - Heredis Database to Genealogical Database Query Tool

This package provides tools to query Polish genealogical databases for persons
from a Heredis genealogy database.
"""

from .models import Person, SearchResult
from .database import MatchedRecordsDB
from .location import LocationParser
from .utils import extract_first_name, print_person_info, print_search_results, process_matches

__version__ = "0.2.0"

__all__ = [
    'Person',
    'SearchResult',
    'MatchedRecordsDB',
    'LocationParser',
    'extract_first_name',
    'print_person_info',
    'print_search_results',
    'process_matches',
]
