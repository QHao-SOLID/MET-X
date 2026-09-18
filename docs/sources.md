# Benchmarks & sources

Realism checks (`04 §10`) compare a run against industry targets in
`simulation/benchmarks.json`. Every target carries `source_ids` that resolve to
the citation ledger at `simulation/sources/benchmarks_sources.json`.

**Retrieval**: 2026-09-18, Parallel Search (parallel-cli 0.7.1, basic mode) via
the `research-lookup` skill. Results are **search-derived** titles/snippets, not
full-text extractions — run an Extract pass on the primary sources before
quoting numbers externally.

The full ledger (URLs, publishers, key values, exact queries) lives in the
project — embedded here so the docs and repo never drift:

--8<-- "simulation/SOURCES.md:content"

## Maintenance

1. Add the source to `simulation/sources/benchmarks_sources.json`
   (id, url, `used_for`, key values).
2. Reference its id from `simulation/benchmarks.json` → target `source_ids`.
3. Re-run `python run_scenarios.py --scenarios base` and check `§10` of `analysis.ipynb` still reflects intent.
