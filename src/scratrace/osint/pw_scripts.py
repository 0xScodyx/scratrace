"""Playwright-скрипты детекта OSINT-профилей и доркинг.

Профильные скрипты (browser.username):
  — привязаны к сайту из БД с PLAYWRIGHT маркером
  — получают (page, username) и возвращают bool (True = профиль найден)

Доркинг-скрипты (browser.dork):
  — не привязаны к БД, запускаются всегда
  — получают (page, username) и возвращают dict[str, str] (url -> сниппет)
  — результаты идут в категорию "other_info" с дедупликацией против
    обычных категорий

Регистрация:
    @browser.username("tiktok.com")
    async def tiktok(page, username: str) -> bool: ...

    @browser.dork("duckduckgo")
    async def duckduckgo(page, username: str) -> dict[str, str]: ...

Вызов:
  get_checker(cls, name)       — профильные (cls = "UserName"/"Mail"/...)
  get_dork_checker(name)       — доркинг
"""

from __future__ import annotations

from typing import Awaitable, Callable
from urllib.parse import urlparse

from scratrace.osint.log import scratrace_log, WARNING

class _PwError(Exception): ...
class _PwTimeoutError(Exception): ...
PwError: type[Exception] = _PwError
PwTimeoutError: type[Exception] = _PwTimeoutError
_PW_AVAILABLE = False
try:
    from playwright.async_api import Error as _PwRealError, TimeoutError as _PwRealTimeout  # type: ignore[assignment]
    PwError = _PwRealError  # type: ignore[assignment]
    PwTimeoutError = _PwRealTimeout  # type: ignore[assignment]
    _PW_AVAILABLE = True
except (ImportError, AttributeError):
    scratrace_log("playwright not available — browser checks and dorking disabled", type=WARNING)

# реестр: { "UserName": {name: fn}, "Mail": {...}, ... }
_REGISTRY: dict[str, dict[str, Callable]] = {}
# реестр доркинг-скриптов: {name: fn} — не привязаны к БД, всегда запускаются
_DORK_REGISTRY: dict[str, Callable] = {}


def get_checker(cls: str, name: str) -> Callable | None:
    """Достать зарегистрированную функцию по (класс OSINT, имя)."""
    return _REGISTRY.get(cls, {}).get(name)


def get_dork_checker(name: str) -> Callable | None:
    """Достать доркинг-функцию по имени."""
    return _DORK_REGISTRY.get(name)


def _register(cls: str, name: str):
    """Зарегистрировать fn под (класс OSINT, имя)."""
    def deco(fn: Callable):
        _REGISTRY.setdefault(cls, {})[name] = fn
        return fn
    return deco


def _register_dork(name: str):
    """Зарегистрировать доркинг-функцию (не в БД, всегда запускается)."""
    def deco(fn: Callable):
        _DORK_REGISTRY[name] = fn
        return fn
    return deco


class _Browser:
    """Именованные декораторы по классам OSINT (все через _register)."""

    username = staticmethod(lambda name: _register("UserName", name))
    mail = staticmethod(lambda name: _register("Mail", name))
    fullname = staticmethod(lambda name: _register("FullName", name))
    numberphone = staticmethod(lambda name: _register("NumberPhone", name))
    dork = staticmethod(lambda name: _register_dork(name))


browser = _Browser()


# ====================================================================== #
# UserName — playwright-пул
# ====================================================================== #
@browser.username("tiktok.com")
async def tiktok(page, username: str) -> bool:
    # page уже открыт на https://www.tiktok.com/@{username} (launch/goto/close
    # делает обёртка, headless=True). Тикток по HTTP неотличим (antibot), поэтому
    # смотрим в отрендеренный DOM: у реального профиля есть uniqueId/userInfo в
    # __UNIVERSAL_DATA__, у «аккаунт не найден» — нет.
    #
    # TIKTOK_TIMEOUT — потолок ожидания рендера (мс). Меняй здесь, если тикток
    # не успевает отрисоваться или, наоборот, надо жёстче обрубать вис.
    TIKTOK_TIMEOUT = 8000
    try:
        # ждём именно маркер, а не слепую паузу: появился <script id=... с
        # __UNIVERSAL_DATA__ → профиль отрисовался; таймаут → антибот-оболочка.
        await page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").wait_for(
            state="attached", timeout=TIKTOK_TIMEOUT
        )
    except PwTimeoutError:
        return False  # DOM так и не отдали (antibot) — считаем «не найдено»
    content = await page.content()
    return "uniqueId" in content and "userInfo" in content


@browser.username("hubski.com")
async def hubski(page, username: str) -> bool:
    # page уже открыт на https://hubski.com/user/{username}
    # Hubski показывает recaptcha на HTTP-уровне всем. В браузере после JS
    # у реального профиля появляется блок с постами/очками пользователя.
    # У несуществующего — только recaptcha/логин.
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PwTimeoutError:
        pass
    content = await page.content()
    # Реальный профиль содержит теги/посты пользователя
    # Страница без профиля показывает только recaptcha и логин
    if "recaptcha" in content and "login" not in content.lower():
        return False
    # Если есть упоминание username в контексте профиля — найден
    return f"/user/{username}" in content or "points" in content.lower()


