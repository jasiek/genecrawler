"""
Poznan Project searcher for GeneCrawler.

This module handles searching the Poznan Project database (poznan-project.psnc.pl).
"""

import time
from playwright.sync_api import Page
from bs4 import BeautifulSoup

from ..models import Person, SearchResult
from ..utils import extract_first_name


class PoznanProjectSearcher:
    """Searches Poznan Project database"""

    BASE_URL = "https://poznan-project.psnc.pl"

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search Poznan Project database for person"""
        print(f"  Searching Poznan Project for {person.given_name} {person.surname}...")

        try:
            page.goto(self.BASE_URL, timeout=30000)
            page.wait_for_load_state('networkidle')

            # Click on extended search
            page.click('a[href="#extendedsearch"]')
            time.sleep(1)

            # Fill in search form (use first name only)
            if person.surname:
                page.fill('input[name="surname"]', person.surname)

            search_given_name = extract_first_name(person.given_name) if person.given_name else None
            if search_given_name:
                # Groom or bride name
                page.fill('input[name="firstname1"]', search_given_name)

            # Set year range if available
            if person.birth_year:
                # For marriage records, estimate marriage year
                marriage_year = person.birth_year + 25
                page.fill('input[name="yearfrom"]', str(marriage_year - 10))
                page.fill('input[name="yearto"]', str(marriage_year + 10))

            # Submit search
            page.click('button#searchextended')
            page.wait_for_load_state('networkidle', timeout=30000)

            # Parse results
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for results table
            results = []
            result_table = soup.find('table', {'id': 'results'})
            if result_table:
                rows = result_table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        result = {
                            'groom': cols[0].text.strip(),
                            'bride': cols[1].text.strip(),
                            'year': cols[2].text.strip(),
                            'parish': cols[3].text.strip()
                        }
                        results.append(result)

            return SearchResult(
                source="Poznan Project",
                found=len(results) > 0,
                record_count=len(results),
                details=results
            )

        except Exception as e:
            return SearchResult(
                source="Poznan Project",
                found=False,
                record_count=0,
                details=[],
                error=str(e)
            )
