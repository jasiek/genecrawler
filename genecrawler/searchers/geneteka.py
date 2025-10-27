"""
Geneteka searcher for GeneCrawler.

This module handles searching the Geneteka database (geneteka.genealodzy.pl).
"""

import time
from typing import Optional
from playwright.sync_api import Page
from bs4 import BeautifulSoup

from ..models import Person, SearchResult
from ..utils import extract_first_name


class GenetekaSearcher:
    """Searches geneteka.genealodzy.pl database"""

    BASE_URL = "https://geneteka.genealodzy.pl"

    # Mapping of standardized voivodeship names to Geneteka codes
    VOIVODESHIP_CODES = {
        'dolnośląskie': '01ds',
        'kujawsko-pomorskie': '02kp',
        'lubelskie': '03lb',
        'lubuskie': '04ls',
        'łódzkie': '05ld',
        'małopolskie': '06mp',
        'mazowieckie': '07mz',
        'opolskie': '08op',
        'podkarpackie': '09pk',
        'podlaskie': '10pl',
        'pomorskie': '11pm',
        'śląskie': '12sl',
        'świętokrzyskie': '13sk',
        'warmińsko-mazurskie': '14wm',
        'wielkopolskie': '15wp',
        'zachodniopomorskie': '16zp',
    }

    def __init__(self, recent_only: bool = False, max_pages: Optional[int] = None):
        """Initialize Geneteka searcher

        Args:
            recent_only: If True, search only records updated in last 60 days
            max_pages: Maximum number of pages to crawl per search (None = unlimited)
        """
        self.recent_only = recent_only
        self.max_pages = max_pages

    def search(self, page: Page, person: Person) -> SearchResult:
        """Search Geneteka database for person"""
        print(f"  Searching Geneteka for {person.given_name} {person.surname}...")

        all_results = []

        # Determine which voivodeships to search
        voivodeship = person.birth_voivodeship or person.death_voivodeship
        if voivodeship and voivodeship in self.VOIVODESHIP_CODES:
            # Search only the identified voivodeship
            voivodeships_to_search = [(voivodeship, self.VOIVODESHIP_CODES[voivodeship])]
            print(f"  Searching in voivodeship: {voivodeship}")
        else:
            # Search all voivodeships
            voivodeships_to_search = list(self.VOIVODESHIP_CODES.items())
            print(f"  No voivodeship identified - searching all {len(voivodeships_to_search)} voivodeships")

        # Search for births, marriages, and deaths
        # Map BDM types to table IDs used in Geneteka results
        record_types = [
            ('B', 'births', 'table_b', person.birth_year, -5, 5),
            ('M', 'marriages', 'table_s', person.birth_year + 25 if person.birth_year else None, -10, 10),
            ('D', 'deaths', 'table_d', person.death_year, -5, 5)
        ]

        for bdm_type, type_name, table_id, base_year, year_before, year_after in record_types:
            print(f"    Searching {type_name}...")

            for voivodeship_name, voivodeship_code in voivodeships_to_search:
                try:
                    # Navigate to main search page
                    page.goto(f"{self.BASE_URL}/index.php?op=gt&lang=pol", timeout=30000)
                    page.wait_for_load_state('domcontentloaded')

                    # Set the BDM (birth/marriage/death) parameter
                    page.evaluate(f"document.querySelector('input[name=\"bdm\"]').value = '{bdm_type}'")

                    # Select voivodeship
                    page.select_option('select[name="w"]', voivodeship_code)

                    # Fill in surname
                    if person.surname:
                        page.fill('input[name="search_lastname"]', person.surname)

                    # Fill in given name (use first name only)
                    search_given_name = extract_first_name(person.given_name) if person.given_name else None
                    if search_given_name:
                        page.fill('input[name="search_name"]', search_given_name)

                    # Fill in date range if available
                    from_year = None
                    to_year = None
                    if base_year:
                        from_year = base_year + year_before
                        to_year = base_year + year_after
                        page.fill('input[name="from_date"]', str(from_year))
                        page.fill('input[name="to_date"]', str(to_year))

                    # Check "recent records only" option if requested
                    if self.recent_only:
                        page.check('input[name="search_only_recent"]')

                    # Print search parameters
                    recent_str = ", recent_only=True" if self.recent_only else ""
                    print(f"      Parameters: bdm={bdm_type}, voivodeship={voivodeship_code} ({voivodeship_name}), "
                          f"surname={person.surname or 'any'}, given_name={search_given_name or 'any'}, "
                          f"years={from_year or 'any'}-{to_year or 'any'}{recent_str}")

                    # Submit form
                    page.click('input[type="submit"]')
                    page.wait_for_load_state('networkidle', timeout=30000)

                    # Parse results from all pages
                    page_num = 1
                    total_row_count = 0

                    while True:
                        # Parse current page
                        html = page.content()
                        soup = BeautifulSoup(html, 'html.parser')

                        # Look for result table with specific ID and class
                        result_table = soup.find('table', {'id': table_id, 'class': 'tablesearch'})
                        if not result_table:
                            break

                        rows = result_table.find_all('tr')[1:]  # Skip header
                        page_row_count = 0

                        for row in rows:
                            cols = row.find_all('td')

                            # Parse based on record type (different table structures)
                            if bdm_type == 'B' and len(cols) >= 10:
                                # Birth table: Rok, Akt, Imię, Nazwisko, Imię ojca, Imię matki,
                                #              Nazwisko matki, Parafia, Miejscowość, Uwagi
                                scan_link = None
                                if cols[9].find('a', href=True):
                                    for link in cols[9].find_all('a', href=True):
                                        if 'skanoteka' in link['href'] or 'doc' in link.get('target', ''):
                                            scan_link = link['href']
                                            break

                                result = {
                                    'type': type_name,
                                    'voivodeship': voivodeship_name,
                                    'year': cols[0].text.strip(),
                                    'act': cols[1].text.strip(),
                                    'given_name': cols[2].text.strip(),
                                    'surname': cols[3].text.strip(),
                                    'father_given_name': cols[4].text.strip(),
                                    'mother_given_name': cols[5].text.strip(),
                                    'mother_surname': cols[6].text.strip(),
                                    'parish': cols[7].text.strip(),
                                    'locality': cols[8].text.strip(),
                                    'link': scan_link
                                }
                                all_results.append(result)
                                page_row_count += 1

                            elif (bdm_type == 'M' or bdm_type == 'D') and len(cols) >= 5:
                                # TODO: Marriage and death tables have different structures
                                # For now, use a generic parser
                                result = {
                                    'type': type_name,
                                    'voivodeship': voivodeship_name,
                                    'data': ', '.join([col.text.strip() for col in cols[:5]])
                                }
                                all_results.append(result)
                                page_row_count += 1

                        total_row_count += page_row_count

                        if page_row_count > 0:
                            print(f"      → Page {page_num}: Found {page_row_count} result(s)")

                        # Check if we've reached max_pages limit
                        if self.max_pages and page_num >= self.max_pages:
                            print(f"      → Reached max pages limit ({self.max_pages})")
                            break

                        # Check for next page button (DataTables pagination)
                        # Look for enabled "Next" button
                        try:
                            next_button = page.locator(f'#{table_id}_next:not(.disabled)')
                            if next_button.count() > 0 and 'disabled' not in next_button.get_attribute('class'):
                                next_button.click()
                                page.wait_for_load_state('networkidle', timeout=10000)
                                page_num += 1
                                time.sleep(0.5)  # Small delay between pages
                            else:
                                break
                        except Exception:
                            # No more pages
                            break

                    if total_row_count > 0:
                        print(f"      → Total: {total_row_count} result(s) from {page_num} page(s)")

                    # Small delay between searches
                    time.sleep(1)

                except Exception as e:
                    print(f"      Error searching {voivodeship_name}: {e}")

        return SearchResult(
            source="Geneteka",
            found=len(all_results) > 0,
            record_count=len(all_results),
            details=all_results
        )
