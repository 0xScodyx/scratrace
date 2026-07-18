#!/usr/bin/env python3
"""Cut dead domains from the site registry based on a previously written list.

This is a *standalone* script (NOT a pytest test). It reads ``tests/.dead_sites.json``
— produced by ``tests/test_sites.py`` when a domain fails the reachability check —
and sets ``type_url = NULL`` for those domains in the SQLite database.

Run it from anywhere:

    python tests/cut_sites.py

All paths are resolved relative to this file, so the working directory does not matter.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DEAD_SITES_FILE = _HERE / ".dead_sites.json"
DB_PATH = _HERE.parent / "src" / "scratrace" / "osint" / "SiteRegistry.db"


def _load_dead() -> set[str]:
    if not _DEAD_SITES_FILE.exists():
        sys.exit(f"No dead-site list found at {_DEAD_SITES_FILE}.\n"
                 f"Run `pytest tests/test_sites.py` first to generate it.")
    try:
        data = json.loads(_DEAD_SITES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"Corrupt dead-site list: {exc}")
    if not isinstance(data, list):
        sys.exit("Dead-site list must be a JSON array of domain strings.")
    # keep only bare domains (skip any leftover username templates)
    return {d for d in data if isinstance(d, str) and not d.startswith("{")}


def _remove_dead_from_db(dead: set[str]) -> int:
    """Delete dead domains from the database."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    
    removed = 0
    for domain in dead:
        for (table,) in tables:
            cur.execute(f"SELECT 1 FROM {table} WHERE link = ?", (domain,))
            if cur.fetchone():
                cur.execute(
                    f"DELETE FROM {table} WHERE link = ?",
                    (domain,)
                )
                print(f"[+] DELETED {table}: {domain}")
                removed += 1
                break
        else:
            print(f"[-] NOT FOUND: {domain}")
    
    con.commit()
    con.close()
    return removed


def main() -> None:
    dead = _load_dead()
    if not dead:
        print("Dead-site list is empty — nothing to cut.")
        return

    removed = _remove_dead_from_db(dead)
    
    if removed:
        print(f"Removed {removed} dead domain(s) from the database.")
    else:
        print("No matching domains found — nothing removed.")
    
    if removed:
        print("Re-run `pytest tests/test_sites.py` to confirm and update the list.")


if __name__ == "__main__":
    main()
