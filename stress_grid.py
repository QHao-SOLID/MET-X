"""Stress scenario grid — EDIT ME.

Each entry:
  name    : label shown in results
  cfg     : DGP overrides, deep-merged onto CFG (see voltvision/config.py)
  card    : RateCard overrides for pricing (expense_loading, tpo_loading...)
  vehicle : optional 'ICE' | 'EV' | 'MIX' for this scenario (default MIX)

Useful DGP stress levers:
  claim_frequency_base  log base rate: -2.00 baseline; -1.80 ~= +22% claims;
                        -1.60 ~= +49% claims
  severity_multiplier   global claim-cost shock on EVERY peril (1.20 = +20%)
  ev_severity_factor    EV repair loading on AD/Theft/Fire (baseline 1.20)
  coverage_pct          product mix, e.g. {'Comprehensive': 0.45, 'TPFT': 0.20,
                        'TPO': 0.35} for a TPO-heavy book
  entrant_frac          yearly new business as a share of n (baseline 0.50)

Useful pricing levers (card): expense_loading, tpo_loading, tpo_sa_pct,
risk_step, train_book_seed (None = legacy in-sample).
"""

SCENARIOS = [
    # Reference: no overrides.
    {'name': 'base', 'cfg': {}, 'card': {}},

    # Claims inflation: frequency only.
    {'name': 'freq_x1.22', 'cfg': {'claim_frequency_base': -1.80}},
    {'name': 'freq_x1.49', 'cfg': {'claim_frequency_base': -1.60}},

    # Claims inflation: severity only (all perils).
    {'name': 'sev_x1.20', 'cfg': {'severity_multiplier': 1.20}},
    {'name': 'sev_x1.35', 'cfg': {'severity_multiplier': 1.35}},

    # EV repair costs run hot (own-damage perils on EVs).
    {'name': 'ev_sev_1.40', 'cfg': {'ev_severity_factor': 1.40}},

    # Adverse product mix: more third-party-only cover (weakest tariff leg).
    {'name': 'tpo_heavy', 'cfg': {'coverage_pct': {'Comprehensive': 0.45, 'TPFT': 0.20, 'TPO': 0.35}}},

    # EV-only book (worst-case EV adoption).
    {'name': 'ev_only', 'cfg': {}, 'card': {}, 'vehicle': 'EV'},

    # Pricing response scenarios: loadings raised to defend the LR.
    {'name': 'prudent_load', 'cfg': {}, 'card': {'expense_loading': 1.80, 'tpo_loading': 1.35}},
    {'name': 'tpo_reprice', 'cfg': {}, 'card': {'tpo_sa_pct': 0.010, 'tpo_loading': 1.35}},

    # Combined stress: claims inflation + hot EV + higher loadings (resilience test).
    {'name': 'combo_hard', 'cfg': {'claim_frequency_base': -1.70, 'severity_multiplier': 1.15,
                                   'ev_severity_factor': 1.35},
     'card': {'expense_loading': 1.70}},
]
