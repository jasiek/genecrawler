"""
Command-line interface for GeneCrawler.

This module contains the main CLI entry point and argument parsing.
"""

import argparse
import sys
import time
import random
from pathlib import Path

from playwright.sync_api import sync_playwright

from heredis_adapter import HeredisAdapter
from .models import Person
from .database import MatchedRecordsDB
from .utils import print_person_info, print_search_results, process_matches
from .searchers import (
    GenetekaSearcher,
    PTGSearcher,
    PoznanProjectSearcher,
    BaSIASearcher,
)


def main():
    """Main entry point for GeneCrawler CLI"""
    parser = argparse.ArgumentParser(
        description="Query Polish genealogical databases for persons in a Heredis database"
    )
    parser.add_argument(
        "heredis_db", type=Path, help="Path to Heredis database file (.heredis)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser with visible UI (default: headless mode)",
    )
    parser.add_argument("--limit", type=int, help="Limit number of persons to process")
    parser.add_argument(
        "--databases",
        nargs="+",
        choices=["geneteka", "ptg", "poznan", "basia", "all"],
        default=["all"],
        help="Which databases to query (default: all)",
    )
    parser.add_argument(
        "--use-nominatim",
        action="store_true",
        help="Use Nominatim API for geocoding unknown locations (slower)",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Randomize the order of persons to process (default: oldest first)",
    )
    parser.add_argument(
        "--record-id",
        type=str,
        help="Search only for a specific record by ID (e.g., 53 or @53@)",
    )
    parser.add_argument(
        "--recent-only",
        action="store_true",
        help="Search only records updated in the last 60 days (Geneteka only)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of result pages to crawl per search (default: unlimited)",
    )

    args = parser.parse_args()

    # Check if Heredis database exists
    if not args.heredis_db.exists():
        print(f"Error: Heredis database not found: {args.heredis_db}")
        sys.exit(1)

    # Parse Heredis database
    print(f"Reading Heredis database: {args.heredis_db}")
    with HeredisAdapter(args.heredis_db, use_nominatim=args.use_nominatim) as adapter:
        persons = adapter.parse()
    print(f"Found {len(persons)} persons in database")

    # Filter out people born after 1978
    persons_before_filter = len(persons)
    persons = [p for p in persons if p.birth_year is None or p.birth_year <= 1978]
    if persons_before_filter > len(persons):
        print(
            f"Filtered out {persons_before_filter - len(persons)} person(s) born after 1978"
        )

    # Filter for specific record if requested
    if args.record_id:
        # Normalize the ID - accept both "53" and "@53@" formats
        target_id = args.record_id
        if not target_id.startswith("@"):
            target_id = f"@{target_id}"
        if not target_id.endswith("@"):
            target_id = f"{target_id}@"

        matching_persons = [p for p in persons if p.id == target_id]
        if not matching_persons:
            print(f"Error: No person found with ID {target_id}")
            sys.exit(1)

        persons = matching_persons
        print(f"Filtered to specific record: {target_id}")

    # Show voivodeship statistics
    with_voivodeship = [p for p in persons if p.birth_voivodeship is not None]
    if with_voivodeship:
        print(f"Parsed voivodeships for {len(with_voivodeship)} persons")

    # Show Polish connection statistics
    with_polish_connection = [p for p in persons if p.has_polish_connection()]
    print(f"Found {len(with_polish_connection)} persons with Polish connections")

    # Sort or randomize persons (skip if specific record requested)
    if not args.record_id:
        if args.random:
            random.shuffle(persons)
            print(f"Randomized order of persons")
        else:
            # Sort persons by birth year (oldest first), putting those without birth years at the end
            persons.sort(key=lambda p: (p.birth_year is None, p.birth_year or 9999))
            print(f"Sorted persons by birth year (oldest first)")

        if args.limit:
            persons = persons[: args.limit]
            print(f"Limiting to first {args.limit} persons")

    # Determine which databases to search
    databases = args.databases
    if "all" in databases:
        databases = ["geneteka", "ptg", "poznan", "basia"]

    # Initialize searchers
    searchers = {}
    if "geneteka" in databases:
        searchers["geneteka"] = GenetekaSearcher(
            recent_only=args.recent_only, max_pages=args.max_pages
        )
        if args.recent_only:
            print("Searching only records updated in the last 60 days (Geneteka)")
        if args.max_pages:
            print(f"Limiting to {args.max_pages} page(s) per search (Geneteka)")
    if "ptg" in databases:
        searchers["ptg"] = PTGSearcher()
    if "poznan" in databases:
        searchers["poznan"] = PoznanProjectSearcher()
    if "basia" in databases:
        searchers["basia"] = BaSIASearcher()

    # Initialize matched records database
    matched_db = MatchedRecordsDB()
    print(f"Matched records database: {matched_db.db_path}")

    # Search databases
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()

        for person in persons:
            print_person_info(person)

            # Search each database
            if "geneteka" in searchers:
                # Geneteka only works for Poland
                if person.has_polish_connection():
                    result = searchers["geneteka"].search(page, person)
                    print_search_results(result)
                    process_matches(person, result, matched_db)
                else:
                    print("\nGeneteka:")
                    print("  Skipped (no Polish connection)")

            if "ptg" in searchers:
                result = searchers["ptg"].search(page, person)
                print_search_results(result)
                process_matches(person, result, matched_db)

            if "poznan" in searchers:
                result = searchers["poznan"].search(page, person)
                print_search_results(result)
                process_matches(person, result, matched_db)

            if "basia" in searchers:
                result = searchers["basia"].search(page, person)
                print_search_results(result)
                process_matches(person, result, matched_db)

            # Add a small delay between persons to be respectful to servers
            time.sleep(2)

        browser.close()

    print(f"\n{'='*80}")
    print("Search complete!")


if __name__ == "__main__":
    main()
