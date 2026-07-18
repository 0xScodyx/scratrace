"""Username OSINT checker (OOP style).

``UserName`` aggregates targets from :class:`SiteRegistry` and exposes three
strategies, each returning a ``dict`` mapping category -> list of found URLs:

* :meth:`UserName.by_code`     — match the HTTP status code against ``type_url``
* :meth:`UserName.by_html`     — search the response body for ``type_url`` substrings
* :meth:`UserName.by_redirect` — follow redirects and compare the final URL
* :meth:`UserName.check_all`   — run all three and merge into one dict
"""

from __future__ import annotations

import asyncio

import aiohttp

from scratrace.osint.sites import Redirect, SiteRegistry

from urllib.parse import urlparse

CAT_LOWER = [
    "social", "forums", "blogs", "gaming", "dev", "creative",
    "misc", "professional", "people_search", "links",
]

CONCURRENCY = 80
TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


class UserName:
    """Run username checks across the site registry, grouped by category."""

    def __init__(self, username: str) -> None:
        self.username = username
        self.reg = SiteRegistry()

    # ------------------------------------------------------------------ #
    # internal
    # ------------------------------------------------------------------ #
    def _template(self, obj) -> str | None:
        if not obj.info:
            return None
        if "username" in obj.info:
            return obj.info["username"]
        if "placeholder" in obj.info:
            return obj.info["placeholder"].replace("{placeholder}", "{username}")
        return None

    @staticmethod
    def _hit_redirect(r: Redirect, status: int, final_url: str, text: str, username: str) -> bool:
        """Redirect decision.

        Fact of redirect onto the probe URL is the base signal; type_url_probe
        (if given) refines the decision by status code or HTML substring.
        """

        base = r.probe.replace("{username}", "")
        sp = urlparse(base)
        fp = urlparse(final_url)
        sh = sp.netloc.lower().replace("www.", "")
        fh = fp.netloc.lower().replace("www.", "")
        if not sh or sh != fh:
            return False
        spp = sp.path.rstrip("/")
        fpp = fp.path.rstrip("/")
        if not (fpp == spp or fpp.startswith(spp + "/")):
            return False

        # redirected onto probe
        if r.type_url_probe is None:
            return True
        # refine: status code or HTML substring (str supports {username})
        tu = r.type_url_probe
        if isinstance(tu, int):
            return status == tu
        if isinstance(tu, list):
            for x in tu:
                if isinstance(x, int):
                    if status == x:
                        return True
                elif isinstance(x, str) and x.replace("{username}", username) in text:
                    return True
            return False
        if isinstance(tu, str):
            return tu.replace("{username}", username) in text
        return False

    def _targets(self, kind: str) -> dict[str, list[tuple[str, str, object]]]:
        """Return {category: [(domain, url_template, payload)]} for a check kind."""
        out: dict[str, list[tuple[str, str, object]]] = {c: [] for c in CAT_LOWER}
        # SiteRegistry.categories is {lower_name: {host: Sites}} backed by the DB.
        cats = self.reg.categories
        for cat in CAT_LOWER:
            for dom, obj in cats.get(cat, {}).items():
                t = obj.type_url
                if kind == "code" and isinstance(t, list) and t and not isinstance(t[0], str):
                    tmpl = self._template(obj)
                    if tmpl:
                        out[cat].append((dom, tmpl, t))
                elif kind == "html" and (isinstance(t, str) or (isinstance(t, list) and t and isinstance(t[0], str))):
                    tmpl = self._template(obj)
                    if tmpl:
                        # pass the whole Sites object so reverse_condition survives
                        out[cat].append((dom, tmpl, obj))
                elif kind == "redirect" and isinstance(t, Redirect):
                    out[cat].append((dom, t.probe, obj))
        return out

    async def _fetch(self, session, url):
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                headers=HEADERS, allow_redirects=True,
            ) as resp:
                return resp.status, str(resp.url), await resp.text(errors="replace")
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return -1, url, ""

    async def _collect(self, kind: str) -> dict[str, list[str]]:
        targets = self._targets(kind)
        sem = asyncio.Semaphore(CONCURRENCY)
        result: dict[str, list[str]] = {c: [] for c in CAT_LOWER}

        async def worker(cat, dom, tmpl, payload):
            url = tmpl.replace("{username}", self.username)
            async with sem:
                status, final_url, text = await self._fetch(session, url)
            hit = False
            if kind == "code":
                hit = status in payload
            elif kind == "html":
                marker = payload.type_url
                subs = marker if isinstance(marker, list) else [marker]
                hit = bool(text) and any(s in text for s in subs)
            elif kind == "redirect":
                if status < 0:
                    hit = False
                else:
                    hit = UserName._hit_redirect(payload.type_url, status, final_url, text, self.username)
            if getattr(payload, "reverse_condition", False):
                hit = not hit
            if hit:
                result[cat].append(url)

        async with aiohttp.ClientSession() as session:
            tasks = [
                worker(cat, dom, tmpl, payload)
                for cat, lst in targets.items()
                for (dom, tmpl, payload) in lst
            ]
            await asyncio.gather(*tasks)
        return {c: sorted(v) for c, v in result.items()}

    # ------------------------------------------------------------------ #
    # public: each returns dict[category] -> list[url]
    # ------------------------------------------------------------------ #
    def by_code(self) -> dict[str, list[str]]:
        """Check by HTTP status code. Returns {category: [found urls]}."""
        return asyncio.run(self._collect("code"))

    def by_html(self) -> dict[str, list[str]]:
        """Check by HTML substring. Returns {category: [found urls]}."""
        return asyncio.run(self._collect("html"))

    def by_redirect(self) -> dict[str, list[str]]:
        """Check by final redirect URL. Returns {category: [found urls]}."""
        return asyncio.run(self._collect("redirect"))

    def check_all(self) -> dict[str, list[str]]:
        """Run all three strategies and merge into one {category: [urls]} dict."""
        merged: dict[str, list[str]] = {c: [] for c in CAT_LOWER}
        for fn in (self.by_code, self.by_html, self.by_redirect):
            for cat, urls in fn().items():
                merged[cat].extend(urls)
        return {c: sorted(set(v)) for c, v in merged.items()}

    # ------------------------------------------------------------------ #
    # public helpers used by the interactive app
    # ------------------------------------------------------------------ #
    def targets(self) -> list[tuple[str, str, object]]:
        """Flat list of every (category, url_template, payload) to probe."""
        out: list[tuple[str, str, object]] = []
        for kind in ("code", "html", "redirect"):
            for cat, lst in self._targets(kind).items():
                out.extend((cat, tmpl, payload) for (_, tmpl, payload) in lst)
        return out

    async def _check_sites(self, on_progress=None) -> dict[str, list[str]]:
        """Probe every link across all three strategies, reporting progress.

        ``on_progress`` is called once per completed link (with no args) so the
        UI can advance its spinner/percentage. Returns {category: [found urls]}.
        """
        tasks: list[tuple[str, asyncio.coroutine]] = []
        for kind in ("code", "html", "redirect"):
            for cat, lst in self._targets(kind).items():
                for dom, tmpl, payload in lst:
                    tasks.append((cat, self._probe(cat, dom, tmpl, payload, kind)))
        total = len(tasks)
        found: dict[str, list[str]] = {c: [] for c in CAT_LOWER}
        sem = asyncio.Semaphore(CONCURRENCY)

        async def runner(idx: int, cat: str, coro):
            async with sem:
                url = await coro
            if url:
                found[cat].append(url)
            if on_progress is not None:
                on_progress(cat, url if url else None)

        async with aiohttp.ClientSession() as session:
            self._session = session
            await asyncio.gather(*[runner(i, c, co) for i, (c, co) in enumerate(tasks)])
        del self._session
        return {c: sorted(set(v)) for c, v in found.items()}

    async def _probe(self, cat, dom, tmpl, payload, kind):
        url = tmpl.replace("{username}", self.username)
        status, final_url, text = await self._fetch(self._session, url)
        if kind == "code":
            hit = status in payload
        elif kind == "html":
            marker = payload.type_url
            subs = marker if isinstance(marker, list) else [marker]
            hit = bool(text) and any(s in text for s in subs)
        else:  # redirect
            if status < 0:
                hit = False
            else:
                hit = UserName._hit_redirect(payload.type_url, status, final_url, text, self.username)
        if getattr(payload, "reverse_condition", False):
            hit = not hit
        return url if hit else None

    def check_username_sites(self, on_progress=None) -> dict[str, list[str]]:
        """Synchronous entry point for the app: run the async probe loop."""
        return asyncio.run(self._check_sites(on_progress))
