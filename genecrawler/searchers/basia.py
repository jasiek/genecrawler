"""
BaSIA searcher for GeneCrawler.

This module handles searching the BaSIA database (www.basia.famula.pl).
"""

from playwright.sync_api import Page
from bs4 import BeautifulSoup

from ..models import Person, SearchResult
from ..utils import extract_first_name


class BaSIASearcher:
    """Searches BaSIA database"""

    BASE_URL = "https://www.basia.famula.pl/en/"

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search BaSIA database for person"""
        print(f"  Searching BaSIA for {person.given_name} {person.surname}...")

        try:
            page.goto(self.BASE_URL, timeout=30000)
            page.wait_for_load_state('networkidle')

            # Fill in search form (use first name only)
            search_given_name = extract_first_name(person.given_name) if person.given_name else None
            if search_given_name:
                page.fill('input[name="firstname"]', search_given_name)

            if person.surname:
                page.fill('input[name="lastname"]', person.surname)

            # Set year range if available
            if person.birth_year:
                page.fill('input[name="yearfrom"]', str(person.birth_year - 5))
                page.fill('input[name="yearto"]', str(person.birth_year + 5))

            # Submit search
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=30000)

            # Parse results
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for results
            results = []
            result_table = soup.find('table', {'class': 'results'})
            if result_table:
                rows = result_table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        result = {
                            'name': cols[0].text.strip(),
                            'year': cols[1].text.strip(),
                            'place': cols[2].text.strip(),
                            'document_type': cols[3].text.strip()
                        }
                        results.append(result)

            return SearchResult(
                source="BaSIA",
                found=len(results) > 0,
                record_count=len(results),
                details=results
            )

        except Exception as e:
            return SearchResult(
                source="BaSIA",
                found=False,
                record_count=0,
                details=[],
                error=str(e)
            )
