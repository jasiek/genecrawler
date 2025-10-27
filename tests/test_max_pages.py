"""
Test suite to verify max_pages functionality with GenetekaSearcher
"""

import pytest
from genecrawler.searchers import GenetekaSearcher
from genecrawler.models import Person


def test_geneteka_searcher_default_max_pages():
    """Test that default max_pages is None (unlimited)"""
    searcher = GenetekaSearcher(recent_only=False)
    assert searcher.max_pages is None, "Default should be unlimited (None)"


def test_geneteka_searcher_max_pages_one():
    """Test that max_pages can be set to 1"""
    searcher = GenetekaSearcher(recent_only=False, max_pages=1)
    assert searcher.max_pages == 1, "max_pages should be 1"


def test_geneteka_searcher_max_pages_five():
    """Test that max_pages can be set to 5"""
    searcher = GenetekaSearcher(recent_only=False, max_pages=5)
    assert searcher.max_pages == 5, "max_pages should be 5"


def test_geneteka_searcher_recent_only_and_max_pages():
    """Test that both recent_only and max_pages can be set together"""
    searcher = GenetekaSearcher(recent_only=True, max_pages=3)
    assert searcher.recent_only is True, "recent_only should be True"
    assert searcher.max_pages == 3, "max_pages should be 3"


def test_person_class_still_works():
    """Test that Person class creation still works correctly"""
    test_person = Person(
        id="@123@",
        given_name="Jan",
        surname="TEST",
        birth_year=1900
    )
    assert test_person.given_name == "Jan", "Person creation should still work"
    assert test_person.surname == "TEST"
    assert test_person.birth_year == 1900
