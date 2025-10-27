"""
PTG PomGenBaza searcher for GeneCrawler.

This module handles searching the PTG PomGenBaza database (www.ptg.gda.pl).
"""

from playwright.sync_api import Page
from bs4 import BeautifulSoup

from ..models import Person, SearchResult
from ..utils import extract_first_name


class PTGSearcher:
    """Searches PTG PomGenBaza database"""

    BASE_URL = "https://www.ptg.gda.pl/language/pl/pomgenbaza/przeszukiwanie-rejestrow-metrykalnych/"

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search PTG database for person"""
        print(f"  Searching PTG PomGenBaza for {person.given_name} {person.surname}...")

        try:
            page.goto(self.BASE_URL, timeout=30000)
            page.wait_for_load_state('networkidle')

            # Fill in search form (use first name only)
            search_given_name = extract_first_name(person.given_name) if person.given_name else None
            if search_given_name:
                page.fill('input[name="mim"]', search_given_name)

            if person.surname:
                page.fill('input[name="mnz"]', person.surname)

            # Fill in date range if available
            if person.birth_year:
                page.fill('input[name="ode"]', str(person.birth_year - 5))
                page.fill('input[name="doe"]', str(person.birth_year + 5))

            # Submit search
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=30000)

            # Parse results
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for results
            results = []
            result_div = soup.find('div', {'id': 'ptgSearchResults'})
            if result_div:
                rows = result_div.find_all('div', {'class': 'ptg-search-row'})
                for row in rows:
                    result = {
                        'name': row.find('span', {'class': 'name'}).text.strip() if row.find('span', {'class': 'name'}) else '',
                        'year': row.find('span', {'class': 'year'}).text.strip() if row.find('span', {'class': 'year'}) else '',
                        'parish': row.find('span', {'class': 'parish'}).text.strip() if row.find('span', {'class': 'parish'}) else ''
                    }
                    results.append(result)

            return SearchResult(
                source="PTG PomGenBaza",
                found=len(results) > 0,
                record_count=len(results),
                details=results
            )

        except Exception as e:
            return SearchResult(
                source="PTG PomGenBaza",
                found=False,
                record_count=0,
                details=[],
                error=str(e)
            )
