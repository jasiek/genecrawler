#!/usr/bin/env python3
"""
GeneCrawler TUI - Browse matched genealogical records with ncurses interface

This script provides a text-based user interface for browsing records stored
in the matched_records database. Features:
- Column-based display of all matched records
- Full-text search across all fields (press '/')
- Keyboard navigation (arrow keys, page up/down)
- Sorted display in ascending order
"""

import curses
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class MatchedRecordsBrowser:
    """TUI for browsing matched genealogical records"""

    def __init__(self):
        self.db_path = Path.home() / '.genecrawler' / 'matched_records.db'
        self.records: List[Dict] = []
        self.filtered_records: List[Dict] = []
        self.current_row = 0
        self.scroll_offset = 0
        self.search_mode = False
        self.details_mode = False
        self.search_query = ""
        self.status_message = ""

        # Column definitions: (name, width, db_field)
        # Special field "_link" will show ✓ or ✗ based on presence of link
        self.columns = [
            ("ID", 8, "person_id"),
            ("Name", 20, "person_given_name"),
            ("Surname", 15, "person_surname"),
            ("Type", 10, "record_type"),
            ("Year", 6, "year"),
            ("Link", 5, "_link"),
            ("Source", 10, "source"),
            ("Parish", 25, "parish"),
            ("Locality", 20, "locality"),
        ]

    def load_records(self) -> bool:
        """Load all records from database"""
        if not self.db_path.exists():
            self.status_message = f"Database not found: {self.db_path}"
            return False

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Load all records sorted by person_surname, person_given_name, year
            cursor.execute('''
                SELECT * FROM matched_records
                ORDER BY person_surname ASC, person_given_name ASC, year ASC
            ''')

            self.records = [dict(row) for row in cursor.fetchall()]
            self.filtered_records = self.records.copy()
            conn.close()

            self.status_message = f"Loaded {len(self.records)} records from database"
            return True

        except Exception as e:
            self.status_message = f"Error loading database: {e}"
            return False

    def filter_records(self, query: str):
        """Filter records based on search query (full text search)"""
        if not query:
            self.filtered_records = self.records.copy()
            return

        query_lower = query.lower()
        self.filtered_records = []

        for record in self.records:
            # Search across all text fields
            searchable_text = " ".join([
                str(record.get('person_id', '')),
                str(record.get('person_given_name', '')),
                str(record.get('person_surname', '')),
                str(record.get('record_type', '')),
                str(record.get('source', '')),
                str(record.get('voivodeship', '')),
                str(record.get('year', '')),
                str(record.get('result_given_name', '')),
                str(record.get('result_surname', '')),
                str(record.get('father_given_name', '')),
                str(record.get('mother_given_name', '')),
                str(record.get('mother_surname', '')),
                str(record.get('parish', '')),
                str(record.get('locality', '')),
            ]).lower()

            if query_lower in searchable_text:
                self.filtered_records.append(record)

        # Reset scroll position when filtering
        self.current_row = 0
        self.scroll_offset = 0

    def get_column_value(self, record: Dict, db_field: str) -> str:
        """Get the display value for a column field

        Handles special fields like _link that need custom logic
        """
        if db_field == "_link":
            # Show ✓ if link is present, blank if not
            link = record.get('link', '')
            return "✓" if link and str(link).strip() else ""
        else:
            # Regular field - just return the value
            return str(record.get(db_field, ''))

    def truncate_text(self, text: str, width: int) -> str:
        """Truncate text to fit within column width"""
        text = str(text) if text else ""
        if len(text) <= width:
            return text.ljust(width)
        return text[:width-1] + "…"

    def draw_header(self, stdscr, height: int, width: int):
        """Draw the column header"""
        try:
            # Draw header line
            header = ""
            for col_name, col_width, _ in self.columns:
                header += col_name.ljust(col_width)[:col_width] + " "

            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(0, 0, header[:width-1].ljust(width-1))
            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

            # Draw separator line
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(1, 0, "─" * (width-1))
            stdscr.attroff(curses.color_pair(1))
        except curses.error:
            pass

    def draw_records(self, stdscr, height: int, width: int):
        """Draw the records table"""
        # Calculate available rows for records (header + separator + status + search)
        available_rows = height - 4

        # Draw visible records
        for i in range(available_rows):
            row_idx = self.scroll_offset + i

            if row_idx >= len(self.filtered_records):
                break

            record = self.filtered_records[row_idx]

            # Build row text
            row_text = ""
            for _, col_width, db_field in self.columns:
                value = self.get_column_value(record, db_field)
                row_text += self.truncate_text(value, col_width) + " "

            # Highlight current row
            y_pos = 2 + i
            if row_idx == self.current_row:
                try:
                    stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                    stdscr.addstr(y_pos, 0, row_text[:width-1].ljust(width-1))
                    stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                except curses.error:
                    pass
            else:
                try:
                    stdscr.addstr(y_pos, 0, row_text[:width-1])
                except curses.error:
                    pass

    def draw_status(self, stdscr, height: int, width: int):
        """Draw the status bar at the bottom"""
        status_y = height - 2

        try:
            # Draw status bar background
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(status_y, 0, " " * (width-1))

            # Show current position and total
            if len(self.filtered_records) > 0:
                pos_text = f" Row {self.current_row + 1}/{len(self.filtered_records)} "
                if len(self.filtered_records) != len(self.records):
                    pos_text += f"(filtered from {len(self.records)}) "
            else:
                pos_text = " No records "

            stdscr.addstr(status_y, 0, pos_text[:width-1])
            stdscr.attroff(curses.color_pair(1))

            # Draw help text
            help_y = height - 1
            help_text = "q:Quit | /:Search | ↑↓:Navigate | PgUp/PgDn:Scroll | Enter:Details"
            try:
                stdscr.addstr(help_y, 0, help_text[:width-1])
            except curses.error:
                pass

        except curses.error:
            pass

    def draw_search_bar(self, stdscr, height: int, width: int):
        """Draw the search bar at the top when in search mode"""
        if not self.search_mode:
            return

        try:
            search_y = 0
            stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            search_text = f"Search: {self.search_query}"
            stdscr.addstr(search_y, 0, search_text[:width-1].ljust(width-1))
            stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

            # Move cursor to end of search text
            curses.curs_set(1)
            cursor_x = min(len(search_text), width - 2)
            stdscr.move(search_y, cursor_x)
        except curses.error:
            pass

    def draw_details(self, stdscr, height: int, width: int):
        """Draw detailed view of selected record"""
        if self.current_row >= len(self.filtered_records):
            return

        record = self.filtered_records[self.current_row]

        # Title
        try:
            title = "=== Record Details ==="
            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(0, 0, title)
            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

            # Display all fields
            fields = [
                ("Person ID", record.get('person_id', '')),
                ("Person Name", f"{record.get('person_given_name', '')} {record.get('person_surname', '')}"),
                ("Record Type", record.get('record_type', '')),
                ("Source", record.get('source', '')),
                ("Year", record.get('year', '')),
                ("Voivodeship", record.get('voivodeship', '')),
                ("Act Number", record.get('act', '')),
                ("Result Name", f"{record.get('result_given_name', '')} {record.get('result_surname', '')}"),
                ("Father", record.get('father_given_name', '')),
                ("Mother", f"{record.get('mother_given_name', '')} {record.get('mother_surname', '')}"),
                ("Parish", record.get('parish', '')),
                ("Locality", record.get('locality', '')),
                ("Link", record.get('link', '')),
                ("Found", record.get('found_timestamp', '')),
            ]

            y_pos = 2
            for label, value in fields:
                if value and str(value).strip():
                    line = f"{label:20s}: {value}"
                    stdscr.addstr(y_pos, 0, line[:width-1])
                    y_pos += 1
                    if y_pos >= height - 3:
                        break

            # Help text
            help_text = "Press Enter to return to list..."
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(height - 1, 0, help_text[:width-1])
            stdscr.attroff(curses.color_pair(1))

        except curses.error:
            pass

    def handle_input(self, key: int, height: int) -> bool:
        """Handle keyboard input. Returns False to quit."""
        available_rows = height - 4

        # Handle details mode first
        if self.details_mode:
            if key in (curses.KEY_ENTER, 10, 13):
                self.details_mode = False
            elif key == ord('q') or key == ord('Q'):
                return False
            # Ignore other keys in details mode
            return True

        # Handle search mode
        if self.search_mode:
            if key == 27:  # ESC
                self.search_mode = False
                self.search_query = ""
                self.filter_records("")
                curses.curs_set(0)
            elif key in (curses.KEY_ENTER, 10, 13):
                self.search_mode = False
                curses.curs_set(0)
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.search_query = self.search_query[:-1]
                self.filter_records(self.search_query)
            elif 32 <= key <= 126:  # Printable characters
                self.search_query += chr(key)
                self.filter_records(self.search_query)
        else:
            # Handle regular navigation mode
            if key == ord('q') or key == ord('Q'):
                return False
            elif key == ord('/'):
                self.search_mode = True
                self.search_query = ""
                curses.curs_set(1)
            elif key == curses.KEY_UP:
                if self.current_row > 0:
                    self.current_row -= 1
                    if self.current_row < self.scroll_offset:
                        self.scroll_offset -= 1
            elif key == curses.KEY_DOWN:
                if self.current_row < len(self.filtered_records) - 1:
                    self.current_row += 1
                    if self.current_row >= self.scroll_offset + available_rows:
                        self.scroll_offset += 1
            elif key == curses.KEY_PPAGE:  # Page Up
                self.current_row = max(0, self.current_row - available_rows)
                self.scroll_offset = max(0, self.scroll_offset - available_rows)
            elif key == curses.KEY_NPAGE:  # Page Down
                self.current_row = min(len(self.filtered_records) - 1,
                                      self.current_row + available_rows)
                self.scroll_offset = min(len(self.filtered_records) - available_rows,
                                        self.scroll_offset + available_rows)
                if self.scroll_offset < 0:
                    self.scroll_offset = 0
            elif key == curses.KEY_HOME:
                self.current_row = 0
                self.scroll_offset = 0
            elif key == curses.KEY_END:
                self.current_row = len(self.filtered_records) - 1
                self.scroll_offset = max(0, len(self.filtered_records) - available_rows)
            elif key in (curses.KEY_ENTER, 10, 13):
                if len(self.filtered_records) > 0:
                    self.details_mode = True

        return True

    def run(self, stdscr):
        """Main TUI loop"""
        # Initialize colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)

        # Setup
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)  # Enable keypad mode
        stdscr.timeout(100)  # Non-blocking input with 100ms timeout

        # Load records
        if not self.load_records():
            stdscr.addstr(0, 0, self.status_message)
            stdscr.addstr(2, 0, "Press any key to exit...")
            stdscr.refresh()
            stdscr.getch()
            return

        if len(self.records) == 0:
            stdscr.addstr(0, 0, "No records found in database.")
            stdscr.addstr(1, 0, f"Database: {self.db_path}")
            stdscr.addstr(3, 0, "Run genecrawler.py to search for records first.")
            stdscr.addstr(5, 0, "Press any key to exit...")
            stdscr.refresh()
            stdscr.getch()
            return

        # Main loop
        running = True
        while running:
            height, width = stdscr.getmaxyx()

            stdscr.clear()

            # Draw UI components based on mode
            if self.details_mode:
                # Draw details view
                self.draw_details(stdscr, height, width)
            else:
                # Draw table view
                if self.search_mode:
                    self.draw_search_bar(stdscr, height, width)
                    # Adjust drawing positions when search bar is visible
                    # We draw the search bar at the top, pushing everything else down
                else:
                    self.draw_header(stdscr, height, width)

                self.draw_records(stdscr, height, width)
                self.draw_status(stdscr, height, width)

            stdscr.refresh()

            # Handle input
            key = stdscr.getch()
            if key != -1:  # Key was pressed
                running = self.handle_input(key, height)


def main():
    """Main entry point"""
    browser = MatchedRecordsBrowser()
    try:
        curses.wrapper(browser.run)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
