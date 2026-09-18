# Analysis — `analysis.ipynb`

Reads a combined result from `simulation/shared/results/` and computes everything
from the `PREM_*` columns present — no hardcoded regime trio. Loader default:
`('base', 42)` if it exists, else the newest run in the manifest.

| Section | Content |
|---|---|
| §1 Executive summary | scorecard per regime (LR, retained LR, premium-risk alignment, avg premium) |
| §2 Portfolio & cohort | inception mix, age/SA distributions, cohort evolution, NCD/premium trends, sample policy trails, heatmaps, age-band risk |
| §3 Claims profile | frequency, severity, peril mix, LR by coverage |
| §4 Validation | model sanity checks (PASS/FAIL) + distribution tests (KS, gamma fits, Poisson dispersion) |
| §5 Pricing comparison | N-regime scorecard + effectiveness checks (risk signals, best regime, alignment) |
| §5b Cross-scenario table | tariff on ICE/MIX/EV, ML on EV — TPO LR, avg LR, premium bounds, avg premium |
| §6 Telematics tiers | premium and LR per score band, per regime |
| §7 EV vs ICE | share, frequency, severity, LR per year (plus any vehicle ramp visible in share) |
| §8 Seed spread | every seed of every scenario, read from `manifest.json` (no re-simulation) |
| §10 Realism vs benchmarks | scored table against `benchmarks.json` (PASS/FAIL) |

The desk notebook (`pricing_desk.ipynb`) covers live quoting and what-ifs; the
analysis notebook is the deep-dive. Both read the same result files the runner
produces, so numbers always reconcile with `manifest.json`.

## §5b matrix table — what your scenarios need

The cross-scenario review table is built from **other runs on disk**, not from
the current book. It expects scenarios named exactly `ICE`, `EV`, `MIX`,
produced at the **same seed** as the analysis loader (`SEED_RUN`, default `42`):

| Table column | Comes from scenario | Regime |
|---|---|---|
| Tariff ICE ONLY | `ICE` | `tariff` |
| Tariff EV and ICE combined | `MIX` | `tariff` |
| Tariff EV ONLY | `EV` | `tariff` |
| GLM EV ONLY | `EV` | `glm` |
| GLM + Telematics EV ONLY | `EV` | `telem` |

The repo ships `scenarios/matrix.json` with exactly these entries:

```json
[{"name": "ICE", "vehicle": {"ICE": 1.0}},
 {"name": "EV",  "vehicle": {"EV": 1.0}},
 {"name": "MIX"}]
```

Requirements checklist:

1. `simulation/scenarios/matrix.json` exists (or equivalent entries in any group file).
2. `seeds.json` (or the scenarios' `seed` patch) includes the analysis seed
   (`42` by default) — run: `python run_scenarios.py --scenarios ICE,EV,MIX`.
3. Don't rename them — or edit the `pairs` list in `analysis.ipynb` §5b to
   match your scenario names.

Missing columns are listed in the cell output ("not produced by the current
scenario set …") without failing the rest of the notebook.
