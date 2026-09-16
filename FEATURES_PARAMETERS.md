# VoltVision — Feature & Parameter Documentation

## 1. Features

### 1.1 Policy attributes (generated, fixed at inception)
| Feature | Values / distribution | Drives |
|---|---|---|
| `COVERAGE_TYPE` | Comprehensive 65%, TPFT 20%, TPO 15% | frequency multiplier (1.0 / 0.60 / 0.45), peril mix, tariff formula |
| `VEHICLE_TYPE` | ICE / EV (scenario switch) | +0.05 log-freq if EV; 1.2× severity on AD/Theft/Fire |
| `SUM_ASSURED` | Log-normal, ICE λ=50k / EV λ=80k, σ=0.5, rounded RM1k | Comp graduated tariff; TPO +0.5% SA component |
| `ENGINE_CAPACITY` | 8 bands, weights [0.25…0.02] small-car heavy | tariff BASIC lookup |
| `REGION` | Peninsular 80% / East MY 20% | BASIC table + PER_EXTRA rate |
| `DRIVER_AGE_CAT` / `DRIVER_AGE` | Young≤27 / Adult≤45 / Mature≤65 / Senior; 40/40/15/5% | +0.40 Young, +0.26 Senior, +0.05 young-male; driver loading 1.20/1.05/1.00/1.05 |
| `DRIVER_GENDER` | Male 55% / Female 45% | young-male interaction only |
| `CAR_AGE` | 0–10, median 2.0/3.5/5.0/5.5 by age band | +0.03/yr freq; 1.03×/yr loading (cap 10) |
| `FLOOD_RISK` / `THEFT_RISK` | Region-dependent booleans | +0.20/+0.10 log-freq; 1.1× premium each |
| `NCD_YEARS` / `NCD_LEVEL` | Entry 0–5 (30/22/16/13/10/9%) → 0/25/30/38.3/45/55% | −0.05/yr freq; tariff ×(1−NCD); GLM feature; claim resets to 0 |
| `telematics_score` / `BEHAVIOR_RISK` | HB+speed+night composite → 20–100; rank-mapped risk 1.30–0.90 | log-risk multiplier; telem-only pricing feature |
| `BASIC_PREMIUM` | Tariff schedule lookup at inception | tariff premium anchor |

### 1.2 Simulated labels (premium-independent, identical for all 3 regimes)
| Feature | Generation |
|---|---|
| `CLAIM_LAMBDA` | exp(base + age + EV + flags + log(behavior) + car age − NCD) × coverage mult |
| `CLAIM_COUNT` | Poisson(λ) per policy-year |
| `CLAIM_PERIL` | Coverage peril mix (TPO: 78% TPPD / 22% TPBI) |
| `CLAIM_AMOUNT` | Gamma per peril (TPBI 0.35/70000 uncapped; TPPD 0.55/9000 cap 3M; own-damage SA-bound); EV ×1.2 on AD/Theft/Fire |
| `RENEWED` | Experience + telematics retention, premium-independent |
| `FINAL_PREMIUM_SST` | Applied post-simulation per regime +8% SST |

### 1.3 Pricing regimes (same book, three prices — never one alone)
| Regime | Formula | Learns |
|---|---|---|
| Tariff | Comp/TPFT: BASIC·loading·(1−NCD)·1.1^risk·1.08; TPO: (BASIC+0.5%·SA)·1.10·risk·1.08 | nothing (schedule) |
| GLM | Poisson freq × (coverage,vehicle) avg severity ×1.5 ×risk | age, car age, NCD, vehicle, coverage, flags, region |
| GLM+Telematics | same + telematics_score | + driver behavior |

## 2. Parameters (change in simplified notebook Cell 3 unless noted)
| Param | Default | Effect / sensitivity |
|---|---|---|
| `VEHICLE_SCENARIO` | `"ALL"` | `"ICE"` 100% ICE / `"EV"` 100% EV / `"MIX"` 50-50 / `"ALL"` loop all |
| `claim_frequency_base` | −2.00 | −1.80 ≈ +22% frequency (MC stress scenario) |
| `ev_severity_factor` | 1.20 | EV repair loading; own-damage perils only, NOT TPPD/TPBI |
| `tpo_sa_pct` / `tpo_loading` | 0.005 / 1.10 | TPO tariff linkage — **root cause of TPO LR 107–179%; raise SA pct to ~1.5% to fix** |
| `expense_loading` | 1.50 | GLM/telem pure-premium multiplier; higher → lower LR |
| `n` / `N_YEARS` / `SEED` | 10000 / 5 / 20260916 | size / horizon / reproducibility |
| `entrant_frac` | 0.50 | entrants per year as fraction of n; growth 0, no EV ramp (simplification) |
| `RUN_MC` (Cell 10) | `False` | `True` → 18-run grid (2 freq × 3 seeds × 3 regimes) with P(LR>75%) insight |
| GLM training | in-sample 60% split | Simplification vs master (out-of-sample train book); LR ~4pp more optimistic, same ranking |

## 3. TPO loss-ratio diagnostic (why tariff TPO explodes)
- Expected: freq 0.45·e^−2 ≈ 0.061 × E[sev] (0.78·4950+0.22·24500 = RM9251) ≈ **RM563** cost vs ≈RM570 premium → theory LR ≈99%.
- Actual tariff TPO LR: ICE **143–179%**, EV **107–123%** (simplified–master range; same cause).
- Gap drivers: (1) TPBI Gamma(0.35) infinite variance — few huge claims dominate; (2) flat BASIC + only 0.5% SA cushion;
  (3) ICE SA λ=50k gives smaller cushion than EV λ=80k → ICE worse; (4) 5-yr compounding.
- GLM re-rates TPO off its own claims (TPO prem RM565→RM1210 ICE) → LR 62–81%. Telematics adds ~0pp here (behavior already in GLM via NCD/age proxies); value shows in prem-count rho (0.36→0.64).
