import json
from pathlib import Path

import pytest

from scratrace.osint.sites import SiteRegistry

# Where test_sites.py records domains that failed the reachability check.
# cut_sites.py reads this file to know what to delete from sites.py.
DEAD_SITES_FILE = Path(__file__).resolve().parent / ".dead_sites.json"


@pytest.fixture(scope="session")
def registry() -> SiteRegistry:
    return SiteRegistry()


@pytest.fixture(scope="session")
def sites(registry: SiteRegistry) -> list[str]:
    return registry.all


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "site" in metafunc.fixturenames:
        metafunc.parametrize("site", SiteRegistry().all, ids=lambda s: s)


# --- dead-site collection -------------------------------------------------
# Each test process (including xdist workers) accumulates the domains that
# failed the reachability check here, then merges them into .dead_sites.json
# at session end. Merging (not overwriting) keeps every worker's findings.

def pytest_configure(config: pytest.Config) -> None:
    config._dead_sites = set()  # type: ignore[attr-defined]


def pytest_sessionstart(session: pytest.Session) -> None:
    # Master (or non-xdist) only: start each run from a clean slate so stale
    # entries from previous runs are not carried over (cut_sites.py would try
    # to delete domains already removed). Worker runs leave the file alone.
    if getattr(session.config, "workerinput", None) is None:
        for f in (DEAD_SITES_FILE, *DEAD_SITES_FILE.parent.glob(".dead_sites.*.json")):
            try:
                f.unlink()
            except OSError:
                pass


def record_dead_site(config: pytest.Config, site: str) -> None:
    getattr(config, "_dead_sites").add(site)


def _read_sites(path: Path) -> set[str]:
    if path.exists():
        try:
            return set(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    dead: set[str] = getattr(session.config, "_dead_sites", set())
    workerid = getattr(session.config, "workerinput", {}).get("workerid")

    if workerid:
        # xdist worker: write only this worker's findings to a per-worker file.
        part = DEAD_SITES_FILE.with_suffix(f".{workerid}.json")
        part.write_text(json.dumps(sorted(dead), indent=2))
        return

    # Master (or non-xdist run): merge our own findings + any worker parts,
    # then clean up the parts. Never record username templates (they are not
    # real hosts and must not be fed to cut_sites.py).
    dead_real = {d for d in dead if not d.startswith("{")}
    merged = _read_sites(DEAD_SITES_FILE) | dead_real
    for part in DEAD_SITES_FILE.parent.glob(".dead_sites.*.json"):
        merged |= {d for d in _read_sites(part) if not d.startswith("{")}
        part.unlink(missing_ok=True)
    DEAD_SITES_FILE.write_text(json.dumps(sorted(merged), indent=2))
