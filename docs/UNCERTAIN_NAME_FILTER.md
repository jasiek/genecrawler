# Uncertain Name Filter

## Overview

Records with "?" in their names are now automatically skipped during parsing, as these indicate uncertain or unknown data that would not produce reliable search results.

## Implementation

### Filter Logic (genecrawler.py:292-294)

```python
# Skip persons with uncertain names (containing "?")
if '?' in given_name or '?' in surname:
    return None, 'uncertain'
```

The filter checks both given name and surname fields for the "?" character after name parsing is complete.

### Statistics Tracking (genecrawler.py:241-244)

```python
if skipped_no_name > 0:
    print(f"Skipped {skipped_no_name} person(s) without names")
if skipped_uncertain > 0:
    print(f"Skipped {skipped_uncertain} person(s) with uncertain names (containing '?')")
```

The parser now tracks and reports:
- Persons skipped due to missing names
- Persons skipped due to uncertain names (containing "?")

## Test Results

### From Szumiec-Export.ged:
- **Total persons in GEDCOM**: 2489
- **Skipped (uncertain names)**: 64
- **Persons kept**: 2425

### Examples of Filtered Names:
```
@731170@: Eliza ?
@736543@: ? NO NAME
@7332175@: ? ZUBEL
@7337204@: ? KAIM?
@7331080@: Katarzyna ?
@7331092@: Wojciech ?
```

## Verification

Test with `test_uncertain_filter.py`:

```bash
poetry run python test_uncertain_filter.py
```

Output:
```
✓ SUCCESS: All 12 persons with '?' were filtered out
Total persons parsed: 2425
```

**None of the 2425 persons that passed the filter contain "?" in their names.**

## Impact on Search Quality

Benefits of filtering uncertain names:
1. **Reduces false positives** - "?" would match any character in fuzzy searches
2. **Improves accuracy** - Only searches for persons we're confident about
3. **Saves time** - No wasted searches on uncertain data
4. **Better user experience** - Results are more reliable

## Examples of Names That Pass Filter

All these names passed the filter successfully:
- Jan Paweł SZUMIEC
- Danuta KUDERCZAK
- Anna CZAJOWSKA
- Piotr CZAJOWSKI
- Wojciech PAJOR

## Running the Crawler

The filter is automatically applied when parsing GEDCOM files:

```bash
# Run normally - uncertain names are automatically filtered
poetry run python genecrawler.py Szumiec-Export.ged --limit 10

# Output will show:
# Skipped 64 person(s) with uncertain names (containing '?')
```

## Technical Details

The filter operates during the `_extract_person` method after name parsing is complete. It returns a tuple of `(Person, skip_reason)` where:
- `Person` is `None` if the record should be skipped
- `skip_reason` can be:
  - `'no_name'` - Missing both given name and surname
  - `'uncertain'` - Contains "?" in name
  - `'error'` - Exception during parsing
  - `None` - Person was successfully extracted

This approach allows for detailed statistics tracking and future extensibility for other filtering criteria.
