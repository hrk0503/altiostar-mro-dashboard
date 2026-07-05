# VERIFY — reproduce the demo yourself (the Vitalik gate)

Everything below is **synthetic** and watermarked. The point is not the numbers;
it's that *you* can reproduce them from a clean clone in one command, and that
every claim traces to data — no trust required.

## Run the full loop
```bash
pip install -r requirements.txt
python run_loop.py --out-dir results/loop
```

You will see a summary like:
```
relations: 763
mean_before_%: 79.16
mean_after_%: 99.50
mean_improvement_pp: 20.34
run_hash: <sha256>
```

## Verify determinism
Run it twice into different folders and compare the `run_hash` — they must be
identical. Same inputs → same result, byte-for-byte:
```bash
python run_loop.py --out-dir results/a
python run_loop.py --out-dir results/b
# the printed run_hash values must match
```

## What the loop actually does (grounded, not magic)
1. `blaretech_export.build_export` — WINNIIO lists the failing relations and the
   candidate CIOs to test (real geometry from `data/synthetic`).
2. `synthetic_rf_return.generate` — a **deterministic, synthetic** stand-in for
   the Blaretech RF layer fills the counterfactual outcomes. (Real Blaretech
   replaces this file; nothing else changes.)
3. `counterfactual_loop.ingest_counterfactuals` + `optimize` — WINNIIO now has a
   real search space and picks the best CIO per relation.
4. `results/loop/loop_before_after.csv` — per relation: current vs optimized,
   each row carrying `source = counterfactual_sim` provenance.

## Run the tests
```bash
python -m pytest tests/test_repro.py tests/test_counterfactual_loop.py \
                 tests/test_loop_e2e.py tests/eval/ -q
```
- `tests/eval/` is the **golden harness**: 20+ known-answer cases the optimizer
  must always pass. Change the optimizer, these guard you.

## The honest boundary
This proves the **machine** works end-to-end and is reproducible. It does **not**
prove any real-world handover gain — that requires Rakuten's real cluster data
under NDA, at which point step 2 (synthetic return) is replaced by Blaretech's
real RF simulation and the same pipeline runs unchanged.
