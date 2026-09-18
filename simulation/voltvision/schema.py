"""Structural schema — the parts the system must know by shape (never by value).

What lives here:
  COLS      canonical simulated-book column order (attributes + claims only)
  PREM_     premium column naming rule for combined results: PREM_<regime>
  REGIME_RE regime names must match this (safe for column names / JSON keys)

Everything numeric lives in base_template.json (simulation assumptions) or in
the owning pricing method module (rate cards). This file holds no assumptions.
"""

import re

# Canonical simulated-book column order (simulate.py output). Priced books and
# combined result files keep these columns first, then append PREM_<regime>.
COLS = ['POLID', 'COVERAGE_TYPE', 'SUM_ASSURED', 'REGION', 'VEHICLE_TYPE',
        'ENGINE_CAPACITY',
        'DRIVER_AGE_CAT', 'DRIVER_AGE', 'CAR_AGE', 'DRIVER_GENDER',
        'FLOOD_RISK', 'THEFT_RISK',
        'NCD_LEVEL_PRICED', 'NCD_LEVEL',
        'NCD_YEARS', 'CLAIM_LAMBDA',
        'SIM_YEAR', 'CLAIM_COUNT', 'CLAIM_OCCURRED', 'CLAIM_AMOUNT',
        'CLAIM_PERIL',
        'RENEWAL_PROB', 'RENEWED', 'COHORT_YEAR',
        'BEHAVIOR_RISK', 'telematics_score']

# Combined result files carry one premium column per regime: PREM_<regime>.
# e.g. PREM_tariff, PREM_glm, PREM_telem, PREM_floor_demo — any N.
PREM_PREFIX = 'PREM_'

# Regime names must be identifier-safe (used in column names, JSON keys, logs).
REGIME_RE = re.compile(r'^[A-Za-z0-9_]+$')


def premium_column(regime):
    """Column name holding one regime's premium in a combined result file."""
    return f'{PREM_PREFIX}{regime}'


def check_regime_name(name):
    """Register-time guard: names must be identifier-safe for PREM_ columns."""
    if not isinstance(name, str) or not REGIME_RE.match(name):
        raise ValueError(
            f"regime name {name!r} invalid — use letters, digits, underscore "
            "(it becomes the PREM_ column and result file naming)")
    return name
