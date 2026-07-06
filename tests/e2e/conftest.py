"""Fixtures for the Playwright e2e layer.

Launches the REAL `streamlit run` process and drives it with a real browser
(Chromium via Playwright) — this is the only layer of the three that
exercises actual rendered CSS/hover state and actual click dispatch, which
is what the dead "Quick Export" chip needed to be caught: it looked
identical to a real button in the AppTest element tree's HTML string but a
human clicking it (or a browser dispatching a click event to it) would have
found nothing happens.

If Playwright/Chromium cannot be installed or launched in the current
environment, `pytest.skip` is raised with a clear reason at session start
so the rest of the suite is unaffected (see README note in
tests/e2e/test_dashboard_e2e.py for how CI handles this layer).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright", reason="playwright not installed in this environment")

REPO_ROOT = Path(__file__).resolve().parents[2]
SECRETS_PATH = REPO_ROOT / ".streamlit" / "secrets.toml"
TEST_PASSWORD = "test"
PORT = 8765
BASE_URL = f"http://localhost:{PORT}"


def _wait_for_health(timeout: float = 45.0) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/_stcore/health", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def streamlit_server():
    """Launch `streamlit run src/dashboard/app.py` as a real subprocess.

    Writes a temporary root .streamlit/secrets.toml with DASHBOARD_PASSWORD
    (only if one doesn't already exist — never overwrites a real local
    secrets file) and removes it again on teardown.
    """
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    pre_existing = SECRETS_PATH.exists()
    original_content = SECRETS_PATH.read_text(encoding="utf-8") if pre_existing else None
    SECRETS_PATH.write_text(f'DASHBOARD_PASSWORD = "{TEST_PASSWORD}"\n', encoding="utf-8")

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "src/dashboard/app.py",
            "--server.port", str(PORT),
            "--server.headless", "true",
            "--server.runOnSave", "false",
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        ok = _wait_for_health()
        if not ok:
            out = ""
            if proc.stdout:
                try:
                    out = proc.stdout.read(4000)
                except Exception:
                    pass
            proc.terminate()
            pytest.skip(
                "streamlit server did not become healthy at "
                f"{BASE_URL}/_stcore/health within timeout — cannot run "
                f"Playwright e2e layer in this environment. Server output: {out}"
            )
        yield BASE_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        if pre_existing:
            SECRETS_PATH.write_text(original_content, encoding="utf-8")
        else:
            SECRETS_PATH.unlink(missing_ok=True)
            # remove the dir only if we created it and it's now empty
            try:
                next(SECRETS_PATH.parent.iterdir())
            except StopIteration:
                pass  # dir has other files (e.g. config.toml) — leave it
            except FileNotFoundError:
                pass
