# Voivodeship Parsing Feature

## Overview

The GeneCrawler now parses voivodeship (Polish administrative regions) information from GEDCOM location data. This allows for more targeted searches in genealogical databases by filtering results by region.

## Implementation

### 1. Location Parser (`LocationParser` class)

- **Purpose**: Extracts voivodeship information from GEDCOM place strings
- **Format**: GEDCOM places follow the format: `Town, Area code, County, Region, Country, Subdivision`
- **Mapping**: Supports 16 Polish voivodeships with various name formats:
  - Polish names (MAŁOPOLSKA, WIELKOPOLSKIE, etc.)
  - English names (LESSER POLAND VOIVODESHIP, GREATER POLAND, etc.)
  - Various cases and spellings

### 2. Supported Voivodeships

| Standardized Name       | Variants Recognized                                                   |
|------------------------|-----------------------------------------------------------------------|
| dolnośląskie           | DOLNOŚLĄSKIE, LOWER SILESIAN VOIVODESHIP, LOWER SILESIA             |
| kujawsko-pomorskie     | KUJAWSKO-POMORSKIE, KUYAVIAN-POMERANIAN VOIVODESHIP                 |
| lubelskie              | LUBELSKIE, LUBLIN VOIVODESHIP                                        |
| lubuskie               | LUBUSKIE, LUBUSZ VOIVODESHIP                                         |
| łódzkie                | ŁÓDZKIE, LODZKIE, LODZ VOIVODESHIP                                   |
| małopolskie            | MAŁOPOLSKIE, MAŁOPOLSKA, LESSER POLAND VOIVODESHIP, LESSER POLAND    |
| mazowieckie            | MAZOWIECKIE, MASOVIAN VOIVODESHIP, MASOVIA                           |
| opolskie               | OPOLSKIE, OPOLE VOIVODESHIP                                          |
| podkarpackie           | PODKARPACKIE, SUBCARPATHIAN VOIVODESHIP, SUBCARPATHIA               |
| podlaskie              | PODLASKIE, PODLASIE, PODLACHIA                                       |
| pomorskie              | POMORSKIE, POMERANIAN VOIVODESHIP, POMERANIA                         |
| śląskie                | ŚLĄSKIE, SLASKIE, SILESIAN VOIVODESHIP, SILESIA                     |
| świętokrzyskie         | ŚWIĘTOKRZYSKIE, SWIETOKRZYSKIE, HOLY CROSS VOIVODESHIP             |
| warmińsko-mazurskie    | WARMIŃSKO-MAZURSKIE, WARMIAN-MASURIAN VOIVODESHIP                   |
| wielkopolskie          | WIELKOPOLSKIE, GREATER POLAND VOIVODESHIP, GREATER POLAND           |
| zachodniopomorskie     | ZACHODNIOPOMORSKIE, WEST POMERANIAN VOIVODESHIP, WEST POMERANIA     |

### 3. Person Data Model

The `Person` dataclass now includes:
- `birth_voivodeship: Optional[str]` - Parsed voivodeship for birth location
- `death_voivodeship: Optional[str]` - Parsed voivodeship for death location

### 4. Optional Nominatim Integration

The parser can optionally use the Nominatim geocoding API as a fallback for locations not explicitly containing voivodeship information:

```bash
# Enable Nominatim geocoding
poetry run python genecrawler.py Szumiec-Export.ged --use-nominatim
```

**Note**: Nominatim requests are rate-limited and slower. Use only when needed.

## Usage Examples

### Basic Parsing (from GEDCOM data only)

```python
from genecrawler import GedcomParser

parser = GedcomParser("Szumiec-Export.ged", use_nominatim=False)
persons = parser.parse()

# Filter by voivodeship
malopolskie_persons = [p for p in persons if p.birth_voivodeship == "małopolskie"]
```

### With Nominatim Fallback

```python
parser = GedcomParser("Szumiec-Export.ged", use_nominatim=True)
persons = parser.parse()
```

### Using in Searchers

The voivodeship information is available in the `Person` object and can be used when filling search forms:

```python
# Example from GenetekaSearcher
if person.birth_voivodeship:
    page.select_option('select[name="w"]', person.birth_voivodeship)
```

## Test Results

From the test dataset (Szumiec-Export.ged):
- **Total persons**: 2489
- **With parsed birth voivodeship**: 423 (17.0%)
- **With parsed death voivodeship**: 183 (7.4%)

### Voivodeship Distribution (top 5)
1. małopolskie: 278 persons
2. podkarpackie: 115 persons
3. kujawsko-pomorskie: 27 persons
4. mazowieckie: 2 persons
5. dolnośląskie: 1 person

## Testing

Two test files are provided:

1. **test_location_parser.py** - Unit tests for LocationParser
   ```bash
   poetry run python test_location_parser.py
   ```

2. **test_parsing.py** - Integration test with full GEDCOM parsing
   ```bash
   poetry run python test_parsing.py
   ```

## Future Enhancements

- **TODO**: Implement voivodeship selection in database searchers (Geneteka, PTG, Poznan Project, BaSIA)
- Add caching for Nominatim results to reduce API calls
- Support for historical voivodeship names (pre-1999 administrative divisions)
- Add confidence scoring for parsed voivodeships

## Technical Notes

- Voivodeship parsing is cached per location string to improve performance
- The parser handles various encodings and diacritics (ł, ą, ę, etc.)
- Non-Polish locations (e.g., Canada, USA) return `None` for voivodeship
- Empty or malformed location strings are handled gracefully
