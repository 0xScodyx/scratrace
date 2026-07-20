#!/usr/bin/env python3
"""Check that all expected tables exist in the database."""

import sqlite3
from pathlib import Path
import pytest

DB_PATH = Path(__file__).resolve().parent.parent / "src" / "scratrace" / "osint" / "SiteRegistry.db"
EXPECTED_TABLES = [
    "SOCIAL", "FORUMS", "BLOGS", "GAMING", "DEV", "CREATIVE",
    "MISC", "PROFESSIONAL", "PEOPLE_SEARCH", "LINKS"
]





@pytest.mark.parametrize("table", EXPECTED_TABLES)
def test_table_exists(table):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        rows = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        existing = {row[0] for row in rows}
    assert table in existing, f"Table {table} missing"
