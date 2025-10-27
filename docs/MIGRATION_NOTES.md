# Migration from GEDCOM to Heredis Database

This document describes the changes made to migrate GeneCrawler from using GEDCOM files to using Heredis SQLite databases directly.

## Summary of Changes

### Files Modified

1. **genecrawler.py** - Main application file
   - Removed `from ged4py import GedcomReader` import
   - Added `from heredis_adapter import HeredisAdapter` import
   - Removed entire `GedcomParser` class (145 lines)
   - Updated docstring: "GEDCOM to Genealogical Database Query Tool" → "Heredis Database to Genealogical Database Query Tool"
   - Updated `Person` docstring: "from GEDCOM file" → "from genealogy database"
   - Updated command-line arguments:
     - `gedcom_file` → `heredis_db`
     - `--gedcom-record` → `--record-id`
   - Updated main() function to use `HeredisAdapter` instead of `GedcomParser`
   - Updated all user-facing messages to reference "Heredis database" instead of "GEDCOM file"

2. **pyproject.toml** - Dependencies file
   - Removed `ged4py = "^0.4.4"` dependency

### Files Created

1. **heredis_adapter.py** (461 lines)
   - `HeredisAdapter` class - Main adapter for reading Heredis databases
   - `Person` dataclass (standalone version for testing)
   - `LocationParser` placeholder (standalone version for testing)
   - Voivodeship mapping with Heredis-specific variations
   - Full context manager support
   - Read-only database access via SQLite URI mode

2. **README_HEREDIS.md**
   - Complete documentation for the Heredis adapter
   - Usage examples
   - Feature descriptions
   - Database structure details
   - Voivodeship detection information

3. **test_integration.py**
   - Integration test script
   - Validates adapter functionality
   - Tests record filtering
   - Shows sample output

4. **MIGRATION_NOTES.md** (this file)
   - Documents all changes made during migration

## Breaking Changes

### Command-Line Interface

**Before (GEDCOM):**
```bash
python3 genecrawler.py Szumiec-Export.ged --limit 10
python3 genecrawler.py Szumiec-Export.ged --gedcom-record 7335288
```

**After (Heredis):**
```bash
python3 genecrawler.py Szumiec.heredis --limit 10
python3 genecrawler.py Szumiec.heredis --record-id 53
```

### Import Changes

If any code imports `GedcomParser`, it must be updated to use `HeredisAdapter`:

**Before:**
```python
from genecrawler import GedcomParser

parser = GedcomParser(gedcom_file, use_nominatim=True)
persons = parser.parse()
```

**After:**
```python
from heredis_adapter import HeredisAdapter

with HeredisAdapter(heredis_db, use_nominatim=True) as adapter:
    persons = adapter.parse()
```

## Benefits of the Migration

1. **No Export Required**: Work directly with Heredis databases without needing to export to GEDCOM
2. **Better Data Fidelity**: Access native Heredis data structures
3. **Read-Only Safety**: Database is always opened in read-only mode
4. **Improved Voivodeship Detection**: Built-in support for Heredis-specific location formats
5. **Better Parent Information**: Direct access to parent relationships from Heredis tables
6. **Simplified Dependencies**: One fewer dependency (ged4py removed)

## Data Quality Improvements

### Voivodeship Detection

The adapter now correctly parses voivodeships from Heredis databases:

- **Before (GEDCOM)**: ~0 persons with voivodeship detected
- **After (Heredis)**: 426+ persons with voivodeship detected

Heredis-specific variations are now recognized:
- "MAŁOPOLSKA" → małopolskie
- "WIELKOPOLSKA" → wielkopolskie
- English names (e.g., "Lesser Poland Voivodeship")

### Parent Information

The adapter extracts full parent names from the Heredis database:
- Father's full name (given name + surname)
- Mother's full name (given name + surname)

This was partially implemented in the GEDCOM parser but is more reliable with direct database access.

## Testing

Run the integration test to verify everything works:

```bash
python3 test_integration.py
```

Expected output:
```
Reading Heredis database: Szumiec.heredis
Skipped 66 person(s) with uncertain names (containing '?')
Found 2435 persons in database
Parsed voivodeships for 426 persons
Found 1760 persons with Polish connections
...
✓ Integration test passed!
```

## Database Schema Used

The adapter reads from these Heredis tables:
- **Individus**: Person records (CodeID, Prenoms, XrefNom, XrefPere, XrefMere, XrefMainEventNaissance, XrefMainEventDeces)
- **Noms**: Surnames (CodeID, Nom)
- **Evenements**: Events (CodeID, DateGed, XrefLieu)
- **Lieux**: Places (CodeID, Ville, Departement, Region, Pays)

## Future Enhancements

Potential improvements for the adapter:
1. Support for marriage/union information
2. Additional event types beyond birth/death
3. Media/photo associations
4. Source citations
5. Notes and research information

## Rollback Instructions

If you need to rollback to the GEDCOM version:

1. Restore `genecrawler.py` from git:
   ```bash
   git checkout HEAD -- genecrawler.py
   ```

2. Restore `pyproject.toml`:
   ```bash
   git checkout HEAD -- pyproject.toml
   ```

3. Reinstall dependencies:
   ```bash
   poetry install
   ```

4. Use GEDCOM files as before:
   ```bash
   python3 genecrawler.py Szumiec-Export.ged
   ```

## Notes

- The adapter always opens databases in read-only mode for safety
- Original Heredis database files are never modified
- The `Person` dataclass format remains unchanged, ensuring compatibility with existing search code
- All genealogical database searchers (Geneteka, PTG, Poznan, BaSIA) continue to work unchanged
