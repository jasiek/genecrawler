"""
Test suite to verify max_pages parameter implementation
"""

import re
import pytest
from pathlib import Path


def test_geneteka_searcher_has_max_pages_init():
    """Test that GenetekaSearcher.__init__ has max_pages parameter"""
    geneteka_path = Path("genecrawler/searchers/geneteka.py")
    content = geneteka_path.read_text()

    # Check __init__ signature includes max_pages
    init_match = re.search(r'def __init__\(self.*?max_pages.*?\)', content, re.DOTALL)
    assert init_match, "GenetekaSearcher.__init__ should have max_pages parameter"


def test_geneteka_searcher_assigns_max_pages():
    """Test that self.max_pages is assigned in __init__"""
    geneteka_path = Path("genecrawler/searchers/geneteka.py")
    content = geneteka_path.read_text()

    assert "self.max_pages = max_pages" in content, "self.max_pages should be assigned in __init__"


def test_geneteka_searcher_checks_max_pages():
    """Test that pagination loop checks max_pages limit"""
    geneteka_path = Path("genecrawler/searchers/geneteka.py")
    content = geneteka_path.read_text()

    max_pages_check = re.search(r'if self\.max_pages and page_num >= self\.max_pages:', content)
    assert max_pages_check, "Pagination loop should check max_pages"


def test_cli_has_max_pages_argument():
    """Test that CLI has --max-pages argument"""
    cli_path = Path("genecrawler/cli.py")
    content = cli_path.read_text()

    cli_arg = re.search(r'--max-pages.*?Maximum number of result pages', content, re.DOTALL)
    assert cli_arg, "--max-pages command-line argument should be defined"


def test_cli_initializes_geneteka_with_max_pages():
    """Test that CLI initializes GenetekaSearcher with max_pages"""
    cli_path = Path("genecrawler/cli.py")
    content = cli_path.read_text()

    init_call = re.search(r'GenetekaSearcher\(.*?max_pages=args\.max_pages', content, re.DOTALL)
    assert init_call, "GenetekaSearcher should be initialized with args.max_pages"


def test_max_pages_help_message():
    """Test that help message describes max_pages functionality"""
    cli_path = Path("genecrawler/cli.py")
    content = cli_path.read_text()

    help_msg = "Maximum number of result pages to crawl per search" in content
    assert help_msg, "Help message should describe max_pages functionality"


def test_max_pages_user_feedback():
    """Test that user feedback is shown when max_pages is set"""
    cli_path = Path("genecrawler/cli.py")
    content = cli_path.read_text()

    feedback_msg = 'print(f"Limiting to {args.max_pages} page(s) per search (Geneteka)")' in content
    assert feedback_msg, "Should print feedback when max_pages is set"


def test_max_pages_reached_message():
    """Test that message is shown when max pages limit is reached"""
    geneteka_path = Path("genecrawler/searchers/geneteka.py")
    content = geneteka_path.read_text()

    reached_msg = 'print(f"      → Reached max pages limit ({self.max_pages})")' in content
    assert reached_msg, "Should print message when max pages limit is reached"


def test_geneteka_searcher_initialization_with_max_pages():
    """Test that GenetekaSearcher can be initialized with max_pages"""
    from genecrawler.searchers import GenetekaSearcher

    # Test with max_pages set
    searcher = GenetekaSearcher(recent_only=False, max_pages=5)
    assert searcher.max_pages == 5

    # Test with max_pages as None
    searcher2 = GenetekaSearcher(recent_only=False, max_pages=None)
    assert searcher2.max_pages is None
