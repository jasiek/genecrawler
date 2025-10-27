# GeneCrawler

A Python tool to query multiple Polish genealogical databases for persons listed in a GEDCOM file.

## Supported Databases

- **Geneteka** (geneteka.genealodzy.pl) - 62.5 million indexed entries from Polish parish records
- **PTG PomGenBaza** (www.ptg.gda.pl) - Pomeranian region vital records
- **Poznan Project** (poznan-project.psnc.pl) - 1M+ marriage records from Greater Poland (1800-1899)
- **BaSIA** (www.basia.famula.pl) - 6.5 million indexed entries from Greater Poland archives

## Installation

1. The project uses Poetry for dependency management. Poetry version is specified in `.tool-versions` for asdf users.

2. Install dependencies:

```bash
poetry install
```

3. Install Playwright browsers:

```bash
poetry run playwright install chromium
```

## Usage

### Basic Usage

Query all databases for all persons in a Heredis database:

```bash
python3 genecrawler.py path/to/your/database.heredis
```

### Browse Matched Records

After running searches, use the TUI to browse matched records:

```bash
python3 genecrawler_tui.py
```

The TUI provides:
- Column-based table view of all matched records
- Full-text search (press `/`)
- Keyboard navigation with arrow keys
- Detailed view of individual records (press Enter)

See [TUI_GUIDE.md](TUI_GUIDE.md) for detailed usage instructions.

### Advanced Options

Limit to first 5 persons:
```bash
poetry run python genecrawler.py family.ged --limit 5
```

Query only specific databases:
```bash
poetry run python genecrawler.py family.ged --databases geneteka ptg
```

Run with visible browser (for debugging):
```bash
poetry run python genecrawler.py family.ged --no-headless
```

### Command Line Arguments

- `gedcom_file` - Path to your GEDCOM file (required)
- `--no-headless` - Run browser with visible UI for debugging (default: runs in headless mode)
- `--limit N` - Process only first N persons from GEDCOM file
- `--databases` - Select databases to query: `geneteka`, `ptg`, `poznan`, `basia`, or `all` (default: all)

## Output

For each person in the GEDCOM file, the script will:

1. Display person information (name, birth/death years and places)
2. Query each selected database
3. Display search results including:
   - Number of records found
   - Record details (names, dates, parishes, links to scans when available)

**Note**: Persons without names (both given name and surname missing) are automatically skipped.

Example output:

```
================================================================================
Person: Jan Kowalski (ID: @I1@)
Birth: 1850 in Poznań
Death: 1920 in Warszawa
================================================================================

  Searching Geneteka for Jan Kowalski...

Geneteka:
  Found 12 record(s):
    1. surname: Kowalski, given_name: Jan, year: 1850, parish: Poznań - św. Marcin
    2. surname: Kowalski, given_name: Jan, year: 1851, parish: Poznań - Fara
    ...

  Searching PTG PomGenBaza for Jan Kowalski...

PTG PomGenBaza:
  Found 3 record(s):
    1. name: Jan Kowalski, year: 1850, parish: Gdańsk
    ...
```

## Important Notes

### Web Scraping Limitations

This tool uses web scraping to query databases. Please note:

1. **Rate Limiting** - The script includes delays between requests to be respectful to servers
2. **HTML Structure Changes** - Websites may update their structure, requiring script updates
3. **Testing Required** - The HTML parsing selectors are based on research and may need adjustment for actual website structures
4. **Terms of Service** - Check each database's terms of service before heavy usage

### Debugging

If searches are not returning expected results:

1. Run with `--no-headless` to see the browser in action
2. Check if the website structure has changed
3. Verify that form field names and selectors in the code match the current website
4. Add more `time.sleep()` calls if pages are loading slowly

### Refining Searches

The script currently makes basic searches. You may want to customize:

- Search parameters (date ranges, exact vs. fuzzy matching)
- Result parsing (HTML structure varies by website)
- Error handling and retry logic
- Result filtering and ranking

## Development

### Project Structure

- `genecrawler.py` - Main script
- `test.py` - Test script for Geneteka form discovery
- `pyproject.toml` - Poetry dependencies
- `poetry.lock` - Poetry lock file
- `.tool-versions` - asdf version specification for Poetry

### Key Classes

- `GedcomParser` - Parses GEDCOM files using ged4py
  - Extracts names using GIVN/SURN sub-tags (with fallback to NAME value parsing)
- `Person` - Data class for person information
- `SearchResult` - Data class for search results
- `GenetekaSearcher` - Queries Geneteka database
- `PTGSearcher` - Queries PTG PomGenBaza
- `PoznanProjectSearcher` - Queries Poznan Project
- `BaSIASearcher` - Queries BaSIA database

### Adding New Databases

To add a new database:

1. Create a new searcher class (e.g., `MyDatabaseSearcher`)
2. Implement the `search(page: Page, person: Person) -> SearchResult` method
3. Add to the `searchers` dict in `main()`
4. Add to `--databases` choices in argument parser

## License

This tool is for personal genealogical research. Please respect the terms of service of each database you query.

## Contributing

Improvements welcome, especially:
- More accurate HTML parsing for each database
- Better error handling
- Support for additional databases
- GEDCOM parsing enhancements (parent names, etc.)
