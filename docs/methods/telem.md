# Telematics method

Code: `simulation/voltvision/methods/telem.py` · regime name `telem`

GLM plus the device score. Everything else (severity, loadings, training
setup) is shared with [GLM](glm.md).

## Rule sheet

| Piece | Rule |
|---|---|
| Frequency | same Poisson setup as GLM, features = GLM set + `telematics_score` |
| `telematics_score` | 0–100 simulated per policy (higher = safer); rank-mapped to the latent `BEHAVIOR_RISK`; no raw trip data needed |
| Severity | identical to GLM (coverage × vehicle average, coverage fallback) |
| Premium | `freq × severity × expense_loading × risk_step^flags` |
| Training | identical out-of-sample setup as GLM (base template world) |

## Declared rate card

Same parameters as [GLM](glm.md#declared-rate-card) (`expense_loading`,
`risk_step`, `glm_alpha`, training block) — declared independently in this
module, so the two methods can be tuned separately per scenario.

Override example:

```json
{"name": "telem_loaded", "pricing": {"telem": {"expense_loading": 1.8}}}
```

## What the score buys

Portfolio loss ratio barely moves versus GLM (both calibrate to the same mean
frequency). The score's value shows in **segmentation**: the high-risk
telematics tier gets repriced upward, flattening loss ratios across score
bands — see §6 of `analysis.ipynb`.
