"""Stress testing: declarative scenario grids over CFG (DGP) and RateCard (pricing).

Grid = list of scenario dicts:
  {'name': 'freq_up', 'cfg': {'claim_frequency_base': -1.80},
   'card': {'expense_loading': 1.6}, 'vehicle': 'MIX'}

run_stress() deep-merges each cfg override onto CFG, simulates the book once
per (scenario, seed), prices every regime with the scenario's card overrides,
and returns one tidy row per (scenario, seed, regime).

Design notes:
- Overrides are DEEP-merged: {'coverage_pct': {'TPO': 0.35}} touches only TPO.
- Seeds re-draw simulation noise; scenario × seeds defines the grid size.
- Training books are cached per DGP fingerprint (pricing.training_book), so
  scenario pricing reuses one synthetic history across seeds.
- Results are tidy (long form) so pivots/plots/CSV exports are trivial.
"""

import pandas as pd

from .config import CFG, SCEN, N_YEARS, REGIMES
from .simulate import gen, simulate
from .pricing import RateCard, quote, lr, retained_lr, rho, ensure_core_methods


def deep_update(base, overrides):
    # Recursive merge: dict values merge key-by-key, everything else replaces.
    # Returns a new dict; the base is never mutated (scenarios stay reusable).
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in (overrides or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = v
    return out


def run_stress(scenarios, seeds=(0, 1, 2), regimes=REGIMES, vehicle='MIX',
               quick=False, n_years=None, verbose=True):
    # Execute a scenario grid. Each row: scenario name, seed, regime + metrics.
    # vehicle: default book ('ICE' | 'EV' | 'MIX'); per-scenario override wins.
    ensure_core_methods()
    base = dict(CFG)
    if quick:
        base['n'] = 1000
    years = int(n_years or (2 if quick else N_YEARS))
    rows = []
    for scen in scenarios:
        name = scen['name']
        vp = SCEN[scen.get('vehicle', vehicle)]
        cfg = deep_update(base, scen.get('cfg'))
        card_ov = scen.get('card', {})
        if verbose:
            print(f"--- {name}: cfg={scen.get('cfg') or '-'} card={card_ov or '-'}")
        for s in seeds:
            book = simulate(gen(cfg, vp, s), cfg, vp, seed=s,
                            n_years=years, verbose=False)
            for m in regimes:
                b = quote(book, m, RateCard.from_cfg(cfg, **card_ov))
                rows.append({'scenario': name, 'seed': s, 'regime': m,
                             'lr': round(lr(b), 2),
                             'retained_lr': round(retained_lr(b), 2),
                             'rho': round(rho(b), 4),
                             'avg_prem': round(float(b['FINAL_PREMIUM_SST'].mean()), 0),
                             'rows': len(b)})
    return pd.DataFrame(rows)


def stress_summary(df, threshold=75.0):
    # Per (scenario, regime): mean/spread of LR and exceedance probability.
    # threshold = LR appetite line (default 75%).
    g = df.groupby(['scenario', 'regime'])
    out = g.agg(mean_lr=('lr', 'mean'), p05_lr=('lr', lambda x: x.quantile(0.05)),
                p95_lr=('lr', lambda x: x.quantile(0.95)),
                mean_rho=('rho', 'mean'),
                p_lr_gt_thr=('lr', lambda x: (x > threshold).mean()),
                n=('lr', 'size')).reset_index()
    out.columns = ['scenario', 'regime', 'mean_lr', 'p05_lr', 'p95_lr', 'mean_rho',
                   f'p_lr_gt_{int(threshold)}', 'n']
    return out


def stress_pivot(df, value='lr', agg='mean'):
    # Scenario x regime pivot of any tidy-df column, ready for display.
    return df.pivot_table(index='scenario', columns='regime', values=value,
                          aggfunc=agg)
