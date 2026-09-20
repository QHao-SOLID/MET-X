# Assumptions — `base_template.json`

The template is the **single source of truth for simulation assumptions**.
Scenarios are flat patches: keys present replace the base (nested dicts merge
key-by-key); anything absent is inherited. Unknown keys are rejected with a
pointer to `simulation/TEMPLATE.md`.

- Template: `simulation/base_template.json`
- Scenarios: `simulation/scenarios/*.json`
- Key reference (units + effect of raising each key): `simulation/TEMPLATE.md`
- Validation: `voltvision/assumptions.py` (`load_template`, `build_cfg`, `validate`)

## The sections

| Group | Keys |
|---|---|
| Run controls | `n`, `cohort_year`, `n_years`, `seed`, `regimes`, `vehicle_ramp`, `coverage_ramp`, `flood_event_prob`, `severity_inflation`, `entrant_growth`, `sa_depreciation`, `sa_min` |
| Book composition | `region_pct`, `generation_pct`, `age_bands`, `gender_pct`, `car_age_median`, `car_age_sigma`, `sa_stats`, `engine_bands`, `engine_weights`, `entrant_frac` |
| NCD | `ncd_table`, `ncd_entry` |
| Frequency | `claim_frequency_base`, `frequency`, `frequency_intensity`, `risk_flags` |
| Loadings / aging | `loading`, `aging` |
| Severity | `severity` (peril order + per-peril Gamma specs), `peril_dist`, `severity_multiplier` |
| Telematics | `telematics`, `behavior_risk` |
| Retention | `retention` |
| Pricing overrides | `pricing` (opaque to the system — merged into each method's card) |
| Reporting | `reporting` (LR target band, appetite, retained drop, quantiles) |

## Full key reference

The authoritative table with units and the effect of raising each value lives
in the project file — kept as a snippet so docs and code never drift:

--8<-- "simulation/TEMPLATE.md"