@browser.username("replit.com")
async def replit(page, username: str) -> bool:
    # page уже открыт на https://replit.com/@{username}
    # Без авторизации Replit редиректит всех на /login?source=root-profile
    # Реальный профиль: title с ником, секция с REPL
    # Несуществующий на login, либо 404 страница
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PwTimeoutError:
        pass
    final_url = page.url
    if "/login" in final_url:
        return False
    # Если не редиректнуло на логин — скорее всего профиль
    title = await page.title()
    if "not found" in title.lower() or "404" in title:
        return False
    return True


@browser.username("news.ycombinator.com")
async def news_ycombinator(page, username: str) -> bool:
    # page уже открыт на https://news.ycombinator.com/user?id={username}
    # Hacker News — простая серверная страница, но рейт-лимит на HTTP.
    # В браузере работает обычно.
    try:
        await page.wait_for_selector("body", timeout=10000)
    except PwTimeoutError:
        return False
    content = await page.content()
    if "No such user" in content:
        return False
    # Реальный профиль содержит "karma" или "created"
    return "karma" in content.lower()


@browser.username("steamcommunity.com")
async def steamcommunity(page, username: str) -> bool:
    # page уже открыт на https://steamcommunity.com/id/{username}
    # Настоящий профиль: title "Steam Community :: {name}"
    # Несуществующий: title "Steam Community :: Error" + содержит "The specified profile could not be found"
    try:
        await page.wait_for_selector("title", timeout=5000)
    except PwTimeoutError:
        return False
    title = await page.title()
    if "Error" in title:
        return False
    content = await page.content()
    return "The specified profile could not be found" not in content


@browser.username("500px.com")
async def five00px(page, username: str) -> bool:
    # page уже открыт на https://500px.com/p/{username}
    # 500px — SPA на React. HTTP возвращает одинаковый HTML для всех.
    # В браузере реальный профиль показывает фотографии пользователя,
    # несуществующий — страницу с "Page not found" или "doesn't exist".
    try:
        await page.wait_for_load_state("networkidle", timeout=12000)
    except PwTimeoutError:
        pass
    content = await page.content()
    title = await page.title()
    if "Page not found" in title or "not found" in content.lower()[:1000]:
        return False
    # Реальный профиль содержит ссылки на фото или user data
    if "photo" in content.lower()[:3000] and "avatar" in content.lower()[:3000]:
        return True
    # fallback: title не "500px" (дефолтный для пустой SPA)
    return title != "500px"


@browser.username("unsplash.com")
async def unsplash(page, username: str) -> bool:
    # page уже открыт на https://unsplash.com/@{username}
    # Настоящий профиль: title "Unsplash (@{name}) | ...", есть заголовок профиля
    # Несуществующий: title "Page not found | Unsplash", текст "Page not found" / "404"
    try:
        await page.wait_for_selector("title", timeout=5000)
    except PwTimeoutError:
        return False
    title = await page.title()
    if "Page not found" in title or "404" in title:
        return False
    content = await page.content()
    return "Page not found" not in content and "404" not in content.lower()[:500]


@browser.username("livejournal.com")
async def livejournal(page, username: str) -> bool:
    # page уже открыт на https://{username}.livejournal.com
    # (с SSL=False из-за cert mismatch на поддоменах)
    # Реальный журнал: title с ником, контент постов
    # Несуществующий: title "lj.USER" или редирект на главную
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PwTimeoutError:
        pass
    title = await page.title()
    if not title or "LiveJournal" not in title and "lj." not in title:
        return False
    # Если title содержит только "LiveJournal.com" без ника → нет профиля
    if title.strip().lower() in ("livejournal.com", "livejournal"):
        return False
    content = await page.content()
    return username.lower() in content.lower()[:5000]


@browser.username("weebly.com")
async def weebly(page, username: str) -> bool:
    # page уже открыт на https://{username}.weebly.com
    # Weebly под Cloudflare. После прохода CF реальный сайт показывает
    # контент владельца. Несуществующий — 403 или "site not found".
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PwTimeoutError:
        pass
    # Проверяем, не застряли ли на Cloudflare
    content = await page.content()
    if "Just a moment" in content or "Attention Required" in content:
        return False
    title = await page.title()
    # Заглушка Weebly для несуществующих сайтов
    if not title or title in ("Weebly", "weebly.com", "Attention Required! | Cloudflare"):
        return False
    if "page not found" in content.lower()[:2000] or "404" in content[:2000]:
        return False
    return True


