"""Phase 2 backend API tests: /czml, /datasets, /simulate, /jobs, auth, WS."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

TOKEN = "test-secret-token"


@pytest.fixture(autouse=True)
def _set_token(monkeypatch):
    monkeypatch.setenv("WINNIIO_API_TOKEN", TOKEN)


@pytest.fixture(autouse=True)
def _clean_czml_cache():
    """The CZML cache is disk-persisted across test runs by design (that's the
    feature under test) -- clear it so cache-hit/miss assertions are not
    polluted by a previous run's artifacts."""
    from backend.app.paths import CACHE_DIR
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
    yield


@pytest.fixture
def client():
    from backend.app.main import app
    return TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {TOKEN}"}


# ── auth ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("method,url,kwargs", [
    ("get", "/api/v1/czml", {}),
    ("post", "/api/v1/datasets", {"files": {"file": ("x.csv", b"a,b\n1,2\n", "text/csv")}}),
    ("post", "/api/v1/simulate", {"json": {"rf_provider": "synthetic"}}),
    ("get", "/api/v1/jobs/does-not-exist", {}),
])
def test_401_without_token(client, method, url, kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == 401


# ── /czml ─────────────────────────────────────────────────────────────────

def test_czml_returns_document_and_expected_ue_count(client):
    resp = client.get("/api/v1/czml?n_ues=5&seed=1&duration_s=10", headers=_auth())
    assert resp.status_code == 200
    doc = resp.json()
    assert doc[0]["id"] == "document"
    ue_ids = [p["id"] for p in doc if p["id"].startswith("UE-")]
    assert len(ue_ids) == 5
    assert resp.headers.get("x-cache") == "MISS"


def test_czml_second_call_is_cache_hit(client):
    params = "n_ues=4&seed=2&duration_s=10"
    r1 = client.get(f"/api/v1/czml?{params}", headers=_auth())
    r2 = client.get(f"/api/v1/czml?{params}", headers=_auth())
    assert r1.status_code == r2.status_code == 200
    assert r1.headers.get("x-cache") == "MISS"
    assert r2.headers.get("x-cache") == "HIT"
    assert r1.json() == r2.json()


def test_czml_n_ues_over_cap_is_422(client):
    resp = client.get("/api/v1/czml?n_ues=9999", headers=_auth())
    assert resp.status_code == 422


def test_czml_duration_over_cap_is_422(client):
    resp = client.get("/api/v1/czml?duration_s=99999", headers=_auth())
    assert resp.status_code == 422


# ── /datasets ─────────────────────────────────────────────────────────────

def test_upload_valid_relation_csv_matches_model(client):
    csv = (
        "source_cell_id,target_cell_id,timestamp_utc,ho_attempts,ho_successes,"
        "ho_failures,too_early_ho,too_late_ho,wrong_cell,correct_cell,ping_pong,cio_db\n"
        "A,B,2026-04-01 00:00:00,10,9,1,0,1,0,9,0,0\n"
    )
    resp = client.post(
        "/api/v1/datasets",
        headers=_auth(),
        files={"file": ("relation.csv", csv.encode(), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["matched_model"] == "RelationPMRecord"
    assert body["tenancy"] == "single (P3)"
    assert "dataset_id" in body


def test_upload_renamed_columns_map_to_canonical(client):
    csv = (
        "src_cell,tgt_cell,timestamp_utc,ho_attempts,ho_successes,ho_failures,"
        "too_early_ho,too_late_ho,wrong_cell,correct_cell,ping_pong,cio\n"
        "A,B,2026-04-01 00:00:00,10,9,1,0,1,0,9,0,0\n"
    )
    resp = client.post(
        "/api/v1/datasets",
        headers=_auth(),
        files={"file": ("relation_renamed.csv", csv.encode(), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["matched_model"] == "RelationPMRecord"
    assert body["rename_map"]["src_cell"] == "source_cell_id"
    assert body["rename_map"]["tgt_cell"] == "target_cell_id"


def test_upload_junk_csv_is_422_with_hints(client):
    csv = "foo,bar\n1,2\n"
    resp = client.post(
        "/api/v1/datasets",
        headers=_auth(),
        files={"file": ("junk.csv", csv.encode(), "text/csv")},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "hint" in detail
    assert "foo" in detail["unmapped"] or "bar" in detail["unmapped"]


def test_upload_wrong_extension_is_422(client):
    resp = client.post(
        "/api/v1/datasets",
        headers=_auth(),
        files={"file": ("data.txt", b"a,b\n1,2\n", "text/plain")},
    )
    assert resp.status_code == 422


def test_upload_over_size_cap_is_413(client, monkeypatch):
    import backend.app.routers.datasets as ds_mod
    monkeypatch.setattr(ds_mod, "MAX_UPLOAD_BYTES", 10)
    resp = client.post(
        "/api/v1/datasets",
        headers=_auth(),
        files={"file": ("big.csv", b"a,b\n1,2\n1,2\n1,2\n", "text/csv")},
    )
    assert resp.status_code == 413


# ── /simulate ─────────────────────────────────────────────────────────────

def test_simulate_synthetic_done_with_banner_and_results_file(client):
    resp = client.post("/api/v1/simulate", headers=_auth(), json={"rf_provider": "synthetic"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "done"
    assert "NOT_A_PERFORMANCE_CLAIM" in body["summary"]["banner"]
    assert body["summary"]["relations"] > 0

    from backend.app.paths import RESULTS_DIR
    assert (RESULTS_DIR / f"{body['job_id']}.csv").exists()

    job = client.get(f"/api/v1/jobs/{body['job_id']}", headers=_auth())
    assert job.status_code == 200
    assert job.json()["status"] == "done"


def test_simulate_blaretech_is_501(client):
    resp = client.post("/api/v1/simulate", headers=_auth(), json={"rf_provider": "blaretech"})
    assert resp.status_code == 501


def test_jobs_unknown_id_is_404(client):
    resp = client.get("/api/v1/jobs/nonexistent-job", headers=_auth())
    assert resp.status_code == 404


# ── websocket ─────────────────────────────────────────────────────────────

def test_websocket_query_string_token_is_rejected(client):
    with client.websocket_connect(f"/api/v1/ws/noc-copilot?token={TOKEN}") as ws:
        # first message must still be the auth frame; a stray text frame
        # sent as if pre-authed should be rejected, proving query token alone
        # grants nothing.
        ws.send_text("hello")
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_websocket_first_message_auth_succeeds(client):
    with client.websocket_connect("/api/v1/ws/noc-copilot") as ws:
        ws.send_text(json.dumps({"token": TOKEN}))
        ws.send_text("ping")
        msg = ws.receive_json()
        assert msg["status"] == "not_implemented"
        assert msg["echo"] == "ping"


def test_websocket_wrong_first_message_token_closes(client):
    with client.websocket_connect("/api/v1/ws/noc-copilot") as ws:
        ws.send_text(json.dumps({"token": "wrong"}))
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()
