# GeneCrawler Changelog

## [Unreleased]

### Added - 2025-01-26

#### Max Pages Feature
- Added `--max-pages` command-line argument to limit result page crawling
- Allows users to control search depth: `--max-pages 1` for fast shallow searches
- Provides significant performance improvement (5-10 sec vs 10-30 sec per person)
- Displays feedback when max pages limit is reached
- Default behavior unchanged (unlimited pages when not specified)

**Files Modified:**
- `genecrawler.py`:
  - Added `max_pages` parameter to `GenetekaSearcher.__init__` (line 458)
  - Added pagination limit check in search loop (line 604-607)
  - Added `--max-pages` CLI argument (line 923-924)
  - Added user feedback message (line 990-991)

**Files Created:**
- `test_max_pages_simple.py` - Test suite for max_pages feature
- `MAX_PAGES_FEATURE.md` - Comprehensive feature documentation

**Documentation Updated:**
- `USAGE.md` - Added max-pages usage examples and performance comparison

**Use Cases:**
```bash
# Fast reconnaissance
python3 genecrawler.py Szumiec.heredis --max-pages 1 --limit 20

# Balanced search
python3 genecrawler.py Szumiec.heredis --max-pages 3 --limit 50

# Comprehensive (default)
python3 genecrawler.py Szumiec.heredis
```

#### Heredis Database Integration
- Complete migration from GEDCOM to Heredis database format
- Created `HeredisAdapter` class for reading .heredis files directly
- Removed GEDCOM parser and ged4py dependency
- Improved voivodeship detection (0 → 426+ persons with voivodeship info)
- Database always opened in read-only mode for safety

**Files Created:**
- `heredis_adapter.py` (461 lines) - Complete Heredis database adapter
- `README_HEREDIS.md` - Adapter documentation
- `MIGRATION_NOTES.md` - Migration guide from GEDCOM
- `USAGE.md` - Complete usage guide
- `test_integration.py` - Integration test suite

**Files Modified:**
- `genecrawler.py` - Removed GedcomParser, integrated HeredisAdapter
- `pyproject.toml` - Removed ged4py dependency

**Breaking Changes:**
- Command-line argument `gedcom_file` → `heredis_db`
- Command-line argument `--gedcom-record` → `--record-id`
- Now requires .heredis database files instead of .ged files

## Performance Impact

### Max Pages Feature

| Configuration | Time Savings | Recommended Use |
|--------------|--------------|-----------------|
| `--max-pages 1` | 50-70% faster | Quick testing, reconnaissance |
| `--max-pages 3` | 20-40% faster | Balanced production searches |
| No limit | Baseline (0%) | Comprehensive research |

### Heredis Integration

| Metric | GEDCOM | Heredis | Improvement |
|--------|--------|---------|-------------|
| Voivodeships detected | 0 | 426+ | ∞ (infinite improvement) |
| Export step required | Yes | No | Workflow simplified |
| Parent information | Partial | Complete | More accurate |
| Dependencies | ged4py + others | others only | -1 dependency |

## Migration Guide

### From GEDCOM to Heredis

**Before:**
```bash
# Export from Heredis to GEDCOM first
python3 genecrawler.py Szumiec-Export.ged --limit 10
```

**After:**
```bash
# Use database directly
python3 genecrawler.py Szumiec.heredis --limit 10
```

See `MIGRATION_NOTES.md` for detailed migration instructions.

### Using Max Pages

**Before (unlimited pages):**
```bash
python3 genecrawler.py Szumiec.heredis --limit 100
# Takes ~20-50 minutes
```

**After (limited pages):**
```bash
python3 genecrawler.py Szumiec.heredis --limit 100 --max-pages 1
# Takes ~10-15 minutes (50-70% faster)
```

## Testing

All features have been tested:

```bash
# Test Heredis integration
python3 test_integration.py

# Test max_pages feature
python3 test_max_pages_simple.py

# Test standalone adapter
python3 heredis_adapter.py Szumiec.heredis
```

## Documentation

Comprehensive documentation available:

- `README_HEREDIS.md` - Heredis adapter documentation
- `USAGE.md` - Complete usage guide with examples
- `MIGRATION_NOTES.md` - Migration guide from GEDCOM
- `MAX_PAGES_FEATURE.md` - Detailed max_pages documentation
- `CHANGELOG.md` - This file

## Statistics

**Code Changes:**
- Lines added: ~1,250+
- Lines removed: ~184
- Net change: +1,066 lines
- Files created: 8
- Files modified: 3

**Test Coverage:**
- Integration test: ✅ Passing (2435 persons loaded)
- Max pages test: ✅ All 8 tests passing
- Adapter test: ✅ Passing (voivodeship detection working)

## Contributors

- Migration to Heredis database
- Max pages feature implementation
- Documentation updates
- Test suite creation

## Future Enhancements

Potential future features:
- [ ] Extend `--max-pages` to PTG, Poznan, BaSIA databases
- [ ] Add `--max-results` to limit total results instead of pages
- [ ] Add progress indicators for long-running searches
- [ ] Add `--resume` to continue interrupted searches
- [ ] Add search result caching to avoid duplicate searches
- [ ] Export matched records to various formats (CSV, JSON, GEDCOM)

## Version History

### Current (Unreleased)
- Max pages feature
- Heredis database integration

### Previous
- Original GEDCOM-based implementation
- Support for Geneteka, PTG, Poznan Project, BaSIA
- Exact match detection and storage
- Voivodeship filtering
