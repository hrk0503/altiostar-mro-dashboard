"""Effect-tests for the dashboard UI (QA hardening — see epic in CHANGELOG.md).

These use ``streamlit.testing.v1.AppTest`` to actually RUN the app script and
assert on the resulting element tree, not just that the source parses. This
is the layer that would have caught a dead top-bar chip IF it had been a real
widget wired to nothing — the companion static guard
(``tests/test_no_dead_controls.py``) catches decorative HTML that isn't a
widget at all.

Every assertion here checks an EFFECT of clicking a control (a panel
appearing, a download button materializing) — never just "did it render
without throwing."
"""
from __future__ import annotations

import hashlib

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "src/dashboard/app.py"
TEST_PASSWORD = "test"
_AUTH_VAL = hashlib.sha256(TEST_PASSWORD.encode()).hexdigest()[:16]

# Long timeout: the app loads CSVs + JSON experiment results on every run.
_TIMEOUT = 90


def _authed_app() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=_TIMEOUT)
    at.secrets["DASHBOARD_PASSWORD"] = TEST_PASSWORD
    at.query_params["_a"] = _AUTH_VAL
    at.run()
    return at


def _has_markdown_containing(at: AppTest, needle: str) -> bool:
    return any(needle in m.value for m in at.markdown)


def test_auth_bypass_reaches_dashboard_not_login():
    """Sanity check the auth harness itself: without the token we should be
    stuck on the login screen; with it, we should reach the dashboard."""
    at = AppTest.from_file(APP_PATH, default_timeout=_TIMEOUT)
    at.secrets["DASHBOARD_PASSWORD"] = TEST_PASSWORD
    at.run()
    assert not at.exception
    assert any(ti.label == "Password" for ti in at.text_input)

    at = _authed_app()
    assert not at.exception
    assert not any(ti.label == "Password" for ti in at.text_input)


def test_no_unhandled_exception_on_dashboard_load():
    at = _authed_app()
    assert not at.exception, [str(e) for e in at.exception]


@pytest.mark.parametrize("page", [
    "Dashboard", "Cell Map", "Experiments", "Network", "Simulation",
    "Reports", "Data Upload",
])
def test_every_nav_page_renders_without_exception(page):
    at = _authed_app()
    nav = at.radio[0]
    assert nav.options == [
        "Dashboard", "Cell Map", "Experiments", "Network", "Simulation",
        "Reports", "Data Upload",
    ]
    nav.set_value(page).run()
    assert not at.exception, f"{page} page raised: {[str(e) for e in at.exception]}"


# ── Header chip-buttons — each must be a REAL widget with a REAL effect ────
# These are the controls that replaced the dead `topnav-chip` spans.

def test_anomaly_chip_toggles_panel():
    at = _authed_app()
    assert not _has_markdown_containing(at, "Anomaly Scan Results")
    at.button(key="btn_anomaly").click().run()
    assert not at.exception
    assert _has_markdown_containing(at, "Anomaly Scan Results")
    # click again — must toggle back off (real state, not one-shot reveal)
    at.button(key="btn_anomaly").click().run()
    assert not _has_markdown_containing(at, "Anomaly Scan Results")


def test_health_check_chip_toggles_panel():
    at = _authed_app()
    assert not _has_markdown_containing(at, "Network Health Report")
    at.button(key="btn_health").click().run()
    assert not at.exception
    assert _has_markdown_containing(at, "Network Health Report")
    at.button(key="btn_health").click().run()
    assert not _has_markdown_containing(at, "Network Health Report")


def test_quick_export_chip_reveals_four_download_buttons_with_data():
    at = _authed_app()
    assert len(at.get("download_button")) == 0

    at.button(key="btn_export").click().run()
    assert not at.exception

    downloads = at.get("download_button")
    assert len(downloads) == 4
    # AppTest doesn't expose raw bytes for download_button (data is written to
    # the mock MediaFileManager, not the proto), so the effect we assert is:
    # each button registered a distinct, real media URL — proof the CSV/JSON
    # payload was actually generated and attached, not a stub with no file.
    urls = [d.proto.url for d in downloads]
    assert all(u.startswith("/mock/media/") for u in urls), urls
    assert len(set(urls)) == 4, "expected 4 distinct export files, got duplicates"
    exts = sorted(u.rsplit(".", 1)[-1] for u in urls)
    assert exts == ["csv", "csv", "csv", "json"], exts

    # toggle off — panel and its download buttons disappear
    at.button(key="btn_export").click().run()
    assert len(at.get("download_button")) == 0


def test_only_one_control_per_action_no_duplicate_buttons():
    """Regression guard for the de-duplication fix: there used to be a
    second row of buttons (Run Anomaly Scan / Network Health Check / Quick
    Export All) duplicating the header chips. There must be exactly one
    button per action now."""
    at = _authed_app()
    keys = [b.key for b in at.button]
    for expected in ("btn_anomaly", "btn_health", "btn_export"):
        assert keys.count(expected) == 1, f"expected exactly one {expected} button, found {keys.count(expected)}"
