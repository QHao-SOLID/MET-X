# GLM method

Code: `simulation/voltvision/methods/glm.py` · regime name `glm`

Pure-premium risk model: Poisson frequency × observed severity × expense
loading. No tariff tables — the method learns from simulated experience.

## Rule sheet

| Piece | Rule |
|---|---|
| Frequency | `PoissonRegressor(alpha=glm_alpha)` on features below |
| Features | `DRIVER_AGE`, `CAR_AGE`, `NCD_LEVEL`, `VEHICLE_TYPE`, `COVERAGE_TYPE`, `FLOOD_RISK`, `THEFT_RISK`, `REGION` |
| Severity | mean `CLAIM_AMOUNT` per `CLAIM_COUNT` by (coverage, vehicle), coverage fallback |
| Premium | `freq × severity × expense_loading × risk_step^flags` |
| Training | `train_frac` of first-year rows of a **separate historical book** (see below) |

## Declared rate card

| Param | Default | Unit | Note |
|---|---|---|---|
| `expense_loading` | 1.5 | multiplier | pure-premium loading; raise → lower LR |
| `risk_step` | 1.1 | per flag | multiplier per true risk flag |
| `glm_alpha` | 1e-3 | L2 penalty | Poisson regularization |
| `train_frac` | 0.6 | fraction | share of training rows used to fit |
| `train_seed` | 7 | seed | train-split seed |
| `train_book_seed` | 42 | seed or null | separate historical book; `null` = in-sample (comparison only) |
| `train_window_years` | 5 | years | training horizon, one period before the priced cohort |
| `train_vehicle` | null | share dict | training fleet mix; null = training world `vehicle_mix` |
| `train_dgp` | {} | engine overrides | extra training-world assumptions |

## Training-world rule

The training book is generated from the **base template world**, one window
earlier (`ml.training_history`) — scenario DGP patches never flow into training.
Stressed scenarios therefore price against unchanged historical experience and
show honest loss-ratio deterioration instead of pre-pricing the shock via
inflated premiums.

Override example:

```json
{"name": "glm_loaded", "pricing": {"glm": {"expense_loading": 1.8}}}
```
