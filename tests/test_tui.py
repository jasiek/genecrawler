"""
Test suite for GeneCrawler TUI
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path to import the TUI module
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_tui_imports():
    """Test that TUI module imports successfully"""
    import genecrawler_tui
    assert genecrawler_tui is not None


def test_matched_records_browser_class():
    """Test that MatchedRecordsBrowser class can be instantiated"""
    import genecrawler_tui
    browser = genecrawler_tui.MatchedRecordsBrowser()
    assert browser is not None
    assert browser.db_path == Path.home() / '.genecrawler' / 'matched_records.db'
    assert browser.search_mode is False
    assert browser.details_mode is False


def test_browser_columns_defined():
    """Test that browser has columns defined"""
    import genecrawler_tui
    browser = genecrawler_tui.MatchedRecordsBrowser()
    assert hasattr(browser, 'columns')
    assert len(browser.columns) > 0
    assert all(len(col) == 3 for col in browser.columns)

    # Check that Link column is present
    column_names = [col[0] for col in browser.columns]
    assert "Link" in column_names


def test_browser_get_column_value():
    """Test get_column_value function for special fields"""
    import genecrawler_tui
    browser = genecrawler_tui.MatchedRecordsBrowser()

    # Test _link field with link present
    record_with_link = {'link': 'https://example.com'}
    assert browser.get_column_value(record_with_link, '_link') == "✓"

    # Test _link field with empty link
    record_no_link = {'link': ''}
    assert browser.get_column_value(record_no_link, '_link') == ""

    # Test _link field with None link
    record_none_link = {'link': None}
    assert browser.get_column_value(record_none_link, '_link') == ""

    # Test _link field with whitespace-only link
    record_whitespace_link = {'link': '   '}
    assert browser.get_column_value(record_whitespace_link, '_link') == ""

    # Test regular field
    record = {'person_given_name': 'Jan'}
    assert browser.get_column_value(record, 'person_given_name') == "Jan"


def test_browser_truncate_text():
    """Test text truncation function"""
    import genecrawler_tui
    browser = genecrawler_tui.MatchedRecordsBrowser()

    # Test normal text
    assert browser.truncate_text("Hello", 10) == "Hello     "

    # Test truncation
    result = browser.truncate_text("This is a very long text", 10)
    assert len(result) == 10
    assert result.endswith("…")

    # Test empty text
    assert browser.truncate_text("", 5) == "     "

    # Test None
    assert browser.truncate_text(None, 5) == "     "


def test_browser_filter_records():
    """Test record filtering function"""
    import genecrawler_tui
    browser = genecrawler_tui.MatchedRecordsBrowser()

    # Create test records
    browser.records = [
        {'person_given_name': 'Jan', 'person_surname': 'Kowalski', 'year': '1900'},
        {'person_given_name': 'Anna', 'person_surname': 'Nowak', 'year': '1920'},
        {'person_given_name': 'Maria', 'person_surname': 'Kowalski', 'year': '1945'},
    ]

    # Test filtering
    browser.filter_records("Kowalski")
    assert len(browser.filtered_records) == 2

    browser.filter_records("Anna")
    assert len(browser.filtered_records) == 1
    assert browser.filtered_records[0]['person_given_name'] == 'Anna'

    browser.filter_records("1920")
    assert len(browser.filtered_records) == 1
    assert browser.filtered_records[0]['year'] == '1920'

    # Test empty query
    browser.filter_records("")
    assert len(browser.filtered_records) == 3


@pytest.mark.skipif(
    not (Path.home() / '.genecrawler' / 'matched_records.db').exists(),
    reason="matched_records.db not found"
)
def test_browser_load_records():
    """Test loading records from actual database"""
    import genecrawler_tui
    browser = genecrawler_tui.MatchedRecordsBrowser()

    result = browser.load_records()
    assert result is True
    assert len(browser.records) > 0
    assert len(browser.filtered_records) == len(browser.records)
