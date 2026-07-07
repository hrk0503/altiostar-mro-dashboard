"""Blaretech RF provider -- NOT YET WIRED.

File-handoff contract (per docs/COUNTERFACTUAL.md and
src/integration/blaretech_export.py):

  1. WINNIIO calls src.integration.blaretech_export.build_export(data_dir,
     out_dir) to produce:
       01_counterfactual_request.csv  -- (relation x candidate CIO) to simulate
       02_sites.geojson               -- georeferenced sites for RF ingestion
       03_relations.geojson           -- georeferenced relation lines
       RETURN_SCHEMA.csv              -- empty template of columns to fill
  2. The package is handed off to Blaretech (today: manual/NDA file exchange;
     future: an API or shared bucket -- undecided).
  3. Blaretech runs their RF/propagation/mobility sim per candidate CIO and
     returns a filled CSV matching RETURN_SCHEMA.csv's columns.
  4. WINNIIO re-ingests via src.integration.counterfactual_loop.
     ingest_counterfactuals and resumes the optimize() search.

No transport, polling, or async job mechanism exists yet. This class exists
so the /simulate endpoint has a real seam to wire once that handoff is agreed.
"""
from __future__ import annotations

from pathlib import Path

from backend.app.rf.provider import RFProvider


class BlaretechRFProvider(RFProvider):
    name = "blaretech"

    def simulate(self, request_dir: Path) -> Path:
        raise NotImplementedError(
            "blaretech RF provider not wired: no transport for the "
            "request/return file handoff exists yet (see module docstring "
            "for the documented contract)",
        )
