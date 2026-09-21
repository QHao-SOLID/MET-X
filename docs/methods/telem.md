# Telematics method

Code: `simulation/voltvision/methods/telem.py` · regime name `telem`

GLM plus the device score. Everything else (severity, target-LR anchor, NCD
treatment, training setup) is shared with [GLM](glm.md).

## Rule sheet

| Piece | Rule |
|---|---|
| Telematics scope | **EV-only** — device data only exists for EVs, so `telematics_score` is `NaN` for ICE. The latent `BEHAVIOR_RISK` still exists for every vehicle (and still drives frequency + the retention behaviour penalty); only the observable score is EV-only. |
| Frequency | **two models**: EV = GLM features + `telematics_score` (trained on a **full-EV** book); ICE = GLM features (trained on a **full-ICE** book) |
| `telematics_score` | 0–100 simulated per EV policy (higher = safer); rank-mapped to the latent `BEHAVIOR_RISK`; no raw trip data needed |
| Severity | coverage × vehicle average, coverage fallback — EV severity from the EV book, ICE severity from the ICE book |
| Premium | `freq × severity ÷ target_lr × (1 − NCD_LEVEL) × risk_step^flags` |
| NCD | statutory post-model discount, TPO exempt — identical to GLM |
| Training | identical out-of-sample setup as GLM (base template world); `train_vehicle_ev` (`{"EV": 1.0}`) and `train_vehicle_ice` (`{"ICE": 1.0}`) give each model a full-fuel book |

## Declared rate card

Same parameters as [GLM](glm.md#declared-rate-card) (`target_lr`,
`risk_step`, `glm_alpha`, training block) — declared independently in this
module, so the two methods can be tuned separately per scenario. Instead of
GLM's single `train_vehicle`, telematics declares `train_vehicle_ev` and
`train_vehicle_ice`.

Override example:

```json
{"name": "telem_loaded", "pricing": {"telem": {"target_lr": 0.60}}}
```

## What the score buys

On the EV segment, telematics reprices high-risk drivers upward and flattens
loss ratios across score bands; ICE is priced like GLM (no device score). See
§6 of `analysis.ipynb` (EV-only tiers).
