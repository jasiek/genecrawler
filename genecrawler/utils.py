"""
Utility functions for GeneCrawler.

This module contains helper functions used across the application.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Person, SearchResult
    from .database import MatchedRecordsDB


def extract_first_name(full_name: str) -> str:
    """Extract first name from a full given name string.

    Handles names like "Jan Walenty" -> "Jan"

    Args:
        full_name: Full given name (may contain multiple names)

    Returns:
        First name only
    """
    if not full_name:
        return ""
    return full_name.strip().split()[0]


def print_person_info(person: 'Person'):
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


def print_search_results(result: 'SearchResult'):
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


def process_matches(person: 'Person', result: 'SearchResult', matched_db: 'MatchedRecordsDB'):
    """Check for exact matches and store them in database

    Args:
        person: The Person from database
        result: The SearchResult from database search
        matched_db: The MatchedRecordsDB instance
    """
    if not result.found:
        return

    match_count = 0
    for detail in result.details:
        if matched_db.upsert_match(person, detail, result.source):
            match_count += 1

    if match_count > 0:
        print(f"  → Stored {match_count} exact match(es) to database")
