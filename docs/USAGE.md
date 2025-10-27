# GeneCrawler Usage Guide

GeneCrawler reads genealogy data from a Heredis database and searches Polish genealogical databases for matching records.

## Basic Usage

### Search all persons in a Heredis database

```bash
python3 genecrawler.py Szumiec.heredis
```

This will:
1. Read all persons from the Heredis database
2. Search Geneteka, PTG, Poznan Project, and BaSIA for each person
3. Store exact matches in `~/.genecrawler/matched_records.db`

### Limit the number of persons to search

```bash
python3 genecrawler.py Szumiec.heredis --limit 10
```

Processes only the first 10 persons (oldest first by birth year).

### Search only recent Geneteka records

```bash
python3 genecrawler.py Szumiec.heredis --recent-only
```

Searches only records added/updated in Geneteka in the last 60 days.

### Limit pages crawled per search

```bash
python3 genecrawler.py Szumiec.heredis --max-pages 1
```

Crawls only the first page of results for each search. Useful for faster searches when you don't need comprehensive results.

```bash
python3 genecrawler.py Szumiec.heredis --max-pages 3 --limit 10
```

Crawls up to 3 pages of results per search, processing 10 persons.

### Search a specific person by ID

```bash
python3 genecrawler.py Szumiec.heredis --record-id 57
```

Or with the @ format:
```bash
python3 genecrawler.py Szumiec.heredis --record-id @57@
```

### Select specific databases to search

```bash
# Search only Geneteka
python3 genecrawler.py Szumiec.heredis --databases geneteka

# Search Geneteka and PTG only
python3 genecrawler.py Szumiec.heredis --databases geneteka ptg
```

Available databases:
- `geneteka` - Geneteka.genealodzy.pl
- `ptg` - PTG PomGenBaza
- `poznan` - Poznan Project
- `basia` - BaSIA
- `all` - All databases (default)

### Randomize search order

```bash
python3 genecrawler.py Szumiec.heredis --random --limit 20
```

Process 20 random persons instead of the oldest first.

### Run with visible browser (debugging)

```bash
python3 genecrawler.py Szumiec.heredis --no-headless
```

Shows the browser window during searches (useful for debugging).

### Use Nominatim for location lookups

```bash
python3 genecrawler.py Szumiec.heredis --use-nominatim
```

Enables Nominatim geocoding to identify voivodeships for unknown locations.
**Warning**: This is slower and makes external API calls.

## Advanced Examples

### Search recent records for specific persons with Polish connections

```bash
python3 genecrawler.py Szumiec.heredis \
    --recent-only \
    --databases geneteka \
    --limit 50
```

### Full search with all options

```bash
python3 genecrawler.py Szumiec.heredis \
    --databases geneteka ptg \
    --use-nominatim \
    --limit 100 \
    --recent-only \
    --max-pages 5
```

### Quick shallow search (fast)

```bash
python3 genecrawler.py Szumiec.heredis \
    --databases geneteka \
    --max-pages 1 \
    --limit 20
```

Performs a fast search by crawling only the first page of results for 20 persons.

## Output

### Console Output

GeneCrawler displays:
- Database loading progress
- Person statistics (voivodeships, Polish connections)
- Search results for each person
- Exact matches stored to database

Example:
```
Reading Heredis database: Szumiec.heredis
Skipped 66 person(s) with uncertain names (containing '?')
Found 2435 persons in database
Parsed voivodeships for 426 persons
Found 1760 persons with Polish connections
Sorted persons by birth year (oldest first)

================================================================================
Person: Anna CZAJOWSKA (ID: @57@)
Birth: 1918 in Modlniczka, Powiat Krakowski, MAŁOPOLSKA, POLAND [małopolskie]
Death: 1990
Father: Jan CZAJOWSKI
Mother: Marianna PSTRUŚ
================================================================================
  Searching Geneteka for Anna CZAJOWSKA...
  Searching in voivodeship: małopolskie
    Searching births...
      Parameters: bdm=B, voivodeship=06mp (małopolskie), surname=CZAJOWSKA, given_name=Anna, years=1913-1923
      → Page 1: Found 2 result(s)
      → Total: 2 result(s) from 1 page(s)
    ...

Geneteka:
  Found 2 record(s):
    1. type: births, voivodeship: małopolskie, year: 1918, act: 123, given_name: Anna, surname: Czajowska, ...
    2. ...
  → Stored 1 exact match(es) to database
```

