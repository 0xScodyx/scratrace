"""Test SiteRegistry — DB integrity, serialization, and lookups."""

import json
from pathlib import Path
import pytest
from scratrace.osint.sites import SiteRegistry, Redirect, PLAYWRIGHT, CATEGORIES, Sites

DB_PATH = Path(__file__).resolve().parent.parent / "src" / "scratrace" / "osint" / "SiteRegistry.db"


def test_db_file_exists():
    assert DB_PATH.is_file(), f"Database not found at {DB_PATH}"


@pytest.mark.parametrize("table", CATEGORIES)
def test_table_exists(table):
    cats = SiteRegistry().categories
    assert table.lower() in cats, f"Category {table} missing"


def test_all_categories_have_sites():
    cats = SiteRegistry().categories
    for name, sites in cats.items():
        assert len(sites) > 0, f"Category {name} is empty"


def test_get_known_site():
    site = SiteRegistry.get("github.com")
    assert site is not None
    assert isinstance(site, Sites)


def test_get_nonexistent():
    assert SiteRegistry.get("this-site-does-not-exist.example") is None


def test_get_type_url_category():
    r = SiteRegistry()
    for link in ("facebook.com", "github.com", "reddit.com"):
        t = r.get_type_url(link)
        assert t in ("code", "html", "redirect", "dynamic"), f"Unknown type_url for {link}: {t}"


def test_fetch_all_returns_all():
    all_sites = SiteRegistry.fetch_all()
    assert len(all_sites) > 1000
    assert "github.com" in all_sites


def test_redirect_serialization_roundtrip():
    """Verify Redirect -> JSON -> Redirect round-trip."""
    original = Redirect(final_url="/login", marker=[404, 302])
    serialized = SiteRegistry._serialize_type_url(original)
    assert isinstance(serialized, str)
    raw = json.loads(serialized)
    assert raw.get("__redirect__") is True
    deserialized = SiteRegistry._deserialize_type_url(serialized)
    assert isinstance(deserialized, Redirect)
    assert deserialized.final_url == "/login"  # type: ignore[union-attr]
    assert deserialized.marker == [404, 302]  # type: ignore[union-attr]


def test_redirect_serialization_none_marker():
    original = Redirect(final_url="/404")
    serialized = SiteRegistry._serialize_type_url(original)
    deserialized = SiteRegistry._deserialize_type_url(serialized)
    assert isinstance(deserialized, Redirect)
    assert deserialized.final_url == "/404"  # type: ignore[union-attr]
    assert deserialized.marker is None  # type: ignore[union-attr]


def test_serialize_none():
    assert SiteRegistry._serialize_type_url(None) is None


def test_serialize_int_list():
    result = SiteRegistry._serialize_type_url([200, 301, 302])
    assert result == [200, 301, 302]


def test_deserialize_plain_str():
    result = SiteRegistry._deserialize_type_url("hello world")
    assert result == "hello world"


def test_deserialize_int_list():
    result = SiteRegistry._deserialize_type_url([200, 404])
    assert result == [200, 404]


def test_playwright_constant():
    assert PLAYWRIGHT == -999
