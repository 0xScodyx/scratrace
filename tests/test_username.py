"""Behavioural tests for the username OSINT checker.

Imports the site registry directly from ``sites.py`` (NOT via ``UserName``) and
probes each link itself. Prints one mark per link straight to the console
stream, AS SOON AS the link is checked: ``.`` when the link is truthful, ``F``
when it lies. The lying links themselves are reported by pytest at the end
(spread-out text, one per failing item).

Each link is probed against 4 nicks:

* 3 guaranteed-taken nicks: admin, username, qwerty.
* 1 random 16-char nick generated at runtime (NEVER hardcoded -- someone could
  register that exact nickname to poison the tool on purpose).

A link is a FALSE POSITIVE when it reacts IDENTICALLY across all 4 nicks --
present for every nick, or absent for every nick. We then null such links in
sites.py (``Sites(info=None, type_url=None)``).

    pytest tests/test_username.py
"""

from __future__ import annotations

import asyncio
import random
import string
from urllib.parse import urlparse

import aiohttp
import pytest

from scratrace.osint.sites import SiteRegistry

TAKEN = ["admin", "username", "qwerty"]

TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _random_nick(length: int = 16) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


# Generated once at import so every parametrized link item is probed under the
# same 4th nick (anti-poisoning: never a hardcoded nickname).
RANDOM_NICK = _random_nick()


def _all_links() -> list[tuple[str, str, object]]:
    """(domain, url_template, payload) for every probed link."""
    reg = SiteRegistry()
    out: list[tuple[str, str, object]] = []
    for cat in (
        "SOCIAL", "FORUMS", "BLOGS", "GAMING", "DEV", "CREATIVE",
        "MISC", "PROFESSIONAL", "PEOPLE_SEARCH", "LINKS",
    ):
        for dom, obj in getattr(reg, cat).items():
            if not obj.info:
                continue
            tmpl = (
                obj.info.get("username")
                or obj.info.get("placeholder", "").replace("{placeholder}", "{username}")
                or obj.info.get("probe")
            )
            if not tmpl:
                continue
            t = obj.type
            if isinstance(t, list) and t:
                out.append((dom, tmpl, t))
            elif "error" in obj.info or "probe" in obj.info:
                out.append((dom, tmpl, obj))
    return out


TOTAL = len(_all_links())


async def _fetch(session, url):
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=TIMEOUT),
            headers=HEADERS, allow_redirects=True,
        ) as resp:
            return resp.status, str(resp.url), await resp.text(errors="replace")
    except Exception:
        return -1, url, ""


def _hit(payload, status, final_url, text) -> bool:
    if isinstance(payload, list) and payload and isinstance(payload[0], str):
        return bool(text) and any(s in text for s in payload)
    if isinstance(payload, list):
        return status in payload
    # redirect object
    if status < 0:
        return False
    if payload.info.get("error"):
        eh = urlparse(payload.info["error"]).netloc.lower().replace("www.", "")
        ep = urlparse(payload.info["error"]).path.rstrip("/")
        fp = urlparse(final_url).path.rstrip("/")
        return not (eh and eh in final_url and (fp == ep or not ep))
    return 200 <= status < 300


async def _probe_one(dom, tmpl, payload, nicks):
    async with aiohttp.ClientSession() as session:
        hits = []
        for nick in nicks:
            status, final_url, text = await _fetch(
                session, tmpl.replace("{username}", nick)
            )
            hits.append(_hit(payload, status, final_url, text))
    return hits


@pytest.mark.osint
@pytest.mark.parametrize("link_id", range(TOTAL))
def test_username_link_truthful(link_id):
    # One test item per link. pytest prints the dots/F itself; the lying links
    # are reported by pytest at the end via the failure message.
    links = _all_links()
    dom, tmpl, payload = links[link_id]
    nicks = TAKEN + [RANDOM_NICK]
    hits = asyncio.run(_probe_one(dom, tmpl, payload, nicks))
    if sum(hits) in (0, len(hits)):
        link = tmpl.replace("{username}", nicks[0])
        pytest.fail(f"lying link: {link}  (domain={dom})")