### Matched Records Database

Exact matches are stored in `~/.genecrawler/matched_records.db`.

Query matched records:
```bash
sqlite3 ~/.genecrawler/matched_records.db "SELECT * FROM matched_records WHERE person_surname = 'CZAJOWSKA'"
```

View all matches for a person:
```bash
sqlite3 ~/.genecrawler/matched_records.db \
    "SELECT source, record_type, year, parish, locality FROM matched_records WHERE person_id = '@57@'"
```

## Standalone Adapter Usage

You can also use the Heredis adapter directly:

```python
from pathlib import Path
from heredis_adapter import HeredisAdapter

# Read all persons
with HeredisAdapter(Path("Szumiec.heredis")) as adapter:
    persons = adapter.parse()

# Filter persons with voivodeships
with_voivodeship = [p for p in persons if p.birth_voivodeship]

# Find specific person
person = next((p for p in persons if p.surname == "CZAJOWSKA"), None)

if person:
    print(f"{person.given_name} {person.surname}")
    print(f"Born: {person.birth_year} in {person.birth_place}")
    if person.birth_voivodeship:
        print(f"Voivodeship: {person.birth_voivodeship}")
```

## Tips

1. **Start small**: Use `--limit 10` to test before processing all persons
2. **Use --max-pages**: Start with `--max-pages 1` for fast testing, then increase as needed
3. **Use --recent-only**: If you've already searched older records
4. **Target specific voivodeships**: Filter persons in Python before searching
5. **Check matched records**: Review `matched_records.db` regularly
6. **Respect rate limits**: Add delays between searches if needed
7. **Database backups**: The Heredis database is always opened read-only, but backup your matched_records.db
8. **Shallow vs deep searches**: Use `--max-pages 1` for quick reconnaissance, unlimited for comprehensive searches

## Troubleshooting

### Database not found
```
Error: Heredis database not found: Szumiec.heredis
```
**Solution**: Check the file path and ensure the .heredis file exists

### No persons found
```
Found 0 persons in database
```
**Solution**: Verify the database file is a valid Heredis database

### Playwright errors
```
ModuleNotFoundError: No module named 'playwright'
```
**Solution**: Install dependencies:
```bash
poetry install
playwright install chromium
```

### No voivodeships detected
The adapter includes built-in voivodeship detection. If none are found:
- Check that the Region field in your Heredis Lieux table is populated
- Try `--use-nominatim` for unknown locations (slower)

### Search failures
If searches consistently fail:
- Check your internet connection
- Try `--no-headless` to see browser errors
- Ensure the websites are accessible
- Respect rate limits (add delays if needed)

## Performance

Typical performance:
- Database loading: < 1 second for ~2500 persons
- Geneteka search (1 page): ~5-10 seconds per person
- Geneteka search (all pages): ~10-30 seconds per person (depends on result count)
- Full database search: Several hours (with delays between searches)

Recommendations:
- Use `--limit` for testing
- Use `--max-pages 1` for faster shallow searches
- Use `--recent-only` for incremental searches
- Search specific databases rather than all
- Run searches during off-peak hours

Performance comparison:
- `--max-pages 1`: ~5-10 seconds per person (fastest, may miss some results)
- `--max-pages 3`: ~10-20 seconds per person (good balance)
- No limit (default): ~10-30 seconds per person (most thorough)
