"""Test that all Playwright scripts are properly registered."""

from scratrace.osint.pw_scripts import get_checker, get_dork_checker


def test_dork_duckduckgo_registered():
    fn = get_dork_checker("duckduckgo")
    assert fn is not None
    assert callable(fn)


def test_username_scripts_registered():
    expected = [
        "tiktok.com",
        "hubski.com",
        "replit.com",
        "news.ycombinator.com",
        "steamcommunity.com",
        "500px.com",
        "unsplash.com",
        "livejournal.com",
        "weebly.com",
        "wix.com",
        "xanga.com",
        "fiverr.com",
    ]
    for name in expected:
        fn = get_checker("UserName", name)
        assert fn is not None, f"UserName.{name} not registered"
        assert callable(fn)


def test_mail_scripts_registered():
    for name in ("protonmail.com", "gmail.com"):
        fn = get_checker("Mail", name)
        assert fn is not None, f"Mail.{name} not registered"
        assert callable(fn)


def test_fullname_scripts_registered():
    fn = get_checker("FullName", "linkedin.com")
    assert fn is not None
    assert callable(fn)


def test_numberphone_scripts_registered():
    for name in ("whatsapp.com", "telegram.org"):
        fn = get_checker("NumberPhone", name)
        assert fn is not None, f"NumberPhone.{name} not registered"
        assert callable(fn)


def test_unknown_checker_returns_none():
    assert get_checker("UserName", "nonexistent.example") is None
    assert get_checker("UnknownClass", "tiktok.com") is None
    assert get_dork_checker("nonexistent") is None
