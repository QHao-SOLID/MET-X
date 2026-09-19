# MET-X — simulator (project component)

Part of the MET-X monorepo. Full documentation: `../docs/` (MkDocs site at the
repo root). Agent/engineering rules: `../AGENT.md`.

Synthetic Malaysian motor book, built as two deliberately separated systems:

1. **Simulation** — `voltvision/simulate.py` generates policy books and evolves
   them over `n_years` (frequency → peril → severity → settlement → retention →
   NCD). Claims are shared by every pricing method; no premium is ever simulated.
   The claim model is industry-calibrated (total-loss settlement, excesses,
   flood event years, inflation, SA depreciation).
2. **Pricing** — black-box methods in `voltvision/methods/` (one module per
   regime) behind one standard interface: `(book, card, cfg, base_cfg) ->
   book + FINAL_PREMIUM_SST`. Each method declares its own rate card.

## Quickstart

```bash
python run_scenarios.py                 # full sweep -> shared/results/
python run_scenarios.py --quick         # smoke run
python run_scenarios.py --scenarios MIX
python run_scenarios.py --excel MIX_s42 # xlsx from an existing result
```

Then: `pricing_desk.ipynb` (live quoting) or `analysis.ipynb` (deep-dive +
§10 realism vs `benchmarks.json`, §12 premium evolution).

## Layout

| Path | What it is |
|---|---|
| `base_template.json` | simulation assumptions (see `TEMPLATE.md`) |
| `scenarios/*.json` | flat patches on the template (one file = one group) |
| `seeds.json` | seeds every scenario runs unless it patches its own |
| `run_scenarios.py` | the loop: simulate → price → combine → save |
| `pricing_desk.ipynb` | desk: resolve cards, quote, compare, what-if |
| `analysis.ipynb` | analysis, reads `shared/results/` only |
| `voltvision/` | engine (`simulate`), connector (`pricing`), methods, runner, io |
| `voltvision/methods/*.py` | pricing methods (tariff, glm, telem) — each owns its numbers |
| `shared/results/` | generated: `<scenario>_s<seed>.pkl` + `manifest.json` |
| `sources/` + `SOURCES.md` | citation ledger for the benchmark targets |

## Parity baseline (full size, seed 42)

| Book | Tariff | GLM | GLM+Telematics |
|---|---|---|---|
| ICE | 83.38% | 63.84% | 64.31% |
| EV | 59.72% | 58.39% | 58.84% |
| MIX / base | 80.08% | 69.57% | 69.76% |

NCD is applied after the model as a statutory discount (TPO exempt), so the
ML premiums are pure-premium / `target_lr` figures shaded by NCD — never a
learned rating factor. Engine hashes and the exact check procedure live in
`../docs/development.md` and `../AGENT.md`. The default book passes all 6/6
§10 industry realism checks.
