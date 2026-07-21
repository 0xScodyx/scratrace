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
import contextlib
from pathlib import Path

import aiohttp

from scratrace.osint.log import scratrace_log, ERROR, WARNING, INFO
from scratrace.osint.sites import Redirect, SiteRegistry, PLAYWRIGHT, INFO_KEY_TO_CLASS

from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PwTimeoutError
from playwright_stealth import Stealth
from scratrace.osint.pw_scripts import get_checker, get_dork_checker, _DORK_REGISTRY

CAT_LOWER = [
    "social", "forums", "blogs", "gaming", "dev", "creative",
    "misc", "professional", "people_search", "links", "other_info",
]

CONCURRENCY = 80
TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
PW_LAUNCH_ARGS = [
    "--headless=new",
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-infobars",
]


def _extract_domain(url: str) -> str:
    """Вернуть домен второго уровня (tiktok.com, github.com, ...)."""
    host = urlparse(url).hostname or ""
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


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
    def _hit_redirect(r: Redirect, entry_url: str, status: int, final_url: str, text: str, username: str) -> bool:
        """Redirect decision.

        Базовый сигнал — ФАКТ редиректа: final_url ушёл с точки входа
        ``entry_url`` (из info.username). Если не ушёл — профиль есть
        (запрос остался на профиле). ``r.final_url`` — куда именно сайт
        кидает (шаблон/подстрока); ``r.marker`` уточняет уже на финальной
        странице (html/код).
        """

        sp = urlparse(entry_url.replace("{username}", username))
        fp = urlparse(final_url)
        sh = sp.netloc.lower().replace("www.", "")
        fh = fp.netloc.lower().replace("www.", "")
        if not sh or sh != fh:
            return False
        spp = sp.path.rstrip("/")
        fpp = fp.path.rstrip("/")
        # нет редиректа — остались на профиле => профиль есть
        if fpp == spp or fpp.startswith(spp + "/"):
            return True

        # сайт нас перекинул — профиля на точке входа нет.
        # r.final_url — шаблон «страницы отсутствия» (куда кидает, если
        # профиля нет). Если final_url ему соответствует — профиля нет.
        if r.final_url:
            fu = r.final_url.replace("{username}", username)
            if fu in final_url:
                return False  # кинуло на страницу отсутствия => нет профиля
        # уточняем маркером на финальной странице (html/код)
        if r.marker is None:
            return True
        m = r.marker
        if isinstance(m, int):
            return status == m
        if isinstance(m, list):
            for x in m:
                if isinstance(x, int):
                    if status == x:
                        return True
                elif isinstance(x, str) and x.replace("{username}", username) in text:
                    return True
            return False
        if isinstance(m, str):
            return m.replace("{username}", username) in text
        return False

    def _targets(self, kind: str) -> dict[str, list[tuple[str, str, object]]]:
        """Return {category: [(domain, url_template, payload)]} for a check kind."""
        out: dict[str, list[tuple[str, str, object]]] = {c: [] for c in CAT_LOWER}
        # SiteRegistry.categories is {lower_name: {host: Sites}} backed by the DB.
        cats = self.reg.categories
        for cat in CAT_LOWER:
            for dom, obj in cats.get(cat, {}).items():
                t = obj.type_url
                if kind == "browser" and t == PLAYWRIGHT:
                    tmpl = self._template(obj)
                    if tmpl:
                        # имя скрипта = link без www; класс из info-ключа
                        script = dom[4:] if dom.startswith("www.") else dom
                        cls = INFO_KEY_TO_CLASS.get(next(iter(obj.info))) if obj.info else None
                        out[cat].append((dom, tmpl, (obj, script, cls)))
                elif kind == "code" and (
                    (isinstance(t, int) and t != PLAYWRIGHT)
                    or (isinstance(t, list) and t and not isinstance(t[0], str))
                ):
                    tmpl = self._template(obj)
                    if tmpl:
                        out[cat].append((dom, tmpl, t))
                elif kind == "html" and (isinstance(t, str) or (isinstance(t, list) and t and isinstance(t[0], str))):
                    tmpl = self._template(obj)
                    if tmpl:
                        # pass the whole Sites object so reverse_condition survives
                        out[cat].append((dom, tmpl, obj))
                elif kind == "redirect" and isinstance(t, Redirect):
                    tmpl = self._template(obj)
                    if tmpl:
                        # URL берём из info (точка входа), Redirect — маркер
                        out[cat].append((dom, tmpl, t))
                
        return out

    async def _fetch(self, session, url, allow_redirect: bool = True):
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                headers=HEADERS, allow_redirects=allow_redirect,
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
                status, final_url, text = await self._fetch(
                    session, url, allow_redirect=(kind == "redirect")
                )
            hit = False
            if kind == "code":
                if isinstance(payload, int):
                    payload = [payload]
                hit = status in payload
            elif kind == "html":
                marker = payload.type_url
                subs = marker if isinstance(marker, list) else [marker]
                hit = bool(text) and any(s in text for s in subs)
            elif kind == "redirect":
                if status < 0:
                    hit = False
                else:
                    hit = UserName._hit_redirect(payload, url, status, final_url, text, self.username)
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

    async def _run_browser_check(self, page, script: str, cls: str | None) -> bool:
        """Выполнить профильный playwright-скрипт. Возвращает True = профиль есть."""
        fn = get_checker(cls or "UserName", script)
        if fn is None:
            return False
        try:
            return bool(await fn(page, self.username))
        except NotImplementedError:
            return False

    async def _run_dork_check(self, page, name: str) -> dict[str, str]:
        """Выполнить доркинг-скрипт. Возвращает {url: сниппет}."""
        fn = get_dork_checker(name)
        if fn is None:
            return {}
        result = await fn(page, self.username)
        return result if isinstance(result, dict) else {}

    async def _open_page(self, browser, url: str):
        """Открыть страницу на нужном URL (browser берёт на себя launch/goto).

        Скрипт получает уже загруженный page — launch/goto/ожидание
        загрузки вынесены сюда, чтобы в pw_scripts писать только анализ DOM.
        """
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        context = await browser.new_context(extra_http_headers=HEADERS)
        page = await context.new_page()
        try:
            await page.goto(url, timeout=TIMEOUT * 1000, wait_until="commit")
        except PwTimeoutError:
            scratrace_log(f"browser goto timeout (continuing): {url}", type=WARNING)
        return page

    async def _page_check(self, browser, url: str, payload) -> tuple[str, bool]:
        """Открыть page на url и прогнать профильный playwright-скрипт."""
        obj, script, cls = payload
        page = await self._open_page(browser, url)
        try:
            hit = await self._run_browser_check(page, script, cls)
        finally:
            with contextlib.suppress(Exception):
                await page.context.close()
        if getattr(obj, "reverse_condition", False):
            hit = not hit
        return url, hit

    async def _collect_browser(self) -> dict[str, list[str]]:
        """Прогнать профильные playwright-скрипты."""
        targets = self._targets("browser")
        result: dict[str, list[str]] = {c: [] for c in CAT_LOWER}
        flat = [
            (cat, tmpl, payload)
            for cat, lst in targets.items()
            for (_, tmpl, payload) in lst
        ]
        if not flat:
            return {c: [] for c in CAT_LOWER}

        async with async_playwright() as pw:
            chromium = await pw.chromium.launch(
                headless=False,
                args=PW_LAUNCH_ARGS,
            )
            try:
                for cat, tmpl, payload in flat:
                    url = tmpl.replace("{username}", self.username)
                    got_url, hit = await self._page_check(chromium, url, payload)
                    if hit:
                        result[cat].append(got_url)
            finally:
                await chromium.close()
        return {c: sorted(v) for c, v in result.items()}

    def _dork_targets(self) -> list[str]:
        return list(_DORK_REGISTRY.keys())

    async def _collect_dorking(self, existing_urls: set[str], existing_domains: set[str]) -> list[str]:
        """Прогнать доркинг-скрипты.
        existing_urls — URL из обычных категорий для дедупа.
        existing_domains — домены из обычных категорий (дедуп по домену).
        Возвращает list[str]: отформатированные "url — сниппет" для other_info.
        """
        names = self._dork_targets()
        if not names:
            return []

        results: list[str] = []
        for name in names:
            for url, text in (await self._run_dork_check(None, name)).items():
                clean = url.rstrip("/")
                if clean in existing_urls:
                    continue
                if _extract_domain(clean) in existing_domains:
                    continue
                results.append(f"{url} — {text}")
        return results

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

    def by_browser(self) -> dict[str, list[str]]:
        """Check via playwright scripts (SPA/antibot/login-wall sites)."""
        return asyncio.run(self._collect_browser())

    def check_all(self) -> dict[str, list[str]]:
        """Run all strategies and merge into one {category: [urls]} dict."""
        merged: dict[str, list[str]] = {c: [] for c in CAT_LOWER}
        for fn in (self.by_code, self.by_html, self.by_redirect, self.by_browser):
            for cat, urls in fn().items():
                merged[cat].extend(urls)
        return {c: sorted(set(v)) for c, v in merged.items()}

    # ------------------------------------------------------------------ #
    # public helpers used by the interactive app
    # ------------------------------------------------------------------ #
    def targets(self) -> list[tuple[str, str, object]]:
        """Flat list of every (category, url_template, payload) to probe."""
        out: list[tuple[str, str, object]] = []
        for kind in ("code", "html", "redirect", "browser"):
            for cat, lst in self._targets(kind).items():
                out.extend((cat, tmpl, payload) for (_, tmpl, payload) in lst)
        return out

    async def _check_sites(self, on_progress=None) -> dict[str, list[str]]:
        """Probe every link across all strategies + dorking.

        ``on_progress`` is called once per completed link (with no args) so the
        UI can advance its spinner/percentage. Returns {category: [found urls]}.
        """
        found: dict[str, list[str]] = {c: [] for c in CAT_LOWER}
        sem = asyncio.Semaphore(CONCURRENCY)

        async def _run(cat: str, url: str | None) -> None:
            if url:
                found[cat].append(url)
            if on_progress is not None:
                on_progress(cat, url)

        async def runner(cat: str, coro) -> None:
            async with sem:
                url = await coro
            await _run(cat, url)

        dork_names = self._dork_targets()
        tasks: list = []

        # HTTP probes — запускаем как задачи, не ждут PW
        for kind in ("code", "html", "redirect"):
            for cat, lst in self._targets(kind).items():
                for dom, tmpl, payload in lst:
                    tasks.append(
                        asyncio.ensure_future(
                            runner(cat, self._probe(cat, dom, tmpl, payload, kind))
                        )
                    )

        async with aiohttp.ClientSession() as session:
            self._session = session

            if dork_names:
                async with async_playwright() as pw:
                    chromium = await pw.chromium.launch(
                        headless=False,
                        args=PW_LAUNCH_ARGS,
                    )
                    try:
                        for name in dork_names:
                            tasks.append(
                                asyncio.ensure_future(
                                    self._dork_runner(chromium, name, _run)
                                )
                            )

                        for cat, lst in self._targets("browser").items():
                            for dom, tmpl, payload in lst:
                                url = tmpl.replace("{username}", self.username)
                                tasks.append(
                                    asyncio.ensure_future(
                                        self._browser_runner(
                                            chromium, cat, url, payload, sem, _run
                                        )
                                    )
                                )

                        await asyncio.gather(*tasks)
                    finally:
                        await chromium.close()
            else:
                await asyncio.gather(*tasks)

        del self._session

        # --- dedup: к этому моменту already all результаты в found ---
        existing: set[str] = set()
        existing_domains: set[str] = set()
        for cat in CAT_LOWER:
            if cat == "other_info":
                continue
            for u in found[cat]:
                if u.startswith(("http://", "https://")):
                    clean = u.rstrip("/")
                    existing.add(clean)
                    existing_domains.add(_extract_domain(clean))

        raw = found.get("other_info", [])
        deduped = []
        seen_other_domains: set[str] = set()
        for item in raw:
            if item.startswith("[") and "\n" in item:
                domain_only = item.split("\n", 1)[0].strip("[]")
            else:
                domain_only = item.split(" — ", 1)[0].rstrip("/")
            if _extract_domain(domain_only) in existing_domains:
                continue
            if domain_only in seen_other_domains:
                continue
            seen_other_domains.add(domain_only)
            deduped.append(item)
        found["other_info"] = deduped

        return {c: sorted(v) for c, v in found.items()}

    async def _browser_runner(
        self,
        chromium,
        cat: str,
        url: str,
        payload,
        sem: asyncio.Semaphore,
        on_result,
    ) -> None:
        """Browser check with shared chromium."""
        async with sem:
            got_url, hit = await self._page_check(chromium, url, payload)
        await on_result(cat, got_url if hit else None)

    async def _dork_runner(self, browser, name: str, on_result) -> None:
        page = None
        try:
            if browser is not None:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                )
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)
            for url, text in (await self._run_dork_check(page, name)).items():
                text = "\n".join(f"    {l}" for l in text.split("\n"))
                await on_result("other_info", f"[https://{url}]\n{text}")
        finally:
            if page is not None:
                await page.close()

    async def _probe(self, cat, dom, tmpl, payload, kind):
        url = tmpl.replace("{username}", self.username)

        status, final_url, text = await self._fetch(
            self._session, url, allow_redirect=(kind == "redirect")
        )
        if kind == "code":
            if isinstance(payload, int):
                payload = [payload]
            hit = status in payload
        elif kind == "html":
            marker = payload.type_url
            subs = marker if isinstance(marker, list) else [marker]
            hit = bool(text) and any(s in text for s in subs)
        else:  # redirect
            if status < 0:
                hit = False
            else:
                hit = UserName._hit_redirect(payload, url, status, final_url, text, self.username)
        if getattr(payload, "reverse_condition", False):
            hit = not hit
        return url if hit else None

    def check_username_sites(self, on_progress=None) -> dict[str, list[str]]:
        """Synchronous entry point for the app: run the async probe loop."""
        return asyncio.run(self._check_sites(on_progress))
