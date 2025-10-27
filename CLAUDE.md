# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GeneCrawler is a Python tool that queries multiple Polish genealogical databases (Geneteka, PTG PomGenBaza, Poznan Project, BaSIA) for persons in a Heredis genealogy database. It uses web scraping via Playwright to search these databases and stores matched records.

## Setup and Dependencies

### Installation
```bash
poetry install
poetry run playwright install chromium
```

### Running the Tool
```bash
# Basic usage
python3 genecrawler.py MyGenealogy.heredis

# With options
python3 genecrawler.py MyGenealogy.heredis --limit 10 --max-pages 1 --recent-only
python3 genecrawler.py MyGenealogy.heredis --record-id 57
python3 genecrawler.py MyGenealogy.heredis --databases geneteka ptg --no-headless
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_refactoring.py

# Run specific test function
poetry run pytest tests/test_refactoring.py::test_person_dataclass

# Show test collection without running
poetry run pytest --collect-only

# Run tests with coverage (if pytest-cov installed)
poetry run pytest --cov=genecrawler
```

## Architecture

### Package Structure

GeneCrawler was refactored from a monolithic 1047-line file into a modular package:

```
genecrawler.py              # Entry point (imports from genecrawler.cli)
heredis_adapter.py          # Heredis SQLite database adapter
genecrawler/
├── __init__.py            # Package exports
├── models.py              # Person and SearchResult dataclasses
├── utils.py               # Helper functions (extract_first_name, print functions)
├── location.py            # LocationParser with voivodeship mapping
├── database.py            # MatchedRecordsDB for storing matches
├── cli.py                 # Main CLI function and argument parsing
└── searchers/             # Web scraping implementations
    ├── __init__.py
    ├── geneteka.py        # GenetekaSearcher (supports --max-pages, --recent-only)
    ├── ptg.py             # PTGSearcher
    ├── poznan.py          # PoznanProjectSearcher
    └── basia.py           # BaSIASearcher
```

### Key Design Patterns

**Data Source**: The project uses Heredis SQLite databases (`.heredis` files) as input, NOT GEDCOM files. The `HeredisAdapter` class in `heredis_adapter.py` reads person data from Heredis tables (Individus, Noms, Prenoms, Evenements, Lieux) and always opens the database in **read-only mode** using SQLite URI syntax.

**Searcher Pattern**: All database searchers implement a common interface:
```python
def search(page: Page, person: Person) -> SearchResult
```
Each searcher uses Playwright to navigate websites, fill search forms, and parse results using BeautifulSoup.

**Polish Geography**: The `LocationParser` handles Polish voivodeship (province) mapping with support for Heredis-specific variations (e.g., "MAŁOPOLSKA" → "małopolskie"). Contains mappings for all 16 Polish voivodeships.

**Matched Records**: Exact matches are stored in `~/.genecrawler/matched_records.db` SQLite database via the `MatchedRecordsDB` class.

### Critical Implementation Details

**Geneteka Pagination**: The `GenetekaSearcher` supports pagination control via `--max-pages`. The pagination check occurs after parsing each page:
```python
if self.max_pages and page_num >= self.max_pages:
    print(f"      → Reached max pages limit ({self.max_pages})")
    break
```
Location: `genecrawler/searchers/geneteka.py`

**Voivodeship Mapping**: Heredis databases use variations like "MAŁOPOLSKA" while Polish standards use "małopolskie". The adapter includes a `VOIVODESHIP_MAPPING` dictionary with both standard names and Heredis variations.
Location: `heredis_adapter.py` and `genecrawler/location.py`

**Name Filtering**: Persons with uncertain names (containing `?`) are automatically skipped during database parsing to avoid false matches.
Location: `heredis_adapter.py:parse()`

**Polish Connection Logic**: Geneteka searches only run for persons with Polish connections (determined by voivodeship or assuming Poland if no location data). See `Person.has_polish_connection()` method.
Location: `genecrawler/models.py` and `genecrawler/cli.py:134-140`

## Common Development Tasks

### Adding a New Database Searcher

1. Create new file in `genecrawler/searchers/` (e.g., `newdb.py`)
2. Implement searcher class with `search(page: Page, person: Person) -> SearchResult` method
3. Add to `genecrawler/searchers/__init__.py` exports
4. Add to CLI initialization in `genecrawler/cli.py:112-117`
5. Add to `--databases` argument choices in `genecrawler/cli.py:31-34`

### Modifying Search Parameters

Search parameters are passed to searcher constructors in `genecrawler/cli.py:104-117`. For example, GenetekaSearcher accepts `recent_only` and `max_pages` parameters.

### Understanding Web Scraping Selectors

Each searcher uses CSS selectors and form field names specific to its target website. These may break if websites change. To debug:
1. Run with `--no-headless` to see browser
2. Use `inspect_geneteka_form.py` as a template for form field discovery
3. Check HTML structure in searcher files (e.g., `.select()` calls in geneteka.py)

### Working with Person Data

The `Person` dataclass (in `genecrawler/models.py`) contains:
- Core fields: `id`, `given_name`, `surname`
- Optional fields: `birth_year`, `death_year`, `birth_place`, `death_place`
- Polish geography: `birth_voivodeship`, `death_voivodeship`
- Family: `father_name`, `mother_name`

Access via the `HeredisAdapter`:
```python
from pathlib import Path
from heredis_adapter import HeredisAdapter

with HeredisAdapter(Path("database.heredis")) as adapter:
    persons = adapter.parse()  # Returns List[Person]
```

## Important Constraints

### Read-Only Database Access
The Heredis adapter ALWAYS opens databases in read-only mode:
```python
db_uri = f"file:{db_path}?mode=ro"
conn = sqlite3.connect(db_uri, uri=True)
```
Never modify this behavior - the database must remain read-only.

### Rate Limiting
The CLI includes `time.sleep(2)` between person searches to respect server resources. Do not remove or reduce these delays without explicit user request.

### Backward Compatibility
The refactoring maintains 100% backward compatibility. All existing CLI commands must continue to work. The entry point `genecrawler.py` is intentionally minimal (17 lines) and delegates to `genecrawler.cli.main()`.

### Web Scraping Fragility
HTML selectors are based on current website structures and may break when websites update. When modifying searchers, test with `--no-headless` to verify behavior.

## Data Flow

1. **Input**: User provides Heredis `.heredis` file path via CLI
2. **Parsing**: `HeredisAdapter` reads SQLite database, extracts persons with voivodeship detection
3. **Filtering**: Persons without names or with uncertain names are skipped
4. **Sorting**: Persons sorted by birth year (oldest first) unless `--random` specified
5. **Searching**: For each person, searchers use Playwright to query databases
6. **Matching**: Results parsed from HTML, exact matches identified
7. **Storage**: Exact matches stored in `~/.genecrawler/matched_records.db`
8. **Output**: Results printed to console with match statistics

## Recent Changes

The codebase recently underwent major refactoring (v0.2.0):
- Migrated from GEDCOM to Heredis database support
- Split monolithic file into modular package structure
- Added `--max-pages` feature for pagination control
- Added `--recent-only` feature for Geneteka incremental searches
- Removed `ged4py` dependency
- All changes maintain 100% backward compatibility

See `docs/REFACTORING_SUMMARY.md` and `docs/CHANGELOG.md` for details.
