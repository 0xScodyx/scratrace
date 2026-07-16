import socket

import pytest

_TIMEOUT = 8


def _is_placeholder(site: str) -> bool:
    """True for template entries like ``{username}.x.com`` / ``{urlmain}/u/{username}``.

    These are not real hosts and never resolve on their own, so the reachability
    check must skip them.
    """
    return site.startswith("{")


def _host_alive(site: str) -> bool:
    """True если домен резолвится и на 443 реально слушает сервер (TCP handshake).

    ICMP ping для современного веба не показателен — Cloudflare/AWS/балансировщики
    массово дропают эхо-запросы, хотя сайты живые. TCP-connect на 443 принимают
    почти все хосты, поэтому это честная проверка «сервер существует и доступен».
    """
    try:
        ip = socket.gethostbyname(site)
    except OSError:
        return False
    try:
        with socket.create_connection((ip, 443), timeout=_TIMEOUT):
            return True
    except OSError:
        return False


def test_sites_parsed(sites: list[str]) -> None:
    assert sites, "registry must contain at least one site"
    assert "github.com" in sites


def test_site_reachable(site: str, request) -> None:
    if _is_placeholder(site):
        pytest.fail(f"{site} is a username template, not a real host")
    if not _host_alive(site):
        getattr(request.config, "_dead_sites").add(site)
        pytest.fail(f"{site} does not resolve or accept connections on port 443")
