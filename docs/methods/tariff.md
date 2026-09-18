# Tariff method

Code: `simulation/voltvision/methods/tariff.py` · regime name `tariff`

The tariff method owns **all** tariff numbers: the 2015 schedule tables, its
knobs, and the premium formula. Nothing tariff-specific exists anywhere else.

## Rule sheet

| Piece | Rule |
|---|---|
| Comprehensive / TPFT | `BASIC × loading × (1 − NCD) × risk_step^flags × (1 + sst)` |
| TPO | `(BASIC + tpo_sa_pct × SA) × tpo_loading × risk_step^flags × (1 + sst)` — no cover loading, no NCD |
| `BASIC` | Schedule of Motor Tariff 2015, graduated: Comp = first-RM1,000 rate + `PER_EXTRA` per extra RM1,000 of SA; TPFT = 75% of Comp; TPO = flat table rate |
| `loading` | driver band (1.20 / 1.05 / 1.00 / 1.05) × (1 + 0.03 × min(CAR_AGE, 10)) |
| `flags` | count of true `FLOOD_RISK` + `THEFT_RISK` |
| Band labels | must match `base_template.json → engine_bands` exactly (validated at price time) |

## Declared rate card

| Param | Default | Unit | Note |
|---|---|---|---|
| `sst` | 0.08 | fraction | premium tax on the tariff leg |
| `tpo_sa_pct` | 0.005 | fraction of SA | TPO SA-linked premium slice |
| `tpo_loading` | 1.10 | multiplier | TPO fixed loading |
| `risk_step` | 1.1 | per flag | multiplier for each true risk flag |

Override per scenario:

```json
{"name": "tpo_reprice", "pricing": {"tariff": {"tpo_sa_pct": 0.010, "tpo_loading": 1.35}}}
```

## Known behaviour

The TPO leg prices below expected cost (TPO loss ratio >100%) with the default
knobs — an intentional teaching point. Raise `tpo_sa_pct` / `tpo_loading` (as in
`tpo_reprice`) to bring TPO LR toward the portfolio band.
