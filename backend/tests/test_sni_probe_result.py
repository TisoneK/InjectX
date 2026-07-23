"""Verdict classification — the pure `classify_http` logic and the
captive-portal heuristic. No network."""

from snihunter.probe import classify_http, looks_like_captive_portal


def test_2xx_is_working():
    assert classify_http(200) == "working"
    assert classify_http(204) == "working"


def test_4xx_still_working():
    # 403/404 still prove we reached the real server behind the SNI.
    assert classify_http(403) == "working"
    assert classify_http(404) == "working"


def test_5xx_is_dead():
    assert classify_http(500) == "dead"
    assert classify_http(503) == "dead"


def test_none_status_is_dead():
    assert classify_http(None) == "dead"


def test_3xx_to_normal_host_is_redirect():
    assert classify_http(302, "https://other.example.com/") == "redirect"
    assert classify_http(301, "https://www.example.com/") == "redirect"


def test_3xx_to_captive_portal_is_blocked():
    assert classify_http(302, "http://captive.isp.com/topup") == "blocked"
    assert classify_http(302, "https://selfcare.safaricom.co.ke/no-balance") == "blocked"


def test_3xx_with_no_location_is_redirect():
    assert classify_http(302, None) == "redirect"


def test_captive_portal_heuristic():
    assert looks_like_captive_portal("http://portal.isp.net/recharge")
    assert looks_like_captive_portal("https://x/OutOfBundle")  # case-insensitive
    assert not looks_like_captive_portal("https://en.wikipedia.org/wiki/Main_Page")
    assert not looks_like_captive_portal(None)


def test_custom_indicator_list():
    # Explicit indicator list overrides the file-loaded default.
    assert classify_http(302, "https://x/mypattern", indicators=["mypattern"]) == "blocked"
    assert classify_http(302, "https://x/topup", indicators=["mypattern"]) == "redirect"
