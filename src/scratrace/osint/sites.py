"""Registry of OSINT target sites, grouped by category.

Replaces the old res/*.txt files: everything lives here as a class so the
data is importable, typed and de-duplicated in one place.
"""

from dataclasses import asdict, dataclass
import json
import sqlite3
from pathlib import Path
from typing import Callable



@dataclass
class Redirect:
    probe: str = ""
    type_url_probe: str | list[str] | int | list[int] | None = None


@dataclass
class Sites:
    # info keys:
    #   "username" / "placeholder" / "number_phone" / "channel" - public URLs
    #   "probe"  - technical endpoint for the check (data.json urlProbe)
    #   "error"  - URL site redirects to when username does NOT exist (errorUrl)
    # type_url: int (HTTP code) | str (HTML substring) | None (dynamic)
    # reverse_condition: invert the hit decision (e.g. telegram: marker present => ABSENT)
    info: dict | None = None
    type_url: int | list[int] | str | list[str] | Callable | None = None
    reverse_condition: bool = False


# SQLite-backed catalog. Data lives in SiteRegistry.db (see SiteRegistry.schema.sql).
# Each category is a STRICT table; link is UNIQUE, type_url/info are TEXT (JSON or NULL).
_DB_PATH = Path(__file__).parent / "SiteRegistry.db"

CATEGORIES = [
    "SOCIAL", "FORUMS", "BLOGS", "GAMING", "DEV",
    "CREATIVE", "MISC", "PROFESSIONAL", "PEOPLE_SEARCH", "LINKS",
]


class SiteRegistry:
    """Holds the site catalog, backed by SiteRegistry.db (SQLite STRICT).

    The in-code category dicts were migrated to the DB; every accessor below
    reads from the DB via @staticmethod helpers.
    """

    # ------------------------------------------------------------------ #
    # low-level DB access (@staticmethod)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _connect() -> sqlite3.Connection:
        con = sqlite3.connect(_DB_PATH)
        con.execute("PRAGMA journal_mode=WAL;")
        return con

    @staticmethod
    def _serialize_type_url(tu):
        """Sites.type_url -> DB cell stored in the ANY column.

        None -> NULL. list/str -> stored as-is (ANY accepts them). Redirect ->
        asdict() serialized to a tagged JSON string so it survives a round-trip
        and reconstructs flexibly (only the fields present are read back).
        """
        if tu is None:
            return None
        if isinstance(tu, Redirect):
            return json.dumps({"__redirect__": True, **asdict(tu)},
                              ensure_ascii=False)
        return tu  # list[int|str] or str, accepted verbatim by ANY

    @staticmethod
    def _deserialize_type_url(cell):
        """DB cell (ANY) -> Sites.type_url value (None / str / list / Redirect)."""
        if cell is None:
            return None
        # Redirect was stored as a JSON string; list/str were stored verbatim.
        if isinstance(cell, (bytes, str)):
            try:
                raw = json.loads(cell)
            except (json.JSONDecodeError, TypeError):
                return cell  # plain str marker, not JSON
            if isinstance(raw, dict) and raw.get("__redirect__"):
                return Redirect(probe=raw.get("probe", ""),
                                type_url_probe=raw.get("type_url_probe"))
            return raw  # decoded list
        return cell  # already a list (stored natively by ANY)

    @staticmethod
    def _deserialize_info(cell: str | None) -> dict | None:
        if cell is None:
            return None
        return json.loads(cell)

    @staticmethod
    def _row_to_site(row) -> "Sites":
        link, info_cell, tu_cell, rev = row
        return link, Sites(
            info=SiteRegistry._deserialize_info(info_cell),
            type_url=SiteRegistry._deserialize_type_url(tu_cell),
            reverse_condition=bool(rev),
        )

    @staticmethod
    def _table_for(link: str) -> str | None:
        """Find which category table holds `link`, or None if absent."""
        con = SiteRegistry._connect()
        cur = con.cursor()
        for cat in CATEGORIES:
            if cur.execute(f"SELECT 1 FROM {cat} WHERE link = ?", (link,)).fetchone():
                con.close()
                return cat
        con.close()
        return None

    @staticmethod
    def get(link: str) -> "Sites | None":
        """Return the Sites object for `link`, or None if it does not exist."""
        cat = SiteRegistry._table_for(link)
        if cat is None:
            return None
        con = SiteRegistry._connect()
        row = con.cursor().execute(
            f"SELECT link, info, type_url, reverse_condition FROM {cat} WHERE link = ?", (link,)
        ).fetchone()
        con.close()
        if row is None:
            return None
        _, site = SiteRegistry._row_to_site(row)
        return site

    @staticmethod
    def fetch_category(cat: str) -> dict:
        """Return {link: Sites} for one category table."""
        con = SiteRegistry._connect()
        out: dict = {}
        for row in con.cursor().execute(
            f"SELECT link, info, type_url, reverse_condition FROM {cat};"
        ):
            link, site = SiteRegistry._row_to_site(row)
            out[link] = site
        con.close()
        return out

    @staticmethod
    def fetch_all() -> dict:
        """Return {link: Sites} across every category (de-duplicated)."""
        out: dict = {}
        for cat in CATEGORIES:
            out.update(SiteRegistry.fetch_category(cat))
        return out

    # ------------------------------------------------------------------ #
    # high-level API (backwards compatible with the old in-code registry)
    # ------------------------------------------------------------------ #
    @property
    def categories(self) -> dict:
        """Return {category_name(lower): {host: Sites}}."""
        names = [c.lower() for c in CATEGORIES]
        return {name: SiteRegistry.fetch_category(cat.upper())
                for name, cat in zip(names, CATEGORIES)}

    @property
    def all(self) -> list:
        """Flat, de-duplicated, sorted list of every site (key)."""
        seen = set(SiteRegistry.fetch_all().keys())
        return sorted(s for s in seen if "." in s)

    @property
    def https_urls(self) -> list:
        """Sorted list of every site as a full https:// URL."""
        return [f"https://{site}" for site in self.all]

    @property
    def urls_return_code(self) -> dict:
        """Sites checked by HTTP status code (int or list[int])."""
        return {s: o for s, o in self._iter() if isinstance(o.type_url, (int, list))}

    @property
    def urls_return_text(self) -> dict:
        """Sites checked by HTML substring (str or list[str])."""
        return {
            s: o for s, o in self._iter()
            if isinstance(o.type_url, (str, list)) and o.type_url
            and isinstance(o.type_url[0], str)
        }

    def _iter(self):
        yield from SiteRegistry.fetch_all().items()

    def get_type_url(self, site: str) -> str:
        """code / html / redirect / dynamic."""
        o = SiteRegistry.get(site)
        if o is None:
            return "dynamic"
        t = o.type_url
        if isinstance(t, (int, list)) and t and not isinstance(t[0], str):
            return "code"
        if isinstance(t, (str, list)) and t and isinstance(t[0], str):
            return "html"
        if o.info and ("error" in o.info or "probe" in o.info):
            return "redirect"
        return "dynamic"

