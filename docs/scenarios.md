# Scenarios

A scenario is a **flat patch** on `base_template.json`, stored as a JSON list in
`simulation/scenarios/*.json` (one file = one group). Anything absent is
inherited from the base.

## Anatomy

```json
{
  "name": "demo_scenario",
  "vehicle": {"ICE": 0.6, "EV": 0.4},
  "coverage_pct": {"Comprehensive": 0.45, "TPFT": 0.20, "TPO": 0.35},
  "pricing": {"glm": {"target_lr": 0.60}},
  "seed": 7
}
```

| Key | Meaning |
|---|---|
| `name` | scenario name — used in file names and the manifest |
| `vehicle` | allocation dict only: `{"ICE": 0.0, "EV": 1.0}` (EV-only) or `{"ICE": 0.6, "EV": 0.4}` (mixed). Absent → template `vehicle_mix`. Zero weights are dropped |
| `seed` | run this scenario once with this seed (overrides `seeds.json`) |
| `pricing` | `{regime: {param: value}}` rate-card overrides; unknown params are rejected by the method's declared card |
| everything else | patches `base_template.json` (nested dicts merge) |

## Seeds

`simulation/seeds.json` holds the default list:

```json
{"seeds": [42, 67, 69]}
```

Every scenario runs once per seed unless it patches `seed`. Result files are
always seed-suffixed: `shared/results/<scenario>_s<seed>.pkl`.

## Vehicle mix over time

`vehicle_ramp` models a foreseeable mix shift. Entrants (new business) move
linearly across the simulation window; existing policies never change fuel type:

```json
{"name": "ev_ramp", "vehicle_ramp": {"EV": {"from": 0.10, "to": 0.40}}}
```

`n_years == 1` uses `from`. `{}` = off.

`coverage_ramp` is the same linear ramp for the product mix — new business
drifts from the template `coverage_pct` (or an explicit `from`) to `to` across
the window, while existing policies keep their coverage:

```json
{"name": "coverage_shift",
 "coverage_ramp": {"to": {"Comprehensive": 0.45, "TPFT": 0.20, "TPO": 0.35}}}
```

Both ramps share one interpolation function (`ramp_progress` + `blend_mix` in
`simulate.py`), so they behave identically. TPO-ward drift pressures the tariff
loss ratio upward (TPO is underpriced — see [Analysis](analysis.md)), though the
TPO book is noisy, so the effect varies by seed; `from` must use exactly the
`coverage_pct` keys.

## Groups in this repo (examples — your folder may differ)

| File | Scenarios |
|---|---|
| `matrix.json` | `ICE`, `EV`, `MIX` — the three standard books; keep the names: they feed the §5b matrix table in `analysis.ipynb` |
| `base.json` | `base` — pure template book (same as MIX) |
| `hard_combo.json` | `combo_hard` — frequency + severity shock with repricing |

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