@browser.username("wix.com")
async def wix(page, username: str) -> bool:
    # page уже открыт на https://{username}.wixsite.com/{username}
    # Wix — SPA-конструктор. Реальный сайт показывает контент.
    # Несуществующий — страницу 404 Wix.
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PwTimeoutError:
        pass
    title = await page.title()
    content = await page.content()
    # Wix 404 страница
    if "404 Error" in title or "Page Not Found" in title:
        return False
    if "Page not found" in content[:2000] and "Wix" in content[:2000]:
        return False
    # Если сайт существует, в title будет имя сайта, не дефолтный Wix
    return bool(title) and "Wix" not in title


@browser.username("xanga.com")
async def xanga(page, username: str) -> bool:
    # page уже открыт на https://{username}.xanga.com
    # Настоящий профиль: title "{name}'s Xanga Site | ..."
    # Несуществующий: title "Xanga 2.0 is Here!" (главная с логин-формой)
    try:
        await page.wait_for_selector("title", timeout=5000)
    except PwTimeoutError:
        return False
    title = await page.title()
    if "Xanga 2.0 is Here" in title or "Login" in title:
        return False
    return True


@browser.username("fiverr.com")
async def fiverr(page, username: str) -> bool:
    # page уже открыт на https://www.fiverr.com/{username}
    # Fiverr под Cloudflare. HTTP 403 для всех неавторизованных.
    # В браузере реальный продавец показывает страницу с гигами,
    # несуществующий — "Page not found" или редирект.
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PwTimeoutError:
        pass
    content = await page.content()
    if "It needs a human touch" in content:
        return False
    title = await page.title()
    if "Page not found" in title or "not found" in content.lower()[:2000]:
        return False
    if "Just a moment" in content or "Attention Required" in content:
        return False
    # Реальный профиль Fiverr содержит "Fiverr" в title и username
    if "Fiverr" in title and username.lower() in content.lower()[:5000]:
        return True
    return False


# ====================================================================== #
# Доркинг — поисковые запросы, возвращают dict[url -> сниппет]
# ====================================================================== #
@browser.dork("duckduckgo")
async def duckduckgo(page, username: str) -> dict[str, str]:
    """Поиск username в DuckDuckGo через Playwright.
    Жмёт «More Results» пока кнопка есть, парсит все страницы.
    Склеивает сниппеты по домену — {domain: весь_текст_про_домен}."""
    domain_raw: dict[str, list[str]] = {}
    seen_keys: dict[str, set[str]] = {}
    seen_urls: set[str] = set()
    if page is None:
        return {}
    query = f'"{username}"'
    try:
        await page.goto("https://duckduckgo.com/", wait_until="domcontentloaded", timeout=10_000)
        await page.wait_for_selector("input[name='q']", timeout=5_000)
        await page.fill("input[name='q']", query)
        await page.keyboard.press("Enter")
        await page.wait_for_selector("li[data-layout='organic']", timeout=10_000)
    except PwTimeoutError:
        return {}

    for _ in range(10):
        items = await page.query_selector_all("li[data-layout='organic']")
        for item in items:
            links = await item.query_selector_all("a[href^='http']")
            if not links:
                continue
            href = await links[0].get_attribute("href")
            if not href or "duckduckgo.com" in href or href in seen_urls:
                continue
            seen_urls.add(href)
            domain = (urlparse(href).hostname or href).removeprefix("www.")
            raw = (await item.inner_text()).strip()
            parts = raw.split("\n\n")
            if len(parts) >= 3:
                raw = "\n\n".join(parts[2:])
            else:
                raw = parts[-1] if len(parts) >= 2 else parts[0]
            key = raw.strip()[:100]
            if key not in seen_keys.setdefault(domain, set()):
                seen_keys[domain].add(key)
                domain_raw.setdefault(domain, []).append(raw)
        more_btn = await page.query_selector("#more-results")
        if not more_btn:
            break
        try:
            await more_btn.click()
        except PwError:
            break
        await page.wait_for_timeout(1_200)
    return {d: "\n".join(v[:3]) for d, v in domain_raw.items()}


# ====================================================================== #
# Mail — примеры
# ====================================================================== #
@browser.mail("protonmail.com")
async def protonmail(page, email: str) -> bool:
    raise NotImplementedError


@browser.mail("gmail.com")
async def gmail(page, email: str) -> bool:
    raise NotImplementedError


# ====================================================================== #
# FullName — примеры
# ====================================================================== #
@browser.fullname("linkedin.com")
async def linkedin(page, name: str) -> bool:
    raise NotImplementedError


# ====================================================================== #
# NumberPhone — примеры
# ====================================================================== #
@browser.numberphone("whatsapp.com")
async def whatsapp(page, phone: str) -> bool:
    raise NotImplementedError


@browser.numberphone("telegram.org")
async def telegram(page, phone: str) -> bool:
    raise NotImplementedError


@browser.username("leetcode.cn")
async def leetcode_cn(page, username: str) -> bool:
    try:
        await page.wait_for_timeout(8000)
    except PwTimeoutError:
        pass
    return "/404/" not in page.url
