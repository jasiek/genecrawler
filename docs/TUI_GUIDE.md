# GeneCrawler TUI Guide

The GeneCrawler TUI (Text User Interface) provides a convenient way to browse matched genealogical records stored in your local database using a terminal-based interface.

## Overview

The TUI displays matched records in a table format with columns showing key information about each match. You can scroll through records, search across all fields, and view detailed information about individual records.

## Starting the TUI

```bash
python3 genecrawler_tui.py
```

The TUI will automatically load all records from `~/.genecrawler/matched_records.db` and display them sorted by surname, given name, and year.

## Interface Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ ID       Name                Surname        Type      Year  Link ... │  <- Column Headers
├──────────────────────────────────────────────────────────────────────┤
│ @57@     Anna                CZAJOWSKA      births    1918  ✓    ... │
│ @58@     Jan                 KOWALSKI       deaths    1920       ... │  <- Records
│ @59@     Maria               NOWAK          marriages 1945  ✓    ... │  <- (highlighted row)
│ ...                                                                   │
├──────────────────────────────────────────────────────────────────────┤
│ Row 3/1377                                                            │  <- Status Bar
│ q:Quit | /:Search | ↑↓:Navigate | PgUp/PgDn:Scroll | Enter:Details  │  <- Help Text
└──────────────────────────────────────────────────────────────────────┘
```

## Columns Displayed

- **ID**: Person ID from your genealogy database
- **Name**: Given name of the person
- **Surname**: Family name of the person
- **Type**: Record type (births, deaths, marriages)
- **Year**: Year of the event
- **Link**: Shows ✓ if a link to the record is available (blank if no link)
- **Source**: Database source (Geneteka, PTG, etc.)
- **Parish**: Parish name where record was found
- **Locality**: Town or locality name

## Keyboard Controls

### Navigation
- **↑ / ↓** (Arrow Keys): Move up/down one row
- **Page Up / Page Down**: Scroll up/down by one page
- **Home**: Jump to first record
- **End**: Jump to last record

### Search
- **/** (Slash): Enter search mode
  - Type your search query
  - Search is performed in real-time as you type
  - Searches across ALL fields: names, years, parishes, localities, etc.
  - **Backspace**: Delete last character
  - **Enter**: Exit search mode (keeps filtered results)
  - **ESC**: Cancel search and show all records

### Actions
- **Enter**:
  - In table view: View detailed information about the selected record
  - In details view: Return to table view
- **q / Q**: Quit the TUI (works in any mode)

## Search Mode

When you press `/`, a search bar appears at the top of the screen:

```
Search: anna 1918
```

The TUI performs full-text search across all fields:
- Person names (given name and surname)
- Record type
- Year
- Source database
- Parish and locality names
- Parent names
- Voivodeship

Results are filtered in real-time as you type. The status bar shows how many records match your search.

### Search Examples

```
/kowalski          → Find all records with "kowalski" anywhere
/1918              → Find all records from year 1918
/geneteka          → Find all records from Geneteka source
/krakow            → Find records with "krakow" in parish or locality
/anna kowalski     → Find records containing both "anna" and "kowalski"
```

## Detailed View

Press **Enter** on any record to see full details. The view will remain open so you can read all the information.

```
=== Record Details ===

Person ID           : @57@
Person Name         : Anna CZAJOWSKA
Record Type         : births
Source              : Geneteka
Year                : 1918
Voivodeship         : małopolskie
Parish              : Modlniczka
Locality            : Modlniczka
Father              : Jan
Mother              : Marianna PSTRUŚ
Link                : https://geneteka.genealodzy.pl/...
Found               : 2024-10-26 23:07:15

Press Enter to return to list...
```

Press **Enter** again to return to the table view. The selected row will still be highlighted, making it easy to compare multiple records.

## Status Bar

The status bar at the bottom shows:
- Current row position (e.g., "Row 3/1377")
- Number of filtered records when searching (e.g., "Row 1/15 (filtered from 1377)")

## Tips

1. **Quick search**: Press `/` and start typing immediately - no need to clear previous searches
2. **Case insensitive**: All searches are case-insensitive
3. **Partial matches**: Search for partial words (e.g., "krak" will match "Kraków")
4. **Multiple terms**: Search for multiple terms to narrow results (e.g., "anna 1918 krakow")
5. **Empty database**: If no records are shown, run `genecrawler.py` first to search and store matches
6. **Terminal size**: The TUI adapts to your terminal size, but works best with at least 120 columns width

## Troubleshooting

### "Database not found" error
The TUI looks for `~/.genecrawler/matched_records.db`. Run the main genecrawler tool first:
```bash
python3 genecrawler.py your-database.heredis --limit 10
```

### "No records found in database"
The database exists but has no matched records. Run more searches with genecrawler to populate it.

### Display issues
- Ensure your terminal supports at least 80 columns and 24 rows
- Some terminals may not support all color schemes - try a different terminal emulator
- If text looks garbled, try resizing your terminal window

### Search not working
- Make sure you're in search mode (press `/` first)
- Search bar should appear at the top with a cursor
- Try pressing ESC to exit search mode and try again

## Database Location

Matched records are stored in:
```
~/.genecrawler/matched_records.db
```

You can also query this database directly with sqlite3:
```bash
sqlite3 ~/.genecrawler/matched_records.db "SELECT * FROM matched_records LIMIT 10"
```

## Implementation Notes

The TUI is built using Python's `curses` library, which provides terminal-independent screen manipulation. It:
- Reads the SQLite database in read-only mode
- Sorts records by surname, given name, and year in ascending order
- Performs full-text search by concatenating all searchable fields
- Uses color pairs for highlighting (header, selected row, search bar)
- Automatically adapts to terminal window size

The TUI does not modify the database - it only reads and displays records.
