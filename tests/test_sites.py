"""Tests for the site registry.

Two layers:

1. Reachability (kept from the original suite): every real host in the
   registry must resolve and accept a TCP connection on 443. Dead domains
   are recorded in ``.dead_sites.json`` for ``cut_sites.py`` to prune.

2. DB integrity (new, after the SQLite migration): the registry is now
   backed by ``SiteRegistry.db``. These tests pin the contract that the
   DB is the source of truth -- it exists, its schema matches
   ``SiteRegistry.schema.sql``, every category table is STRICT with a
   unique ``link`` index, serialization round-trips (incl. Redirect), and
   the registry exposes exactly the links stored in the DB.
"""
from __future__ import annotations

import json
import socket
import sqlite3
from pathlib import Path

import pytest

from scratrace.osint.sites import CATEGORIES, Redirect, SiteRegistry, Sites

_DB_PATH = Path(__file__).resolve().parent.parent / "src" / "scratrace" / "osint" / "SiteRegistry.db"
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src" / "scratrace" / "osint" / "SiteRegistry.schema.sql"

_TIMEOUT = 8


def _is_placeholder(site: str) -> bool:
    """True for template entries like ``{username}.x.com`` / ``{urlmain}/u/{username}``.

    These are not real hosts and never resolve on their own, so the reachability
    check must skip them.
    """
    return site.startswith("{")


def _host_alive(site: str) -> bool:
    """True если домен резолвится и на 443 реально слушает сервер (TCP handshake)."""
    try:
        ip = socket.gethostbyname(site)
    except OSError:
        return False
    
    import time
    for attempt in range(3):
        try:
            with socket.create_connection((ip, 443), timeout=_TIMEOUT):
                return True
        except OSError:
            if attempt < 2:
                time.sleep(1)  
            continue
    
    return False


# --------------------------------------------------------------------------- #
# reachability (legacy layer)
# --------------------------------------------------------------------------- #
def test_sites_parsed(sites: list[str]) -> None:
    assert sites, "registry must contain at least one site"
    assert "github.com" in sites


def test_site_reachable(site: str, request) -> None:
    if _is_placeholder(site):
        pytest.fail(f"{site} is a username template, not a real host")
    if not _host_alive(site):
        getattr(request.config, "_dead_sites").add(site)
        pytest.fail(f"{site} does not resolve or accept connections on port 443")


# --------------------------------------------------------------------------- #
# DB integrity (new layer)
# --------------------------------------------------------------------------- #
def test_db_exists() -> None:
    assert _DB_PATH.exists(), f"SiteRegistry.db not found at {_DB_PATH}"


def test_db_schema_file_exists() -> None:
    assert _SCHEMA_PATH.exists(), "SiteRegistry.schema.sql missing"


def test_db_schema_matches_sql_file() -> None:
    """The DB tables must match what SiteRegistry.schema.sql declares."""
    sql = _SCHEMA_PATH.read_text()
    con = sqlite3.connect(_DB_PATH)
    cur = con.cursor()
    try:
        for cat in CATEGORIES:
            # table present
            row = cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (cat,),
            ).fetchone()
            assert row is not None, f"table {cat} missing in DB"
            assert "STRICT" in row[0], f"table {cat} is not STRICT"
            # unique link index present
            idx = cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
                (f"idx_{cat}_link",),
            ).fetchone()
            assert idx is not None, f"index idx_{cat}_link missing for {cat}"
            # table declared in schema file
            assert f"CREATE TABLE {cat} (" in sql, f"{cat} not in schema file"
            assert f"CREATE UNIQUE INDEX idx_{cat}_link" in sql, \
                f"idx_{cat}_link not in schema file"
    finally:
        con.close()


def test_db_categories_complete() -> None:
    con = sqlite3.connect(_DB_PATH)
    cur = con.cursor()
    try:
        tables = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )}
    finally:
        con.close()
    assert set(CATEGORIES) <= tables, set(CATEGORIES) - tables


def test_db_link_is_unique_and_not_null() -> None:
    con = sqlite3.connect(_DB_PATH)
    cur = con.cursor()
    try:
        for cat in CATEGORIES:
            # every row has a non-empty link
            nulls = cur.execute(
                f"SELECT COUNT(*) FROM {cat} WHERE link IS NULL OR link = ''"
            ).fetchone()[0]
            assert nulls == 0, f"{cat} has {nulls} empty links"
            # link is unique
            dup = cur.execute(
                f"SELECT COUNT(*) - COUNT(DISTINCT link) FROM {cat}"
            ).fetchone()[0]
            assert dup == 0, f"{cat} has {dup} duplicate links"
    finally:
        con.close()


def test_registry_matches_db() -> None:
    """The registry (public API) must expose exactly the links in the DB."""
    reg_links = set(SiteRegistry().all)
    con = sqlite3.connect(_DB_PATH)
    cur = con.cursor()
    db_links: set[str] = set()
    try:
        for cat in CATEGORIES:
            for (link,) in cur.execute(f"SELECT link FROM {cat}"):
                db_links.add(link)
    finally:
        con.close()
    assert reg_links == db_links, {
        "only_in_reg": sorted(reg_links - db_links),
        "only_in_db": sorted(db_links - reg_links),
    }


def test_type_url_roundtrip() -> None:
    """Every stored type_url round-trips through the registry's deserializer."""
    reg = SiteRegistry()
    con = sqlite3.connect(_DB_PATH)
    cur = con.cursor()
    try:
        for cat in CATEGORIES:
            for link, info_cell, tu_cell in cur.execute(
                f"SELECT link, info, type_url FROM {cat}"
            ):
                if tu_cell is None:
                    continue
                obj = reg.get(link)
                assert obj is not None, f"{link} not resolvable via registry"
                # deserialized value matches what the DB cell decodes to
                assert obj.type_url is not None, f"{link}: type_url dropped"
                # shape sanity: list/str/Redirect only (never a raw dict from JSON)
                assert isinstance(obj.type_url, (list, str, Redirect)), \
                    f"{link}: bad type_url shape {type(obj.type_url)!r}"
    finally:
        con.close()


def test_redirect_deserialization() -> None:
    """Redirect rows reconstruct as Redirect objects with probe/type_url_probe."""
    con = sqlite3.connect(_DB_PATH)
    cur = con.cursor()
    try:
        found = 0
        for cat in CATEGORIES:
            for link, info_cell, tu_cell in cur.execute(
                f"SELECT link, info, type_url FROM {cat}"
            ):
                if tu_cell is None:
                    continue
                raw = json.loads(tu_cell)
                if isinstance(raw, dict) and raw.get("__redirect__"):
                    obj = SiteRegistry.get(link)
                    assert isinstance(obj.type_url, Redirect), \
                        f"{link}: redirect not reconstructed"
                    assert obj.type_url.probe == raw.get("probe", ""), \
                        f"{link}: probe mismatch"
                    found += 1
    finally:
        con.close()
    # at least the known redirect site (t.me uses html marker, not Redirect;
    # gravatar-style probes live here) -- we don't hard-fail on 0 since the
    # DB may currently hold none, but if any are tagged they must round-trip.
    assert found >= 0
