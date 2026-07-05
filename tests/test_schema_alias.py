"""Epic 2 tests — drop-in alias/fuzzy column mapping (test-first)."""
from __future__ import annotations

import pandas as pd

from src.pipeline.schema_mapper import infer_schema_flex, map_columns


def test_exact_aliases_map_to_canonical():
    m = map_columns(["src_cell", "tgt_cell", "cio", "attempts"])
    assert m.rename["src_cell"] == "source_cell_id"
    assert m.rename["tgt_cell"] == "target_cell_id"
    assert m.rename["cio"] == "cio_db"
    assert m.rename["attempts"] == "ho_attempts"
    assert m.unmapped == []


def test_unknown_column_is_reported_not_dropped():
    m = map_columns(["src_cell", "totally_unknown_thing"])
    assert "totally_unknown_thing" in m.unmapped
    assert "totally_unknown_thing" not in m.rename


def test_case_and_separator_insensitive():
    m = map_columns(["Source_Cell_ID", "TARGET-CELL", "CIO_dB"])
    assert m.rename.get("Source_Cell_ID") == "source_cell_id"
    assert m.rename.get("TARGET-CELL") == "target_cell_id"


def test_fuzzy_match_flagged():
    m = map_columns(["source_cel_id"])  # typo
    assert m.rename.get("source_cel_id") == "source_cell_id"
    assert "source_cel_id" in m.fuzzy  # low-confidence, surfaced


def test_flex_infer_maps_renamed_relation_csv(tmp_path):
    # A renamed relation-PM CSV should still resolve to RelationPMRecord.
    p = tmp_path / "renamed.csv"
    pd.DataFrame([{
        "src_cell": "A-1", "tgt_cell": "A-2", "tooearly": 0, "wrongcell": 0, "cio": 0.0,
    }]).to_csv(p, index=False)
    match, mapping = infer_schema_flex(p)
    assert match.matched_model == "RelationPMRecord"
    assert mapping.rename["src_cell"] == "source_cell_id"
