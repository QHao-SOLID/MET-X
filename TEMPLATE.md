# base_template.json — key reference

Single source of truth for **simulation assumptions**. Scenarios in
`scenarios/*.json` are flat patches on this file: any key they contain replaces
the base value; everything else is inherited. Unknown keys are rejected by the
loader (this file is the list of what exists).

Tariff rates/knobs are **not** here — they live in `02a_tariff.ipynb` (the
tariff method owns its numbers). Pricing methods receive their numbers through
rate cards; `pricing` below is only an optional override layer.

## Run controls

| Key | Unit | Meaning / effect of raising |
|---|---|---|
| `n` | policies | Book size at cohort inception. 10000 keeps GLM fits stable; 1000 for smoke runs. |
| `cohort_year` | year | First policy year; simulation runs `n_years` forward. |
| `n_years` | years | Horizon; also the window length of the out-of-sample training book. |
| `seed` | int | Simulation RNG seed. Overridable per scenario (`"seed": 7`) and by `seeds.json`. |
| `regimes` | list of names | Pricing methods to run (names must exist in the registry). |
| `vehicle_mix` | share dict | Default ICE/EV split for scenarios without their own `vehicle`. |
| `pricing` | regime → overrides | Optional rate-card overrides; merged between method defaults and scenario overrides. Leave `{}` to use method defaults. |
| `reporting` | see below | Reporting constants (target band, appetite, retained drop, quantiles). |

## Book composition

| Key | Unit | Meaning / effect of raising |
|---|---|---|
| `coverage_pct` | share dict | Comprehensive / TPFT / TPO mix. More TPO lowers premium (TPO tariff underprices → tariff LR up). |
| `region_pct` | share dict | Peninsular / East Malaysia mix. |
| `generation_pct` | share dict | Driver generation mix. More Young Adults raises frequency. |
| `age_bands` | [lo, hi) | Exact age span per generation band. |
| `gender_pct` | share dict | Male / Female mix (young-male frequency loading). |
| `car_age_median` | years | Inception car age median per generation band. |
| `car_age_sigma` | years | Noise around the median; clipped to 0–10. |
| `sa_stats` | median RM, spread | Log-normal sum assured per fuel type, rounded to RM1,000. Higher median → higher tariff premium and severity (own-damage scales with SA). |
| `engine_bands` | labels | Engine/kW tariff bands; the simulation draws this attribute. 02a's rate tables must cover every band. |
| `engine_weights` | shares | Band mix; length must equal `engine_bands`. |
| `entrant_frac` | fraction of `n` | Yearly new business volume. |

## NCD

| Key | Unit | Meaning |
|---|---|---|
| `ncd_table` | discount by year | NCD discount lookup keyed 0–5 (years beyond 5 use the top tier). |
| `ncd_entry` | years + weights | Starting NCD years mix for new policies. |

## Frequency (Poisson log-rate)

| Key | Unit | Meaning / effect of raising |
|---|---|---|
| `claim_frequency_base` | log-rate | Base log frequency (−2.00 ≈ 13.5% before rating). Raise (+0.2 ≈ ×1.22 claims) to stress frequency. |
| `frequency.young_adult` / `.senior` | log add-on | Driver-band loadings. |
| `frequency.young_male` | log add-on | Interaction for Young Adults × Male. |
| `frequency.ev` | log add-on | EV frequency proxy. |
| `frequency.flood` / `.theft` | log add-on | Risk-flag loadings per true flag. |
| `frequency.car_age_per_year` | log/yr | Older car → more claims. |
| `frequency.ncd_per_year` | log/yr | Claim-free years reduce frequency. |
| `frequency.coverage_multiplier` | multiplier | Applied after exponentiating: TPFT 0.60, TPO 0.45, Comprehensive 1.00. |

## Risk flags

| Key | Unit | Meaning |
|---|---|---|
| `risk_flags.flood` | P(true) per region | Random draw per policy; implemented as `random() > 1 − p` (keeps legacy draw semantics). |
| `risk_flags.theft` | P(true) per region | Same mechanism. |

## Loadings (tariff-style loading applied by the tariff method)

| Key | Unit | Meaning |
|---|---|---|
| `loading.driver` | multiplier | Driver-band loading. |
| `loading.car_age_per_year` | fraction/yr | Vehicle-age loading; capped by `loading.car_age_cap`. |
| `loading.car_age_cap` | years | Age at which the loading stops growing. |

