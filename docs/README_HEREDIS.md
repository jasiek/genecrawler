# Heredis Database Adapter for GeneCrawler

This document describes how to use a Heredis SQLite database (.heredis file) as a data source for GeneCrawler in place of a GEDCOM file.

## Overview

The `heredis_adapter.py` module provides a `HeredisAdapter` class that reads person data from Heredis genealogy software databases and converts it to the same `Person` format used by the GEDCOM parser. This allows you to use your Heredis database directly with GeneCrawler without needing to export to GEDCOM format.

## Features

- **Read-only access**: The database is always opened in read-only mode for safety
- **Complete person data**: Extracts names, birth/death dates and places, parent information
- **Voivodeship parsing**: Automatically detects and standardizes Polish voivodeship names from place data
- **Compatible interface**: Provides the same interface as `GedcomParser`, making it a drop-in replacement

## Quick Start

### Standalone Usage

Test the adapter directly on a Heredis database:

```bash
python3 heredis_adapter.py Szumiec.heredis
```

This will display:
- Total number of persons found
- First 5 persons with their details
- Statistics about the data (birth/death years, voivodeships, Polish connections)

### Integration with GeneCrawler

To use the adapter with GeneCrawler, you can modify the main script to accept Heredis databases:

```python
from pathlib import Path
from heredis_adapter import HeredisAdapter

# Instead of using GedcomParser:
# gedcom_parser = GedcomParser(args.gedcom_file, use_nominatim=args.use_nominatim)
# persons = gedcom_parser.parse()

# Use HeredisAdapter:
with HeredisAdapter(Path("Szumiec.heredis"), use_nominatim=args.use_nominatim) as adapter:
    persons = adapter.parse()

# The rest of the code works the same way
for person in persons:
    print(f"{person.given_name} {person.surname}")
    # ... search databases ...
```

## Database Structure

The adapter reads from these Heredis tables:
- **Individus**: Individual person records
- **Noms**: Surnames
- **Prenoms**: Given names
- **Evenements**: Events (births, deaths, marriages)
- **Lieux**: Places
- **Unions**: Marriages/partnerships

## Person Data Extracted

For each person, the adapter extracts:
- **ID**: Internal database ID (formatted as @123@)
- **Given name**: First/given names (from Prenoms field)
- **Surname**: Family name (from Noms table)
- **Birth year**: Extracted from birth event date
- **Death year**: Extracted from death event date
- **Birth place**: Full place string for birth location
- **Death place**: Full place string for death location
- **Birth voivodeship**: Standardized Polish voivodeship for birth
- **Death voivodeship**: Standardized Polish voivodeship for death
- **Father name**: Full name of father
- **Mother name**: Full name of mother

## Voivodeship Detection

The adapter includes built-in support for Polish voivodeship detection:

### Supported Voivodeships
- dolnośląskie (Lower Silesia)
- kujawsko-pomorskie (Kuyavian-Pomeranian)
- lubelskie (Lublin)
- lubuskie (Lubusz)
- łódzkie (Łódź)
- małopolskie (Lesser Poland)
- mazowieckie (Masovian)
- opolskie (Opole)
- podkarpackie (Subcarpathian)
- podlaskie (Podlaskie)
- pomorskie (Pomeranian)
- śląskie (Silesian)
- świętokrzyskie (Holy Cross)
- warmińsko-mazurskie (Warmian-Masurian)
- wielkopolskie (Greater Poland)
- zachodniopomorskie (West Pomeranian)

### Heredis-Specific Variations
The adapter recognizes common variations found in Heredis databases:
- "MAŁOPOLSKA" → małopolskie
- "WIELKOPOLSKA" → wielkopolskie
- English names (e.g., "Lesser Poland Voivodeship")

## Data Filtering

The adapter automatically skips:
- Persons without both a given name and surname
- Persons with uncertain names (containing "?" characters)

## Read-Only Mode

The adapter always opens the database in read-only mode using SQLite's URI mode:
```python
db_uri = f"file:{db_path}?mode=ro"
conn = sqlite3.connect(db_uri, uri=True)
```

This ensures the original database file is never modified.

## Context Manager Support

The adapter supports Python's context manager protocol for automatic resource cleanup:

```python
with HeredisAdapter(db_path) as adapter:
    persons = adapter.parse()
    # Database connection is automatically closed when exiting the block
```

## Example Output

```
Reading Heredis database: Szumiec.heredis
Skipped 66 person(s) with uncertain names (containing '?')

Found 2435 persons in database

First 5 persons:

1. Danuta KUDERCZAK (ID: @53@)
   Birth: 1958
   Death: 2001 in Modlnica, Powiat Krakowski, MAŁOPOLSKA, POLAND [małopolskie]

2. Maria SYREK (ID: @54@)

3. Jan BOCHEŃSKI (ID: @56@)
   Birth: 1913
   Death: 1983

4. Anna CZAJOWSKA (ID: @57@)
   Birth: 1918 in Modlniczka, Powiat Krakowski, MAŁOPOLSKA, POLAND [małopolskie]
   Death: 1990
   Father: Jan CZAJOWSKI
   Mother: Marianna PSTRUŚ

Statistics:
  Persons with birth year: 1763
  Persons with death year: 760
  Persons with voivodeship: 488
  Persons with Polish connection: 1760
```

## Requirements

- Python 3.6+
- sqlite3 (included in Python standard library)
- The `Person` dataclass from genecrawler.py (or standalone version included in adapter)

## Error Handling

The adapter includes error handling for:
- Missing database files
- Database read errors
- Invalid person records
- Missing or malformed data fields

Errors are reported to stdout and problematic records are skipped rather than causing the entire parse to fail.
