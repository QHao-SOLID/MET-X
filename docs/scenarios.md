# Scenarios

A scenario is a **flat patch** on `base_template.json`, stored as a JSON list in
`simulation/scenarios/*.json` (one file = one group). Anything absent is
inherited from the base.

## Anatomy

```json
{
  "name": "demo_scenario",
  "vehicle": {"ICE": 0.6, "EV": 0.4},
  "coverage_ramp": {"from": {"Comprehensive": 0.45, "TPFT": 0.20, "TPO": 0.35}},
  "pricing": {"glm": {"target_lr": 0.60}},
  "seed": 7
}
```

| Key | Meaning |
|---|---|
| `name` | scenario name — used in file names and the manifest |
| `enabled` | `false` skips the scenario (default true) — toggle to run a subset without deleting or passing `--scenarios` |
| `vehicle` | allocation dict only: `{"ICE": 0.0, "EV": 1.0}` (EV-only) or `{"ICE": 0.6, "EV": 0.4}` (mixed). Absent → template `vehicle_ramp.from`. Zero weights are dropped |
| `seed` | run this scenario once with this seed (overrides `seeds.json`) |
| `pricing` | `{regime: {param: value}}` rate-card overrides; unknown params are rejected by the method's declared card |
| everything else | patches `base_template.json` (nested dicts merge) |

## Seeds

`simulation/seeds.json` holds the default list:

```json
{"seeds": [42, 67, 69, 7, 13, 21, 58, 91, 103, 157, 203, 299]}
```

Every scenario runs once per seed unless it patches `seed`. Result files are
always seed-suffixed: `shared/results/<scenario>_s<seed>.pkl`.

## Mix over time

The base fleet mix is `vehicle_ramp.from` (whole book). Entrants can drift
linearly across the simulation window with `to`; existing policies never change
fuel type:

```json
{"name": "ev_ramp",
 "vehicle_ramp": {"from": {"ICE": 0.96, "EV": 0.04},
                  "to":   {"ICE": 0.80, "EV": 0.20}}}
```

`n_years == 1` uses `from`; `to` absent = static book.

`coverage_ramp` is the same ramp for the product mix:

```json
{"name": "coverage_shift",
 "coverage_ramp": {"to": {"Comprehensive": 0.45, "TPFT": 0.20, "TPO": 0.35}}}
```

`from` is inherited from the template, so a scenario only needs to patch `to`.
Both ramps share one interpolation function (`ramp_progress` + `blend_mix` in
`simulate.py`), so they behave identically. TPO-ward drift pressures the tariff
loss ratio upward (TPO is underpriced — see [Analysis](analysis.md)), though the
TPO book is noisy, so the effect varies by seed. `from`/`to` keys must match the
base mix keys exactly.

## Groups in this repo (examples — your folder may differ)

| File | Scenarios |
|---|---|
| `matrix.json` | `ICE`, `EV`, `MIX` — the three standard books; keep the names: they feed the §5b matrix table in `analysis.ipynb` |
| `base.json` | `base` — pure template book (same as MIX) |
| `hard_combo.json` | `combo_hard` — frequency + severity shock with repricing |
| `frequency.json` | `freq_p10`, `freq_p20`, `freq_p25` — `frequency_intensity` 1.10 / 1.20 / 1.25 (`λ = λ_base × intensity`) |
| `long_run.json` | `long_run_30y` (zero inflation/growth), `long_run_30y_inflated` (6% inflation) — `n_years: 30`, `n: 4000` |
| `niche.json` | `ev_ramp_heavy`, `tpo_tsunami`, `senior_skew`, `young_male_skew`, `flood_heavy`, `theft_heavy`, `severity_shock`, `high_inflation`, `clean_book` |

The runner reads **every** `*.json` in `scenarios/`; add or remove files freely.
Other group sets used earlier in this project (`mix_coverage`) live in git
history if you want them back.

> **Matrix table requirement:** `analysis.ipynb` §5b reads `ICE`/`MIX`/`EV`
> results at the analysis seed (default 42), so those scenarios must be run at
> that seed. Details: [Analysis](analysis.md#5b-matrix-table-what-your-scenarios-need).

## Adding a scenario

1. Append an entry to any `scenarios/*.json` (or add a new file — the stem
   becomes the group name).
2. Run it: `python run_scenarios.py --scenarios my_scenario` (`--quick` first).
3. Inspect the patch diff printed by the runner and the metrics table.
