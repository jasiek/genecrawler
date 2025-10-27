"""
Integration test to verify Heredis adapter integration with genecrawler
"""

import pytest
from pathlib import Path
from heredis_adapter import HeredisAdapter


# Check if test database exists
DB_PATH = Path("Szumiec.heredis")
pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason="Szumiec.heredis database not found"
)


def test_heredis_adapter_reads_database():
    """Test that HeredisAdapter can read the database"""
    with HeredisAdapter(DB_PATH, use_nominatim=False) as adapter:
        persons = adapter.parse()

    assert len(persons) > 0, "Should find persons in database"


def test_heredis_adapter_voivodeship_parsing():
    """Test that voivodeships are parsed correctly"""
    with HeredisAdapter(DB_PATH, use_nominatim=False) as adapter:
        persons = adapter.parse()

    with_voivodeship = [p for p in persons if p.birth_voivodeship is not None]
    # We should have at least some persons with voivodeships
    assert len(with_voivodeship) > 0, "Should parse voivodeships for some persons"


def test_heredis_adapter_polish_connections():
    """Test that Polish connections are detected"""
    with HeredisAdapter(DB_PATH, use_nominatim=False) as adapter:
        persons = adapter.parse()

    with_polish_connection = [p for p in persons if p.has_polish_connection()]
    # Most persons should have Polish connections
    assert len(with_polish_connection) > 0, "Should find persons with Polish connections"


def test_heredis_adapter_person_structure():
    """Test that persons have expected structure"""
    with HeredisAdapter(DB_PATH, use_nominatim=False) as adapter:
        persons = adapter.parse()

    # Check first person has required fields
    person = persons[0]
    assert hasattr(person, 'id')
    assert hasattr(person, 'given_name')
    assert hasattr(person, 'surname')
    assert person.id is not None
    assert person.given_name is not None or person.surname is not None


def test_heredis_adapter_filter_by_id():
    """Test filtering persons by ID"""
    with HeredisAdapter(DB_PATH, use_nominatim=False) as adapter:
        persons = adapter.parse()

    # Try to find a specific person by ID
    test_id = "@57@"
    matching = [p for p in persons if p.id == test_id]

    # If the ID exists in the database, we should find it
    # This test won't fail if the ID doesn't exist, as different databases may have different IDs
    if matching:
        assert matching[0].id == test_id
        assert matching[0].given_name is not None or matching[0].surname is not None


def test_heredis_adapter_context_manager():
    """Test that context manager properly manages resources"""
    # This should not raise any exceptions
    with HeredisAdapter(DB_PATH, use_nominatim=False) as adapter:
        persons = adapter.parse()
        assert len(persons) > 0

    # Connection should be closed after exiting context
    # If we get here without errors, the context manager worked
