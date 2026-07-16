#!/usr/bin/env python3
"""Cut dead domains from the site registry based on a previously written list.

This is a *standalone* script (NOT a pytest test). It reads ``tests/.dead_sites.json``
— produced by ``tests/test_sites.py`` when a domain fails the reachability check —
and removes those exact ``"domain": Sites(...)`` lines from every category dict in
``src/scratrace/osint/sites.py``.

Run it from anywhere:

    python tests/cut_sites.py

All paths are resolved relative to this file, so the working directory does not matter.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Pattern

_HERE = Path(__file__).resolve().parent
_DEAD_SITES_FILE = _HERE / ".dead_sites.json"
_SITES_FILE = (
    _HERE.parent
    / "src"
    / "scratrace"
    / "osint"
    / "sites.py"
)


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


def _build_pattern(domain: str) -> str:
    """Build a regex to match ``"domain": Sites(...)`` in any category dict."""
    # Escape special regex chars in the domain (e.g. dots, hyphens)
    escaped = re.escape(domain)
    return rf'^\s*"{escaped}":\s*Sites\('


def _remove_dead_lines(src: str, dead: set[str]) -> tuple[str, int]:
    """Remove ``"domain": Sites(...)`` lines from the file for every dead domain."""

    # Build a single regex matching any of the dead domains at the start of a line
    parts = [re.escape(d) for d in sorted(dead, key=len, reverse=True)]
    pattern = re.compile(rf'^\s*"({"|".join(parts)})":\s*Sites\(.*$', re.MULTILINE)

    removed = 0
    def _remove(m: re.Match) -> str:
        nonlocal removed
        removed += 1
        return ""  # remove the line entirely (including newline)

    new_src = pattern.sub(_remove, src)

    # Clean up blank lines left by removals (multiple consecutive blank lines → one)
    new_src = re.sub(r'\n\s*\n\s*\n', '\n\n', new_src)

    return new_src, removed


def _verify_not_found(src: str, dead: set[str]) -> set[str]:
    """Return the subset of dead domains that were NOT found in the source."""
    not_found = set()
    for d in dead:
        # Check if the domain still appears as a dict key
        if not re.search(rf'^\s*"{re.escape(d)}":\s*Sites\(', src, re.MULTILINE):
            not_found.add(d)
    return not_found


def main() -> None:
    dead = _load_dead()
    if not dead:
        print("Dead-site list is empty — nothing to cut.")
        return

    if not _SITES_FILE.exists():
        sys.exit(f"sites.py not found at {_SITES_FILE}")

    src = _SITES_FILE.read_text(encoding="utf-8")
    new_src, removed = _remove_dead_lines(src, dead)

    not_found = _verify_not_found(src, dead)

    if removed:
        _SITES_FILE.write_text(new_src, encoding="utf-8")
        print(f"Removed {removed} dead domain(s) from {_SITES_FILE}.")
    else:
        print("No matching domains found — nothing removed.")

    if not_found:
        # Show up to 15 to avoid flooding
        sample = sorted(not_found)[:15]
        print(f"Warning: {len(not_found)} domain(s) from the dead list were "
              f"not present in sites.py (already cut?): {', '.join(sample)}")
        if len(not_found) > 15:
            print(f"  ... and {len(not_found) - 15} more")

    if removed:
        print("Re-run `pytest tests/test_sites.py` to confirm and update the list.")


if __name__ == "__main__":
    main()
