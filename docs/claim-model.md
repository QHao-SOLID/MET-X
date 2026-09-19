# Claim settlement & realism

The engine uses one **industry-calibrated claim model** (no modes, no switch).
The settlement rules are described function-by-function in
[How the simulation works](how-the-simulation-works.md); this page summarises
the payout rules and the realism scoreboard.

## Settlement at a glance

| Rule | Mechanics | Template keys |
|---|---|---|
| Theft | always a total loss: payout = sum assured − excess | `severity.specs.Theft` |
| Fire | mixed: 60% total loss, else Gamma partial − excess | `total_loss_prob`, `scale` |
| AD (own damage) | mixed: 8% total loss; partial severity from an **absolute RM** scale (not SA-proportional) | `total_loss_prob`, `scale`, `excess`, `young_excess` |
| Excesses | RM400 standard; RM1,500 for Young Adults; partial ≤ excess is not reported | `excess`, `young_excess` |
| Flood | event years: per-region Bernoulli activates the flood loading; the `FLOOD_RISK` flag prices exposure | `flood_event_prob` |
| Inflation | payouts compound by `(1 + severity_inflation)^(SIM_YEAR − cohort_year)` | `severity_inflation` |
| SA depreciation | sum assured marked down at renewal (market value, floor `sa_min`) | `sa_depreciation`, `sa_min` |
| Entrant growth | `n × entrant_frac × (1 + entrant_growth)^t` | `entrant_frac`, `entrant_growth` |
| EV | no explicit factor — higher sums assured flow through the total-loss and SA-linked rules | — |

## Realism checks (`analysis.ipynb` §10)

Every run is scored against `simulation/benchmarks.json` (sourced targets —
see [Benchmarks & sources](sources.md)). The default book (seed 42, full size)
passes 6/6:

| Metric | Sim | Target | Pass range | Status |
|---|---|---|---|---|
| own-damage claim rate | 6.9% | ~7% | 5–14% | PASS |
| avg claim severity | RM6,481 | RM8,831 | RM6–13k | PASS |
| theft claim rate | 0.16% | ~0.15%/yr | 0.05–0.4% | PASS |
| avg private-car premium | RM857 | ~RM950 | RM700–1,300 | PASS |
| retention | 90.7% | 85% | 75–92% | PASS |
| portfolio claims ratio (tariff) | 80.1% | 75% | 62–85% | PASS |

Legacy "pre-realism" numbers (the flavour of the original notebook) are kept in
git history, not in the running system: theft rate ~1.9% and avg premium
RM1,505 failed these checks by construction.

## Design rule that makes stress honest

Training data always comes from the **base** template world, never the
scenario's patched DGP (`ml.training_history`). Stressed scenarios therefore
price against unchanged historical experience and show honest loss-ratio
deterioration instead of pre-pricing the shock via inflated premiums.
