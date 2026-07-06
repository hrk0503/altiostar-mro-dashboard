"""Playwright e2e — drives the REAL rendered dashboard in a real browser.

This is the highest-fidelity layer: it launches `streamlit run` as a
subprocess and clicks actual DOM elements the way a user (or the original
missed-bug scenario) would. It is the layer that most directly reproduces
"someone drove the running UI" — the thing every prior code roast skipped.

Environment note (zero-gaslight): this module requires `pytest-playwright`
+ an installed Chromium browser. If either is missing, the whole module is
skipped with an explicit reason — this test suite will NEVER report a false
pass. See the session report for whether this actually ran here or is
CI-only scaffold.
"""
from __future__ import annotations

import hashlib

import pytest

pytest.importorskip("playwright", reason="playwright not installed in this environment")

# Kept in sync with tests/e2e/conftest.py::TEST_PASSWORD — duplicated (not
# imported from conftest) to avoid pytest's special conftest-import handling.
TEST_PASSWORD = "test"
_AUTH_VAL = hashlib.sha256(TEST_PASSWORD.encode()).hexdigest()[:16]


@pytest.fixture
def dashboard_page(streamlit_server, page):
    """A page navigated past login via the ?_a= token bypass, with the
    header chip buttons confirmed rendered before handing off to the test
    (avoids flakiness from asserting on a page that's still hydrating)."""
    page.goto(f"{streamlit_server}/?_a={_AUTH_VAL}")
    page.get_by_role("button", name="Quick Export").wait_for(timeout=20000)
    return page


def test_login_gate_blocks_without_token(streamlit_server, page):
    page.goto(streamlit_server)
    page.get_by_placeholder("Enter dashboard password").wait_for(timeout=20000)


def test_anomaly_chip_fires_real_effect(dashboard_page):
    page = dashboard_page
    assert page.get_by_text("Anomaly Scan Results").count() == 0

    page.get_by_role("button", name="Anomaly Scan").click()
    page.get_by_text("Anomaly Scan Results").wait_for(timeout=15000)

    # toggle off
    page.get_by_role("button", name="Anomaly Scan").click()
    page.get_by_text("Anomaly Scan Results").wait_for(state="detached", timeout=15000)


def test_health_check_chip_fires_real_effect(dashboard_page):
    page = dashboard_page
    assert page.get_by_text("Network Health Report").count() == 0

    page.get_by_role("button", name="Health Check").click()
    page.get_by_text("Network Health Report").wait_for(timeout=15000)

    page.get_by_role("button", name="Health Check").click()
    page.get_by_text("Network Health Report").wait_for(state="detached", timeout=15000)


def test_quick_export_chip_triggers_real_download(dashboard_page):
    page = dashboard_page
    page.get_by_role("button", name="Quick Export").click()
    export_button = page.get_by_role("button", name="Cell Data (CSV)")
    export_button.wait_for(timeout=15000)

    with page.expect_download(timeout=15000) as download_info:
        export_button.click()
    download = download_info.value
    assert download.suggested_filename == "cell_data.csv"


def test_live_monitor_is_not_interactive(dashboard_page):
    """The one chip with no backend behind it must NOT read as clickable:
    no button role, and its CSS must not carry a pointer cursor."""
    page = dashboard_page
    assert page.get_by_role("button", name="Live Monitor").count() == 0

    label = page.locator(".status-label", has_text="Live Monitor")
    label.wait_for(timeout=15000)
    cursor = label.evaluate("el => getComputedStyle(el).cursor")
    assert cursor != "pointer", f"Live Monitor label has cursor:{cursor} — reads as clickable"


def test_no_duplicate_action_buttons(dashboard_page):
    """Regression guard for the de-duplication fix: the old bottom row
    ("Run Anomaly Scan" / "Network Health Check" / "Quick Export All") must
    be gone — exactly one control per action now."""
    page = dashboard_page
    assert page.get_by_role("button", name="Run Anomaly Scan").count() == 0
    assert page.get_by_role("button", name="Network Health Check").count() == 0
    assert page.get_by_role("button", name="Quick Export All").count() == 0
    assert page.get_by_role("button", name="Anomaly Scan").count() == 1
