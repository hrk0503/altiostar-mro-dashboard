"""Spine tests — determinism, hashing, watermark (written test-first)."""
from __future__ import annotations

from src.repro import file_hash, result_hash, seed, synthetic_badge


def test_seed_is_deterministic():
    a = seed().integers(0, 1_000_000, size=5).tolist()
    b = seed().integers(0, 1_000_000, size=5).tolist()
    assert a == b  # same seed -> identical draws


def test_result_hash_stable_and_order_independent():
    h1 = result_hash({"a": 1, "b": [1, 2, 3]})
    h2 = result_hash({"b": [1, 2, 3], "a": 1})
    assert h1 == h2 and len(h1) == 64


def test_result_hash_changes_on_change():
    assert result_hash({"x": 1}) != result_hash({"x": 2})


def test_file_hash(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"hello")
    assert file_hash(p) == file_hash(p)
    assert len(file_hash(p)) == 64


def test_watermark_formats():
    assert "SYNTHETIC" in synthetic_badge("text")
    assert "span" in synthetic_badge("html")
    assert synthetic_badge("comment").startswith("#")
