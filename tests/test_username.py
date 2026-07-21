"""Test UserName — construction, routing, and pure logic."""

from scratrace.osint.username import UserName, _extract_domain
from scratrace.osint.sites import Redirect, PLAYWRIGHT


def test_construction():
    u = UserName("testuser123")
    assert u.username == "testuser123"
    assert u.reg is not None


def test_targets_returns_list():
    u = UserName("randomperson")
    targets = u.targets()
    assert isinstance(targets, list)
    assert len(targets) > 0


def test_targets_each_entry():
    u = UserName("randomperson")
    for cat, tmpl, payload in u.targets():
        assert isinstance(cat, str)
        assert isinstance(tmpl, str)
        assert "{username}" in tmpl


def test_targets_code_routing():
    u = UserName("x")
    code = u._targets("code")
    assert isinstance(code, dict)
    for cat, entries in code.items():
        for dom, tmpl, payload in entries:
            assert isinstance(payload, (int, list))


def test_targets_html_routing():
    u = UserName("x")
    html = u._targets("html")
    assert isinstance(html, dict)
    for cat, entries in html.items():
        for dom, tmpl, payload in entries:
            assert hasattr(payload, "type_url")


def test_targets_browser_empty():
    u = UserName("x")
    browser = u._targets("browser")
    assert isinstance(browser, dict)


def test_targets_redirect_empty():
    u = UserName("x")
    redirect = u._targets("redirect")
    assert isinstance(redirect, dict)


def test_hit_redirect_no_redirect():
    """Если редиректа нет — профиль найден."""
    r = Redirect(final_url="")
    result = UserName._hit_redirect(
        r,
        entry_url="https://example.com/user/{username}",
        status=200,
        final_url="https://example.com/user/john",
        text="",
        username="john",
    )
    assert result is True


def test_hit_redirect_redirected_to_absent():
    """Если кинуло на absent-страницу — профиля нет."""
    r = Redirect(final_url="/user/notfound")
    result = UserName._hit_redirect(
        r,
        entry_url="https://example.com/u/{username}",
        status=404,
        final_url="https://example.com/user/notfound",
        text="",
        username="missing",
    )
    assert result is False


def test_hit_redirect_different_host():
    """Если сменился хост — не наш случай, возвращаем False."""
    r = Redirect(final_url="")
    result = UserName._hit_redirect(
        r,
        entry_url="https://site1.com/user/{username}",
        status=302,
        final_url="https://site2.com/login",
        text="",
        username="x",
    )
    assert result is False


def test_hit_redirect_with_status_marker():
    r = Redirect(final_url="/gone", marker=410)
    result = UserName._hit_redirect(
        r,
        entry_url="https://example.com/u/{username}",
        status=410,
        final_url="https://example.com/gone",
        text="",
        username="x",
    )
    assert result is False


def test_extract_domain_standard():
    assert _extract_domain("https://tiktok.com/@user") == "tiktok.com"


def test_extract_domain_www():
    assert _extract_domain("http://www.github.com") == "github.com"


def test_extract_domain_subdomain():
    assert _extract_domain("https://scodyx.itch.io") == "itch.io"



