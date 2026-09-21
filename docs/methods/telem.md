# Telematics method

Code: `simulation/voltvision/methods/telem.py` · regime name `telem`

GLM plus the device score. Everything else (severity, target-LR anchor, NCD
treatment, training setup) is shared with [GLM](glm.md).

## Rule sheet

| Piece | Rule |
|---|---|
| Telematics scope | **EV-only** — device data only exists for EVs, so `telematics_score` is `NaN` for ICE. The latent `BEHAVIOR_RISK` still exists for every vehicle (and still drives frequency + the retention behaviour penalty); only the observable score is EV-only. |
| Frequency | **two models**: EV = GLM features + `telematics_score` (trained on EV-only rows); ICE = GLM features (trained on ICE-only rows) |
| `telematics_score` | 0–100 simulated per EV policy (higher = safer); rank-mapped to the latent `BEHAVIOR_RISK`; no raw trip data needed |
| Severity | identical to GLM (coverage × vehicle average, coverage fallback) |
| Premium | `freq × severity ÷ target_lr × (1 − NCD_LEVEL) × risk_step^flags` |
| NCD | statutory post-model discount, TPO exempt — identical to GLM |
| Training | identical out-of-sample setup as GLM (base template world); EV model trained on EV rows, ICE model on ICE rows |

## Declared rate card

Same parameters as [GLM](glm.md#declared-rate-card) (`target_lr`,
`risk_step`, `glm_alpha`, training block) — declared independently in this
module, so the two methods can be tuned separately per scenario.

Override example:

```json
{"name": "telem_loaded", "pricing": {"telem": {"target_lr": 0.60}}}
```

## What the score buys

On the EV segment, telematics reprices high-risk drivers upward and flattens
loss ratios across score bands; ICE is priced like GLM (no device score). See
§6 of `analysis.ipynb` (EV-only tiers).
