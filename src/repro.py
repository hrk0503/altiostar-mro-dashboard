"""Reproducibility & honesty spine (Sprint 01).

Three primitives every synthetic surface in this repo must use:
- seed(): deterministic RNG so runs are byte-reproducible (Vitalik gate).
- result_hash(): content-address a result so a stranger can verify it.
- synthetic_badge(): the visible "this is synthetic" watermark (Claude-founder gate).
"""
from __future__ import annotations

import hashlib
import json

SEED = 42


def seed(value: int = SEED):
    """Return a NumPy default_rng seeded deterministically.

    Import numpy lazily so this module stays dependency-light for tests.
    """
    import numpy as np
    return np.random.default_rng(value)


def result_hash(obj) -> str:
    """Stable sha256 over a JSON-serialisable object (sorted keys)."""
    payload = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path) -> str:
    """sha256 of a file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


SYNTHETIC_TEXT = "SYNTHETIC DATA — no real operator data; results are illustrative"


def synthetic_badge(fmt: str = "text") -> str:
    """The watermark. `fmt` = 'text' | 'html' | 'comment'."""
    if fmt == "html":
        return (f'<span style="background:#ffb020;color:#0b1020;font-weight:700;'
                f'padding:2px 8px;border-radius:10px;font-size:.7rem;">{SYNTHETIC_TEXT}</span>')
    if fmt == "comment":
        return f"# {SYNTHETIC_TEXT}"
    return SYNTHETIC_TEXT