## Aging (year-on-year evolution)

| Key | Unit | Meaning |
|---|---|---|
| `aging.young_max` / `.adult_max` / `.mature_max` | age | Band upgrade thresholds (≤ young_max → Young, ≤ adult_max → Adult, ≤ mature_max → Mature, else Senior). |
| `aging.car_age_cap` | years | Car age stops increasing beyond this. |

## Severity (per-claim Gamma)

| Key | Unit | Meaning |
|---|---|---|
| `severity.perils` | ordered list | Draw order of perils — **order is part of the RNG sequence**; changing it changes every claim draw. |
| `severity.specs.<peril>.shape` | Gamma shape | Lower shape = heavier tail. |
| `severity.specs.<peril>.scale` | RM or SA rule | Number = absolute RM; object = `clip(SUM_ASSURED × sa_fraction, min, max)`. |
| `severity.specs.<peril>.cap` | RM / `"sum_assured"` / `null` | Payout cap per claim. |
| `severity.specs.<peril>.ev_loading` | bool | Whether `ev_severity_factor` multiplies this peril's scale. |
| `peril_dist` | shares per coverage | Peril mix used when drawing a claim's peril; keys must equal `severity.perils`. |
| `ev_severity_factor` | multiplier | EV repair loading (own-damage perils only, where `ev_loading` is true). |
| `severity_multiplier` | multiplier | Global claim-cost shock on every peril (1.20 = +20%). |

## Telematics generator

| Key | Unit | Meaning |
|---|---|---|
| `telematics.hard_braking` | Γ(shape, scale), max | Raw harsh-braking draw, clipped. |
| `telematics.speeding` | Γ(shape, scale), max | Raw speeding draw, clipped. |
| `telematics.night_driving` | β(a, b) × scale, max | Raw night-share draw, clipped. |
| `telematics.weights` | shares | Blend weights (must match the three inputs). |
| `telematics.score_max` / `.score_min` / `.score_span` | score | `score = clip(score_max − blend × score_span, score_min, score_max)` (higher = safer). |
| `behavior_risk.lo` / `.hi` | multiplier | Rank-mapped latent risk range; safest driver gets `lo`, riskiest `hi`. |

## Retention

| Key | Unit | Meaning |
|---|---|---|
| `retention.base` | probability | Baseline renewal probability. |
| `retention.claim_delta` | pp | Applied when a claim occurred. |
| `retention.clean_delta` | pp | Applied when claim-free. |
| `retention.ncd3_bonus` / `.ncd2_bonus` | pp | Loyalty bonuses at NCD ≥ 3 / ≥ 2. |
| `retention.telematics_high` | threshold + bonus + span | Safe-driver bonus scaling to the score. |
| `retention.telematics_mid` | threshold + bonus | Mid-score flat bonus. |
| `retention.behavior_penalty` | pp per unit | Penalty proportional to `BEHAVIOR_RISK − 1`. |
| `retention.clip` | [lo, hi] | Final probability clip. |

## Reporting

| Key | Unit | Meaning |
|---|---|---|
| `reporting.lr_target` | % band | Green band drawn on LR charts. |
| `reporting.lr_appetite` | % | Exceedance line: `P(LR > appetite)`. |
| `reporting.retained_drop` | fraction | Share of dearest policies dropped for retained-LR. |
| `reporting.quantiles` | fractions | Lower/upper quantiles reported across seeds. |

## Scenario files

Reserved keys in a scenario entry:

| Key | Meaning |
|---|---|
| `name` | Scenario name; used in file names and the manifest. |
| `vehicle` | `"ICE"` / `"EV"` / `"MIX"` or an explicit `{"ICE": 0.6, "EV": 0.4}`. |
| `seed` | Runs this scenario once with this seed (overrides `seeds.json`). |
| `pricing` | `{regime: {param: value}}` rate-card overrides; unknown params are rejected by the method's declared card. |

Everything else patches the template keys above (deep merge for nested dicts).

## Seeds

`seeds.json` — `{"seeds": [0, 1, 2]}`. Every scenario runs once per seed unless
it patches `seed`. Result files are always seed-suffixed:
`shared/results/<scenario>_s<seed>.pkl`.
