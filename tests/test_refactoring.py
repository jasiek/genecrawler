"""
Test suite to verify refactored genecrawler modules.
"""

import pytest
from genecrawler.models import Person, SearchResult
from genecrawler.utils import extract_first_name, print_person_info
from genecrawler.location import LocationParser
from genecrawler.database import MatchedRecordsDB
from genecrawler.searchers import GenetekaSearcher, PTGSearcher, PoznanProjectSearcher, BaSIASearcher


def test_models_import():
    """Test that models module imports correctly"""
    assert Person is not None
    assert SearchResult is not None


def test_utils_import():
    """Test that utils module imports correctly"""
    assert extract_first_name is not None
    assert print_person_info is not None


def test_location_import():
    """Test that location module imports correctly"""
    assert LocationParser is not None


def test_database_import():
    """Test that database module imports correctly"""
    assert MatchedRecordsDB is not None


def test_searchers_import():
    """Test that searchers module imports correctly"""
    assert GenetekaSearcher is not None
    assert PTGSearcher is not None
    assert PoznanProjectSearcher is not None
    assert BaSIASearcher is not None


def test_person_dataclass():
    """Test Person dataclass creation and usage"""
    person = Person(
        id="@123@",
        given_name="Jan",
        surname="Kowalski",
        birth_year=1900
    )
    assert person.given_name == "Jan"
    assert person.surname == "Kowalski"
    assert person.birth_year == 1900
    assert person.id == "@123@"


def test_search_result_dataclass():
    """Test SearchResult dataclass creation and usage"""
    result = SearchResult(
        source="Test",
        found=True,
        record_count=1,
        details=[{"name": "Jan Kowalski"}]
    )
    assert result.source == "Test"
    assert result.found is True
    assert result.record_count == 1
    assert len(result.details) == 1


def test_extract_first_name():
    """Test extract_first_name utility function"""
    assert extract_first_name("Jan Walenty") == "Jan"
    assert extract_first_name("Maria") == "Maria"
    assert extract_first_name("") == ""


def test_person_has_polish_connection():
    """Test Person.has_polish_connection() method"""
    person_with_voivodeship = Person(
        id="@1@",
        given_name="Jan",
        surname="Test",
        birth_voivodeship="małopolskie"
    )
    assert person_with_voivodeship.has_polish_connection() is True

    person_no_location = Person(
        id="@2@",
        given_name="Maria",
        surname="Test"
    )
    assert person_no_location.has_polish_connection() is True


def test_geneteka_searcher_initialization():
    """Test GenetekaSearcher initialization with parameters"""
    searcher = GenetekaSearcher(recent_only=False, max_pages=5)
    assert searcher.recent_only is False
    assert searcher.max_pages == 5


def test_package_exports():
    """Test that package __init__ exports work correctly"""
    import genecrawler
    from genecrawler import Person as P2, SearchResult as SR2

    assert P2 == Person
    assert SR2 == SearchResult


def test_location_parser_voivodeship_mapping():
    """Test LocationParser voivodeship mapping"""
    parser = LocationParser(use_nominatim=False)
    assert "MAŁOPOLSKIE" in parser.VOIVODESHIP_MAPPING
    assert parser.VOIVODESHIP_MAPPING["MAŁOPOLSKIE"] == "małopolskie"
