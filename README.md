# MET-X — VoltVision motor portfolio simulation + pricing lab

Synthetic Malaysian motor book (IFoA VoltVision, post-detariffication context),
built as two deliberately separated systems:

1. **Simulation** — premium-independent engine (`voltvision/simulate.py`).
   Generates policy books and evolves them over `n_years` (frequency → peril →
   severity → retention → NCD). Claims are shared by every pricing method;
   no premium is ever simulated.
2. **Pricing** — black-box methods (`02a`/`02b`/`02c` notebooks) behind one
   standard interface: `func(book, card, cfg) -> book + FINAL_PREMIUM_SST`.
   The system never knows what a method's parameters mean — each method
   declares its own rate card.

## Quickstart

```bash
python run_scenarios.py            # all scenarios x seeds.json -> shared/results/
python run_scenarios.py --quick    # smoke run (n=1000, 2 years)
python run_scenarios.py --scenarios mix_60_40,tpo_heavy
python run_scenarios.py --excel MIX_s0
```

Every run produces ONE combined file: `shared/results/<scenario>_s<seed>.pkl`
= simulated book + one `PREM_<regime>` column per pricing method — plus
`shared/results/manifest.json` holding the cfg/cards snapshot and per-regime
metrics (LR, retained LR, rho, average premium).

## Layout

| Path | What it is |
|---|---|
| `base_template.json` | every simulation assumption (documented in `TEMPLATE.md`) |
| `scenarios/*.json` | flat patches on the template — one file = one group |
| `seeds.json` | seeds every scenario runs, unless a scenario patches its own |
| `run_scenarios.py` | the loop: simulate → price → combine → save |
| `02_pricing.ipynb` | pricing desk: resolve cards, quote, compare, what-if, add a method |
| `02a_tariff.ipynb` / `02b_glm.ipynb` / `02c_telem.ipynb` | the pricing methods (each owns its numbers + math) |
| `04_analysis.ipynb` | full analysis, reads `shared/results/` only |
| `voltvision/` | engine (`simulate`), connector (`pricing`), runner, io, schema |
| `voltvision_all.ipynb`, `voltvision_simple.ipynb` | frozen reference notebooks (do not edit) |

## Parity baseline (full size, seed 20260916)

| Book | Tariff | GLM | GLM+Telematics |
|---|---|---|---|
| ICE | 73.02% | 62.05% | 62.13% |
| EV | 70.72% | 63.75% | 63.83% |
| MIX | 74.45% | 62.87% | 62.89% |

Any refactor must reproduce these numbers (see `AGENT.md` for the exact check).
