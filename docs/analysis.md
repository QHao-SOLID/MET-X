# Analysis — `analysis.ipynb`

Reads a combined result from `simulation/shared/results/` and computes everything
from the `PREM_*` columns present — no hardcoded regime trio. Loader default:
`('base', 67)` if it exists, else the newest run in the manifest.

| Section | Content |
|---|---|
| §1 Executive summary | scorecard per regime (LR, retained LR, premium-risk alignment, avg premium) |
| §2 Portfolio & cohort | inception mix, age/SA distributions, cohort evolution (incl. coverage mix by year — drifts only under `coverage_ramp`), NCD/premium trends, sample policy trails, heatmaps, age-band risk |
| §3 Claims profile | frequency, severity, peril mix, LR by coverage (one column + grouped bars per regime) |
| §4 Validation | model sanity checks (PASS/FAIL) + distribution tests (KS, gamma fits, Poisson dispersion) |
| §5 Pricing comparison | N-regime scorecard + effectiveness checks (risk signals, best regime, alignment) |
| §5b Cross-scenario table | tariff on ICE/MIX/EV, ML on EV — TPO LR, avg LR, premium bounds, avg premium |
| §6 Telematics tiers | premium and LR per score band, per regime |
| §7 EV vs ICE | share, frequency, severity, LR per year (plus any vehicle ramp visible in share) |
| §8 Seed spread | every seed of every scenario, read from `manifest.json` (no re-simulation) |
| §10 Realism vs benchmarks | scored table against `benchmarks.json` (PASS/FAIL) |
| §11 Explainability (SHAP) | exact linear SHAP on the refit GLM and GLM+Telematics frequency models (log-rate + ×multiplier), dependence plots, per-policy waterfalls, GLM-vs-telem attribution delta, and a log-premium anatomy (freq + severity ÷ target_lr + post-model NCD + flags). Requires `pip install shap` |
| §12 Premium evolution | portfolio mean premium by year, seed-averaged with min–max band, plus the cohort-matched smooth path (surviving cohort only) — all regimes |

The desk notebook (`pricing_desk.ipynb`) covers live quoting and what-ifs; the
analysis notebook is the deep-dive. Both read the same result files the runner
produces, so numbers always reconcile with `manifest.json`.

## §5b matrix table — what your scenarios need

The cross-scenario review table is built from **other runs on disk**, not from
the current book. It expects scenarios named exactly `ICE`, `EV`, `MIX`,
produced at the **same seed** as the analysis loader (`SEED_RUN`, default `67`):

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
   (`67` by default) — run: `python run_scenarios.py --scenarios ICE,EV,MIX`.
3. Don't rename them — or edit the `pairs` list in `analysis.ipynb` §5b to
   match your scenario names.

Missing columns are listed in the cell output ("not produced by the current
scenario set …") without failing the rest of the notebook.

## Reading the matrix — two recurring patterns

**1. EV-only tariff LR is lower than ICE (≈59% vs ≈77%, seed 67).**
Tariff `BASIC` is a graduated sum-assured rule — first RM1,000 flat + RM26 per
extra RM1,000 — so EV premium (mean SA ≈ RM67k vs RM29k) is ~1.9x ICE premium.
Claims scale far less: only own-damage perils are SA-linked (total-loss
payouts), while TPPD/TPBI/Windscreen are absolute-cost perils and there is no
explicit EV severity factor — higher EV sums assured carry the cost difference.
Net: EV is charged ~2x for ~1.5x expected cost → lower LR. Risk-based GLM
narrows the fuel gap. Note tariff LR (gross-of-expense) is not directly
comparable to GLM LR (pure premium ÷ `target_lr`, then NCD and flags) — compare
fuels *within* a regime.

**2. ICE TPO LR sits 127–150% while EV TPO LR is 90–120%.**
TPO premium = `(BASIC_TPO + 0.005 × SA) × 1.1 × 1.1^flags × 1.08` — the SA slice
dominates for high-SA cars (ICE ≈ RM145 vs EV ≈ RM340 of the premium), but TPO
claims are third-party only and ignore both own SA and any EV-specific loading
(there is none — SA carries EV cost differences through total-loss rules).
So EV pays ~1.7x the TPO premium for ~1.0–1.35x the claim cost → EV TPO LR
falls below the ICE level. The SA slice is effectively cross-subsidising EV
third-party cover from car value. Both books are noisy across seeds (TPO holds
~470 claims, ~100 TPBI with a heavy Gamma tail — one big award swings LR by
10–20pp), which is why the same scenario can print 90.5% one seed and 119.5%
another. Removing or shrinking the slice would push EV TPO LR above ICE's.
