# VoltVision motor engine - shared simulation + pricing library.
# Imported by main.ipynb (simulation + three-regime comparison + data export)
# and analysis.ipynb (Monte Carlo + consolidated report).
#
# Layout:
#   1. Imports
#   2. Utility helpers
#   3. Configuration / assumptions (single source of truth)
#   4. Data generation (initial cohort + entrants)
#   5. Risk models (claim frequency)
#   6. Simulation engine (vectorized)
#   7. PRICING MODELS (Tariff | GLM | GLM+Telematics) - all pricing together

import copy
import json
import os
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import PoissonRegressor

try:
    from joblib import Parallel, delayed
    _HAS_JOBLIB = True
except ImportError:
    _HAS_JOBLIB = False


# ============================================================================
# 2. UTILITY HELPERS
# ============================================================================

def deep_update(base, overrides):
    """Deep-copy base and recursively merge overrides (None-safe)."""
    out = copy.deepcopy(base)
    if not overrides:
        return out
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = v
    return out


def interp_schedule(sched, year):
    """Linear interpolation of a {year: value} schedule (clamped at ends).
    Empty schedule -> 0.0 (no ramp configured)."""
    yrs = sorted(sched)
    if not yrs:
        return 0.0
    if year <= yrs[0]:
        return sched[yrs[0]]
    if year >= yrs[-1]:
        return sched[yrs[-1]]
    for a, b in zip(yrs, yrs[1:]):
        if a <= year <= b:
            t = (year - a) / (b - a)
            return sched[a] + t * (sched[b] - sched[a])


# ============================================================================
# 3. CONFIGURATION / ASSUMPTIONS - single source of truth
# ============================================================================

ENGINE_CAPACITY_BANDS = [
    "0 to 1,400 cc / EV up to 70 kW",
    "1,401 to 1,650 cc / EV 71 - 100 kW",
    "1,651 - 2,200 cc / EV 101 - 125 kW",
    "2,201 - 3,050 cc / EV 126 - 150 kW",
    "3,051 - 4,100 cc / EV 151 - 200 kW",
    "4,101 - 4,250 cc / EV 201 - 250 kW",
    "4,251 - 4,400 cc / EV 251 - 300 kW",
    "Over 4,400 cc / EV > 300 kW",
]

COHORT_CONFIG = {
    'n': 10000,
    'coverage_pct': {
        'Comprehensive': 0.65,
        'TPFT': 0.20,
        'TPO': 0.15
    },
    'vehicle_pct': {
        'ICE': 0.90,
        'EV': 0.10
    },
    'sa_stats': {
        'ICE': {
            'lambda': 50000,
            'spread': 0.5
        },
        'EV': {
            'lambda': 80000,
            'spread': 0.5
        }
    },
    'region_pct': {
        'Peninsular Malaysia': 0.80,
        'East Malaysia (Sabah, Sawarak & Labuan)': 0.20
    },
    'generation_pct': {
        'Young Adults': 0.40,
        'Adults': 0.40,
        'Mature Adults': 0.15,
        'Seniors': 0.05
    },
    'age_bands': {
        'Young Adults': (18, 28),
        'Adults': (28, 46),
        'Mature Adults': (46, 66),
        'Seniors': (66, 76)
    },
    'gender_pct': {
        'Male': 0.55,
        'Female': 0.45
    },
    'marital_pct': {
        'Young Adults': {'Single': 0.85, 'Married': 0.15},
        'Adults': {'Single': 0.50, 'Married': 0.50},
        'Mature Adults': {'Single': 0.20, 'Married': 0.80},
        'Seniors': {'Single': 0.20, 'Married': 0.80}},
    'car_age_median': {
        'Young Adults': 2.0,
        'Adults': 3.5,
        'Mature Adults': 5.0,
        'Seniors': 5.5
    },
    'car_age_sigma': 1.5,
    'risk_pct': {
        'Peninsular Malaysia': {
            'FLOOD_RISK': [0.60, 0.40],
            'THEFT_RISK': [0.40, 0.60]
        },
        'East Malaysia (Sabah, Sawarak & Labuan)': {
            'FLOOD_RISK': [0.00, 1.00],
            'THEFT_RISK': [0.15, 0.85]
        }
    },
    'ncd_table': {
        0: 0.0000, 1: 0.2500, 2: 0.3000,
        3: 0.3833, 4: 0.4500, 5: 0.5500
    },
    'ncd_entry': {
        'years': [0, 1, 2, 3, 4, 5],
        'weights': [0.30, 0.22, 0.16, 0.13, 0.10, 0.09]
    },
    'cohort_year': 2026,
    'claim_frequency_base': -2.00,
    'ev_severity_factor': 1.20,  # explicit EV repair-cost premium on SA-bound perils (AD/Theft/Fire)

    'behavior_risk': {'lo': 0.90, 'hi': 1.30},   # claim-freq multiplier
    'telemetry': {
        'hb_shape': 2.0, 'hb_scale': 1.8, 'hb_age': -0.15, 'hb_max': 15,
        'sp_shape': 2.0, 'sp_scale': 6.0, 'sp_age': -1.0, 'sp_max': 50,
        'nd_a': 2, 'nd_b': 5, 'nd_scale': 40, 'nd_age': -1.5, 'nd_max': 50,
        'w_hb': 0.45, 'w_sp': 0.40, 'w_nd': 0.15, 'score_lo': 20, 'score_hi': 100,
    },
    'telemetric_load': 1.0000,   # extra multiplier on telematics premium (user lever)
    'expense_loading': 1.0000,  # uniform loading on GLM/telem pure premiums (LR target ~71%)
    'engine_weights': [0.25, 0.20, 0.18, 0.15, 0.10, 0.07, 0.03, 0.02],
    'seed': 42,
    'entrant_profile': {},
    'ev_share_by_year': {
        2026: 0.10, 2027: 0.16, 2028: 0.23, 2029: 0.31, 2030: 0.40, 2035: 0.45, 2040: 0.50, 2045: 0.55
    },
    'entrant_annual_growth': 0.03,
    'entrant_ncd_zero': False,
}

MODEL_TRAIN_SEED = 20260818  # GLM/telem training cohort seed (out-of-sample vs TEST_SEED)
TEST_SEED = COHORT_CONFIG['seed']  # the priced/test book seed (=42)

COHORT_CONFIG['entrant_base_count'] = int(0.50 * COHORT_CONFIG['n'])

DRIVER_AGE_LOADING = {
    "Young Adults": 1.20,
    "Adults": 1.05,
    "Mature Adults": 1.00,
    "Seniors": 1.05,
}

PERIL_DIST = {
    'Comprehensive': {
        'AD': 0.58, 'Windscreen': 0.15, 'Theft': 0.08,
        'Fire': 0.04, 'TPPD': 0.12, 'TPBI': 0.03
    },
    'TPO': {
        'TPPD': 0.78, 'TPBI': 0.22
    },
    'TPFT': {
        'TPPD': 0.444, 'TPBI': 0.111,
        'Theft': 0.296, 'Fire': 0.148
    }
}

PERIL_BASE = {
    'TPBI':       {'shape': 0.35, 'scale': 70000, 'cap': float('inf')},
    'TPPD':       {'shape': 0.55, 'scale': 9000,  'cap': 3000000},
    'Windscreen': {'shape': 2.00, 'scale': 700,   'cap': 15000}
}

# BASIC PREMIUM - Schedule of Motor Tariff 2015 (Form 5 Mathematics Ch.3)
# Graduated tariff:
#   Comprehensive = first-RM1,000 rate + PER_EXTRA x ceil((SA-1000)/1000)
#   TPFT (Third Party, Fire & Theft) = 0.75 x Comprehensive basic (Example 3)
#   TPO = flat tariff rate (no sum-assured scaling)
PER_EXTRA = {
    'Peninsular Malaysia': 26.00,
    'East Malaysia (Sabah, Sawarak & Labuan)': 20.30,
}

MOTOR_TARIFF = {
    'Peninsular Malaysia': {
        'Comprehensive': {
            '0 to 1,400 cc / EV up to 70 kW': 273.80,
            '1,401 to 1,650 cc / EV 71 - 100 kW': 305.50,
            '1,651 - 2,200 cc / EV 101 - 125 kW': 339.10,
            '2,201 - 3,050 cc / EV 126 - 150 kW': 372.60,
            '3,051 - 4,100 cc / EV 151 - 200 kW': 404.30,
            '4,101 - 4,250 cc / EV 201 - 250 kW': 436.00,
            '4,251 - 4,400 cc / EV 251 - 300 kW': 469.60,
            'Over 4,400 cc / EV > 300 kW': 501.30,
        },
        'TPO': {
            '0 to 1,400 cc / EV up to 70 kW': 120.60,
            '1,401 to 1,650 cc / EV 71 - 100 kW': 135.00,
            '1,651 - 2,200 cc / EV 101 - 125 kW': 151.20,
            '2,201 - 3,050 cc / EV 126 - 150 kW': 167.40,
            '3,051 - 4,100 cc / EV 151 - 200 kW': 181.80,
            '4,101 - 4,250 cc / EV 201 - 250 kW': 196.20,
            '4,251 - 4,400 cc / EV 251 - 300 kW': 212.40,
            'Over 4,400 cc / EV > 300 kW': 226.80,
        },
    },
    'East Malaysia (Sabah, Sawarak & Labuan)': {
        'Comprehensive': {
            '0 to 1,400 cc / EV up to 70 kW': 196.20,
            '1,401 to 1,650 cc / EV 71 - 100 kW': 220.00,
            '1,651 - 2,200 cc / EV 101 - 125 kW': 243.90,
            '2,201 - 3,050 cc / EV 126 - 150 kW': 266.50,
            '3,051 - 4,100 cc / EV 151 - 200 kW': 290.40,
            '4,101 - 4,250 cc / EV 201 - 250 kW': 313.00,
            '4,251 - 4,400 cc / EV 251 - 300 kW': 336.90,
            'Over 4,400 cc / EV > 300 kW': 359.50,
        },
        'TPO': {
            '0 to 1,400 cc / EV up to 70 kW': 67.50,
            '1,401 to 1,650 cc / EV 71 - 100 kW': 75.60,
            '1,651 - 2,200 cc / EV 101 - 125 kW': 85.20,
            '2,201 - 3,050 cc / EV 126 - 150 kW': 93.60,
            '3,051 - 4,100 cc / EV 151 - 200 kW': 101.70,
            '4,101 - 4,250 cc / EV 201 - 250 kW': 110.10,
            '4,251 - 4,400 cc / EV 251 - 300 kW': 118.20,
            'Over 4,400 cc / EV > 300 kW': 126.60,
        },
    },
}

SST_RATE = 0.08  # Changeable variable - current SST rate in Malaysia


# ============================================================================
# 4. DATA GENERATION (initial cohort + entrants)
# ============================================================================

def _p(weights):
    """Normalise weights to sum exactly to 1 (float-safe for np.random.choice)."""
    a = np.array(list(weights), dtype=float)
    return a / a.sum()


def driver_age_loading(age_cat):
    return DRIVER_AGE_LOADING.get(age_cat, 1.00)


def car_age_loading(car_age):
    """Linear vehicle-age loading; car age capped at 10 years."""
    return 1 + 0.03 * min(int(car_age), 10)


def total_loading(age_cat, car_age):
    """Combined driver x vehicle loading applied to the premium."""
    return driver_age_loading(age_cat) * car_age_loading(car_age)


def basic_premium_array(df, cfg=COHORT_CONFIG):
    """Vectorized BASIC_PREMIUM per Schedule of Motor Tariff 2015 (graduated)."""
    mt = cfg.get('motor_tariff', MOTOR_TARIFF)
    pe = cfg.get('per_extra', PER_EXTRA)
    region = df['REGION'].values
    eng = df['ENGINE_CAPACITY'].values
    cov = df['COVERAGE_TYPE'].values
    sa = df['SUM_ASSURED'].values
    comp = np.array([mt[r]['Comprehensive'][e] for r, e in zip(region, eng)])
    extra = np.array([pe[r] for r in region])
    units = np.ceil(np.maximum(0.0, (sa - 1000.0) / 1000.0))
    comp_basic = comp + extra * units
    tpo_basic = np.array([mt[r]['TPO'][e] for r, e in zip(region, eng)])
    basic = np.where(cov == 'Comprehensive', comp_basic,
                     np.where(cov == 'TPFT', np.round(0.75 * comp_basic + 1e-9, 2), tpo_basic))
    return np.round(basic, 2)


def generate_dataset(cfg, seed=None, n=None, cohort_year=None, polid_prefix='INIT'):
    """Generate a complete policy book from COHORT_CONFIG assumptions.

    Args:
        cfg: dict (COHORT_CONFIG) with all settings/assumptions
        seed: RNG seed (defaults to cfg['seed'])
        n: number of policies (defaults to cfg['n'])
        cohort_year: policy base year (defaults to cfg['cohort_year'])
        polid_prefix: 'INIT' for the initial book, 'ENT' for new entrants

    Returns:
        pd.DataFrame with all policy attributes + premium columns
    """
    n = int(n if n is not None else cfg['n'])
    rng = np.random.default_rng(int(seed if seed is not None else cfg['seed']))
    base_year = int(cohort_year if cohort_year is not None else cfg['cohort_year'])

    df = pd.DataFrame(index=range(n))

    # Coverage / vehicle / region
    df['COVERAGE_TYPE'] = rng.choice(
        list(cfg['coverage_pct']),
        size=n,
        p=_p(cfg['coverage_pct'].values())
    )
    df['VEHICLE_TYPE'] = rng.choice(
        list(cfg['vehicle_pct']),
        size=n,
        p=_p(cfg['vehicle_pct'].values())
    )
    df['REGION'] = rng.choice(
        list(cfg['region_pct']),
        size=n,
        p=_p(cfg['region_pct'].values())
    )

    # Sum assured: log-normal per vehicle type, rounded to RM 1,000
    sa = np.zeros(n)
    for vt, stats in cfg['sa_stats'].items():
        m = df['VEHICLE_TYPE'].values == vt
        sa[m] = rng.lognormal(
            mean=np.log(stats['lambda']),
            sigma=stats['spread'],
            size=int(m.sum())
        )
    df['SUM_ASSURED'] = np.round(sa / 1000) * 1000

    # Engine capacity: fixed hand-set mix (small cars dominant)
    df['ENGINE_CAPACITY'] = rng.choice(
        ENGINE_CAPACITY_BANDS,
        size=n,
        p=_p(cfg['engine_weights'])
    )

    # Driver profile: category by weights, age drawn from category band
    df['DRIVER_AGE_CAT'] = rng.choice(
        list(cfg['generation_pct']),
        size=n,
        p=_p(cfg['generation_pct'].values())
    )
    cats = df['DRIVER_AGE_CAT'].values
    lo = np.array([cfg['age_bands'][c][0] for c in cats])
    hi = np.array([cfg['age_bands'][c][1] for c in cats])
    df['DRIVER_AGE'] = rng.integers(lo, hi, size=n)
    df['DRIVER_GENDER'] = rng.choice(
        list(cfg['gender_pct']),
        size=n,
        p=_p(cfg['gender_pct'].values())
    )
    marital = np.empty(n, dtype=object)
    for cat, probs in cfg['marital_pct'].items():
        m = cats == cat
        marital[m] = rng.choice(
            list(probs),
            size=int(m.sum()),
            p=_p(probs.values())
        )
    df['MARITAL_STATUS'] = marital

    # Vehicle age at inception, capped 0-10
    car_age = np.zeros(n)
    for cat, med in cfg['car_age_median'].items():
        m = cats == cat
        car_age[m] = np.clip(
            np.round(med + rng.normal(0, cfg['car_age_sigma'], size=int(m.sum()))),
            0, 10
        )
    df['CAR_AGE'] = car_age.astype(int)

    # Region flood/theft risk flags
    for col in ('FLOOD_RISK', 'THEFT_RISK'):
        out = np.zeros(n, dtype=bool)
        for region, probs in cfg['risk_pct'].items():
            m = df['REGION'].values == region
            out[m] = rng.choice([True, False], size=int(m.sum()), p=_p(probs[col]))
        df[col] = out

    # NCD entry mix
    df['NCD_YEARS'] = rng.choice(
        cfg['ncd_entry']['years'],
        size=n,
        p=_p(cfg['ncd_entry']['weights'])
    )
    df['NCD_LEVEL'] = df['NCD_YEARS'].apply(lambda y: cfg['ncd_table'].get(int(min(y, 5)), 0.55))
    df['COHORT_YEAR'] = base_year

    # Telematics (teammate's feature spec): hard braking / speeding / night driving
    # -> composite telematics_score -> BEHAVIOR_RISK (drives claim frequency; mean exactly 1.10).
    # Rank-mapping (not min-max) keeps the score->risk link distortion-free: worst driver -> hi.
    tel = cfg.get('telemetry', {})
    age_z = (df['DRIVER_AGE'].values - df['DRIVER_AGE'].mean()) / df['DRIVER_AGE'].std()
    df['hard_braking_per_100km'] = np.clip(
        rng.gamma(tel.get('hb_shape', 2.0), tel.get('hb_scale', 1.8), size=n)
        + tel.get('hb_age', -0.15) * age_z, 0, tel.get('hb_max', 15))
    df['speeding_pct'] = np.clip(
        rng.gamma(tel.get('sp_shape', 2.0), tel.get('sp_scale', 6.0), size=n)
        + tel.get('sp_age', -1.0) * age_z, 0, tel.get('sp_max', 50))
    df['night_driving_pct'] = np.clip(
        rng.beta(tel.get('nd_a', 2), tel.get('nd_b', 5), size=n) * tel.get('nd_scale', 40)
        + tel.get('nd_age', -1.5) * age_z, 0, tel.get('nd_max', 50))

    def _mm(s):
        return (s - s.min()) / (s.max() - s.min())

    comp = (tel.get('w_hb', 0.45) * _mm(df['hard_braking_per_100km'])
            + tel.get('w_sp', 0.40) * _mm(df['speeding_pct'])
            + tel.get('w_nd', 0.15) * _mm(df['night_driving_pct']))
    df['telematics_score'] = np.clip(
        tel.get('score_hi', 100) - comp * (tel.get('score_hi', 100) - tel.get('score_lo', 20)),
        tel.get('score_lo', 20), tel.get('score_hi', 100))

    br = cfg.get('behavior_risk', {'lo': 0.90, 'hi': 1.30})
    _order = np.argsort(np.argsort(df['telematics_score'].values))
    _u = _order / max(int(n) - 1, 1)
    df['BEHAVIOR_RISK'] = br['hi'] - (br['hi'] - br['lo']) * _u

    # POLID: deterministic prefix-year-sequence (INIT/ENT)
    df['POLID'] = [f"{polid_prefix}{base_year}-{i + 1:06d}" for i in range(n)]

    # Premium-related: BASIC from tariff (needed for tariff pricing) + TOTAL_LOADING.
    # FINAL_PREMIUM_SST is NOT computed here - it is applied post-hoc by price_book,
    # keeping generation premium-independent.
    df['BASIC_PREMIUM'] = basic_premium_array(df, cfg)
    df['TOTAL_LOADING'] = total_loading_array(df, cfg)

    return df


# ============================================================================
# 5. RISK MODELS (claim frequency) - scalar reference for the vectorized engine
# ============================================================================

CLAIM_FREQUENCY_BASE = COHORT_CONFIG['claim_frequency_base']


def compute_claim_lambda(row):
    """Compute Poisson rate lambda via log-linear rating model."""
    log_lambda = CLAIM_FREQUENCY_BASE

    cat = row['DRIVER_AGE_CAT']
    if cat == 'Young Adults':
        log_lambda += 0.40        # young drivers: higher risk
    elif cat == 'Seniors':
        log_lambda += 0.26        # seniors: moderate increase

    # Young male interaction
    if cat == 'Young Adults' and row['DRIVER_GENDER'] == 'Male':
        log_lambda += 0.05

    # EV proxy (higher power/repair exposure)
    if row['VEHICLE_TYPE'] == 'EV':
        log_lambda += 0.05

    # Risk flags
    if row['FLOOD_RISK']:
        log_lambda += 0.20
    if row['THEFT_RISK']:
        log_lambda += 0.10

    # Behavioral risk (latent, telematics-sensed): mean 1.10 portfolio multiplier
    log_lambda += np.log(row['BEHAVIOR_RISK'])

    # Vehicle age: older cars carry higher breakdown/repair frequency
    log_lambda += 0.03 * row['CAR_AGE']

    # NCD safety credit: claim-free drivers are safer
    log_lambda -= 0.05 * row['NCD_YEARS']

    freq = np.exp(log_lambda)

    # Coverage multiplier: TPO no own-damage; TPFT fire/theft only (0.60)
    mult = 0.45 if row['COVERAGE_TYPE'] == 'TPO' else (0.60 if row['COVERAGE_TYPE'] == 'TPFT' else 1.00)
    return freq * mult


# ============================================================================
# 6. SIMULATION ENGINE (vectorized, premium-independent / labels only)
# ============================================================================

def age_band_array(ages):
    """Vectorized band upgrade: crossing 27/45/65 moves to the next rating band."""
    return np.select(
        [ages <= 27, ages <= 45, ages <= 65],
        ['Young Adults', 'Adults', 'Mature Adults'],
        default='Seniors')


def claim_lambda_array(df, cfg=COHORT_CONFIG):
    """Vectorized Poisson frequency (log-linear GLM), same model as compute_claim_lambda."""
    cat = df['DRIVER_AGE_CAT'].values
    log_l = np.full(len(df), cfg['claim_frequency_base'])
    log_l += 0.40 * (cat == 'Young Adults')
    log_l += 0.26 * (cat == 'Seniors')
    log_l += 0.05 * ((cat == 'Young Adults') & (df['DRIVER_GENDER'].values == 'Male'))
    log_l += 0.05 * (df['VEHICLE_TYPE'].values == 'EV')
    log_l += 0.20 * df['FLOOD_RISK'].values
    log_l += 0.10 * df['THEFT_RISK'].values
    log_l += np.log(df['BEHAVIOR_RISK'].values)
    log_l += 0.03 * df['CAR_AGE'].values
    log_l -= 0.05 * df['NCD_YEARS'].values
    cov = df['COVERAGE_TYPE'].values
    mult = np.where(cov == 'TPO', 0.45, np.where(cov == 'TPFT', 0.60, 1.00))
    return np.exp(log_l) * mult


def total_loading_array(df, cfg=COHORT_CONFIG):
    """Vectorized combined driver x vehicle loading."""
    dl_map = cfg.get('driver_age_loading', DRIVER_AGE_LOADING)
    dl = df['DRIVER_AGE_CAT'].map(dl_map).fillna(1.00).values
    cl = 1 + 0.03 * np.minimum(df['CAR_AGE'].values, 10)
    return dl * cl


def retention_prob_array(df):
    """Vectorized premium-independent retention (driver A)."""
    p = np.full(len(df), 0.82)
    p -= np.where(df['CLAIM_OCCURRED'].values, 0.25, -0.05)
    ncd = df['NCD_YEARS'].values
    p += np.select([ncd >= 3, ncd >= 2], [0.15, 0.08], default=0.0)
    ts = df['telematics_score'].values
    p += np.where(ts >= 80, 0.10 * (ts - 80) / 20.0,
                  np.where(ts >= 60, 0.03, 0.0))
    p -= 0.05 * (df['BEHAVIOR_RISK'].values - 1.0)
    return np.clip(p, 0.10, 0.95)


def ncd_level_array(yrs, cfg=COHORT_CONFIG):
    """Vectorized NCD discount lookup (table keyed 0-5; 6+ -> default 0.55)."""
    y = np.asarray(yrs, dtype=int)
    max_y = int(y.max()) if len(y) else 0
    lut = np.array([cfg['ncd_table'].get(min(i, 6), 0.55) for i in range(max_y + 1)])
    return lut[np.clip(y, 0, max_y)]


_PERIL_NAMES = ['AD', 'Windscreen', 'Theft', 'Fire', 'TPPD', 'TPBI']


def _draw_perils(cov, n, rng, cfg):
    """Vectorized peril draw from coverage-specific mixes (cumsum + uniform)."""
    peril_dist = cfg.get('peril_dist', PERIL_DIST)
    P = np.array([[peril_dist[c].get(p, 0.0) for p in _PERIL_NAMES] for c in cov])
    u = rng.random(n)[:, None]
    idx = np.minimum((u > np.cumsum(P, axis=1)).sum(axis=1), len(_PERIL_NAMES) - 1)
    return np.array(_PERIL_NAMES)[idx]


def _peril_params(perils, sa, cfg, ev_mult=None):
    """Vectorized Gamma shape/scale/cap per peril (caps vs sum assured).
    ev_mult: per-claim severity multiplier (e.g. EV factor) applied to
    SA-bound perils only (AD/Theft/Fire)."""
    peril_base = cfg.get('peril_base', PERIL_BASE)
    n = len(perils)
    if ev_mult is None:
        ev_mult = np.ones(n)
    shape = np.zeros(n)
    scale = np.zeros(n)
    cap = np.full(n, np.inf)
    for name in ('TPBI', 'TPPD', 'Windscreen'):
        m = perils == name
        if m.any():
            spec = peril_base[name]
            shape[m] = spec['shape']
            scale[m] = spec['scale']
            cap[m] = spec['cap']
    for name, s_lo, s_hi, s_f, sh in (('Theft', 8000, 20000, 0.20, 1.10),
                                      ('Fire', 7000, 18000, 0.15, 0.90),
                                      ('AD', 4500, 12000, 0.10, 0.60)):
        m = perils == name
        if m.any():
            shape[m] = sh
            scale[m] = np.clip(sa[m] * s_f, s_lo, s_hi) * ev_mult[m]
            cap[m] = sa[m]
    return shape, scale, cap


def simulate_claim_severity_vectorized(df, rng, cfg=COHORT_CONFIG):
    """Vectorized severity: explode by claim count -> peril -> Gamma -> cap -> aggregate."""
    n = len(df)
    amount = np.zeros(n)
    peril_out = np.empty(n, dtype=object)
    peril_out[:] = ''
    counts = df['CLAIM_COUNT'].values
    claim_mask = counts > 0
    if not claim_mask.any():
        return amount, peril_out
    idx = np.repeat(np.flatnonzero(claim_mask), counts[claim_mask])
    cov = df['COVERAGE_TYPE'].values[idx]
    sa = df['SUM_ASSURED'].values[idx]
    perils = _draw_perils(cov, len(idx), rng, cfg)
    ev_mult = np.where(
        df['VEHICLE_TYPE'].values[idx] == 'EV',
        cfg.get('ev_severity_factor', 1.0), 1.0)
    shape, scale, cap = _peril_params(perils, sa, cfg, ev_mult=ev_mult)
    amts = np.minimum(rng.gamma(shape, scale), cap)
    np.add.at(amount, idx, amts)
    s = pd.Series(perils).groupby(pd.Series(idx)).agg('/'.join)
    peril_out[np.flatnonzero(claim_mask)] = s.values
    return amount, peril_out


def _entrant_vehicle_pct(cfg, year):
    """Vehicle mix for entrants in `year`: base mix with EV share ramped by
    schedule; empty/missing schedule -> base mix unchanged (no custom EV share)."""
    base = dict(cfg['vehicle_pct'])
    sched = cfg.get('ev_share_by_year') or {}
    if not sched:
        return base
    ev = interp_schedule(sched, year)
    if ev >= 1.0:
        return {'EV': 1.0}
    others = [k for k in base if k != 'EV']
    rest = sum(base[k] for k in others)
    out = {k: (1 - ev) * base[k] / rest if rest > 0 else 0.0 for k in others}
    out['EV'] = ev
    return out


def _entrant_count(cfg, year_offset):
    """Dynamic entrant count: base * (1 + growth) ** year_offset (compounding)."""
    return max(0, int(round(cfg['entrant_base_count'] *
                            (1 + cfg['entrant_annual_growth']) ** year_offset)))


def simulate_cohort(df_initial, n_years=5, new_entrants_per_year=None,
                    seed=42, cfg=COHORT_CONFIG, verbose=True):
    """Simulate cohort evolution (vectorized hot path; per-seed local RNG).

    Args:
        df_initial: Starting cohort (Year 1)
        n_years: Number of years to simulate
        new_entrants_per_year: static entrants/year (None -> dynamic growth-based count)
        seed: Random seed for reproducibility (local Generator)
        cfg: config dict (default COHORT_CONFIG); threaded to helpers + entrants
        verbose: per-year + summary prints

    Returns:
        pd.DataFrame with all policy-year records
    """
    t0 = time.time()
    rng = np.random.default_rng(seed)
    history = []
    df_active = df_initial.copy()

    for year_offset in range(n_years):
        year = cfg['cohort_year'] + year_offset
        df_active['SIM_YEAR'] = year

        # Age in-force policies (brand-new entrants keep fresh ages).
        aging_mask = df_active['COHORT_YEAR'] < year
        if aging_mask.any():
            df_active.loc[aging_mask, 'DRIVER_AGE'] += 1
            df_active.loc[aging_mask, 'CAR_AGE'] = np.minimum(
                df_active.loc[aging_mask, 'CAR_AGE'] + 1, 10
            )
            # Band upgrades with age: crossing 27/45/65 moves to the next rating band
            df_active.loc[aging_mask, 'DRIVER_AGE_CAT'] = age_band_array(
                df_active.loc[aging_mask, 'DRIVER_AGE'].values
            )

        # Recompute frequency + loadings with current ages and NCD
        # (NCD_LEVEL here still reflects claims through the PRIOR year -> one-year lag)
        df_active['CLAIM_LAMBDA'] = claim_lambda_array(df_active, cfg)
        df_active['TOTAL_LOADING'] = total_loading_array(df_active, cfg)
        df_active['NCD_LEVEL_PRICED'] = df_active['NCD_LEVEL']

        # Simulate claims (Poisson frequency, vectorized)
        df_active['CLAIM_COUNT'] = rng.poisson(df_active['CLAIM_LAMBDA'].values)
        df_active['CLAIM_OCCURRED'] = df_active['CLAIM_COUNT'] > 0

        # Simulate severity (per-peril Gamma, vectorized, aggregated per policy-year)
        amounts, perils = simulate_claim_severity_vectorized(df_active, rng, cfg)
        df_active['CLAIM_AMOUNT'] = amounts
        df_active['CLAIM_PERIL'] = perils

        # Retention is premium-independent (driver A: experience + telematics)

        # Retention + renewals (vectorized)
        df_active['RENEWAL_PROB'] = retention_prob_array(df_active)
        df_active['RENEWED'] = rng.random(len(df_active)) < df_active['RENEWAL_PROB'].values

        # Update NCD based on claims
        df_active.loc[~df_active['CLAIM_OCCURRED'], 'NCD_YEARS'] += 1
        df_active.loc[df_active['CLAIM_OCCURRED'], 'NCD_YEARS'] = 0
        df_active['NCD_LEVEL'] = ncd_level_array(df_active['NCD_YEARS'].values, cfg)

        # Record full year state (including lapsers) for retention analysis
        cols_to_keep = ['POLID', 'COVERAGE_TYPE', 'SUM_ASSURED', 'REGION',
                        'VEHICLE_TYPE', 'DRIVER_AGE_CAT', 'DRIVER_AGE',
                        'CAR_AGE', 'DRIVER_GENDER', 'FLOOD_RISK', 'THEFT_RISK',
                        'BASIC_PREMIUM', 'TOTAL_LOADING',
                        'NCD_LEVEL_PRICED', 'NCD_LEVEL',
                        'NCD_YEARS', 'CLAIM_LAMBDA',
                        'SIM_YEAR', 'CLAIM_COUNT', 'CLAIM_OCCURRED', 'CLAIM_AMOUNT',
                        'CLAIM_PERIL',
                        'RENEWAL_PROB', 'RENEWED', 'COHORT_YEAR',
                        'BEHAVIOR_RISK', 'telematics_score']
        history.append(df_active[cols_to_keep].copy())

        if verbose:
            print(f"Year {year}: {len(df_active)} active policies, "
                  f"claims: {df_active['CLAIM_COUNT'].sum()}, "
                  f"freq: {df_active['CLAIM_OCCURRED'].mean():.1%}, "
                  f"avg NCD priced: {df_active['NCD_LEVEL_PRICED'].mean():.2%}, "
                  f"retention: {df_active['RENEWED'].mean():.1%}")

        # New entrants: dynamic profile (EV share ramps by year) + dynamic count
        # (base * (1 + growth)**year_offset) unless a static override is passed.
        if year_offset < n_years - 1:
            n_ent = (new_entrants_per_year if new_entrants_per_year is not None
                     else _entrant_count(cfg, year_offset))
            if n_ent > 0:
                ecfg = copy.deepcopy(cfg)
                for k, v in cfg.get('entrant_profile', {}).items():
                    ecfg[k] = v
                ecfg['vehicle_pct'] = _entrant_vehicle_pct(cfg, year + 1)
                new_cohort = generate_dataset(
                    ecfg, seed=seed + year_offset,
                    n=n_ent, cohort_year=year + 1,
                    polid_prefix='ENT'
                )
                if cfg.get('entrant_ncd_zero', False):
                    new_cohort['NCD_YEARS'] = 0
                    new_cohort['NCD_LEVEL'] = cfg['ncd_table'].get(0, 0.55)
                df_active = pd.concat(
                    [df_active[df_active['RENEWED']], new_cohort],
                    ignore_index=True
                )
            else:
                df_active = df_active[df_active['RENEWED']].copy()
        else:
            df_active = df_active[df_active['RENEWED']].copy()

    cohort_results = pd.concat(history, ignore_index=True)
    if verbose:
        print(f"\nSimulation complete. Total records: {len(cohort_results)}")
        print(f"Year range: {cohort_results['SIM_YEAR'].min()} - {cohort_results['SIM_YEAR'].max()}")
        print(f"Simulation wall time: {time.time() - t0:.1f}s")
    return cohort_results


# ============================================================================
# MONTE CARLO - scenario x seed x pricing-model grid (uncertainty around baseline)
# ============================================================================

def summarize(results_df):
    """One trajectory -> scalar metrics + per-year loss-ratio series."""
    premium = results_df['FINAL_PREMIUM_SST'].sum()
    claims = results_df['CLAIM_AMOUNT'].sum()
    metrics = {
        'overall_lr': claims / premium if premium > 0 else np.nan,
        'claim_freq': results_df['CLAIM_OCCURRED'].mean(),
        'avg_premium': results_df['FINAL_PREMIUM_SST'].mean(),
        'retention': results_df['RENEWED'].mean(),
        'n_policy_years': len(results_df),
    }

    def _yr_lr(g):
        p = g['FINAL_PREMIUM_SST'].sum()
        return g['CLAIM_AMOUNT'].sum() / p if p > 0 else np.nan

    yearly = results_df.groupby('SIM_YEAR').apply(_yr_lr)
    return metrics, yearly


def _run_one(cfg, seed, n_years, new_entrants_per_year, pricing_model='tariff',
             book_seed=COHORT_CONFIG['seed']):
    df0 = generate_dataset(cfg, seed=book_seed)
    res = simulate_cohort(df0, n_years=n_years,
                          new_entrants_per_year=new_entrants_per_year,
                          seed=seed, cfg=cfg, verbose=False)
    res = price_book(res, pricing_model, cfg)
    return summarize(res)


def run_monte_carlo(overrides=None, seeds=(42,), n_years=20,
                    new_entrants_per_year=None, n_jobs=4, book_seed=None,
                    pricing_models=('tariff',)):
    """Run a (scenario x seed) Monte Carlo grid.

    Args:
        overrides: None | dict | list[dict] - assumption patches on COHORT_CONFIG
        seeds: int | list[int] - independent replications per scenario
        n_years: simulation horizon
        new_entrants_per_year: static entrants/year override (None -> dynamic growth-based)
        n_jobs: parallel workers (threading backend; numpy releases the GIL)
        pricing_models: pricing models evaluated per (scenario, seed)
        book_seed: initial-cohort RNG seed (default COHORT_CONFIG['seed']). The MC
                   seed perturbs only the forward path; the starting book is fixed.

    Returns:
        (metrics_df, summary_df, yearly_lr_df)
    """
    if book_seed is None:
        book_seed = COHORT_CONFIG['seed']
    if overrides is None:
        overrides = [None]
    elif isinstance(overrides, dict):
        overrides = [overrides]
    if isinstance(seeds, int):
        seeds = [seeds]
    if isinstance(pricing_models, str):
        pricing_models = (pricing_models,)

    tasks = [(i, ov, s, pm) for i, ov in enumerate(overrides)
             for s in seeds for pm in pricing_models]

    def work(t):
        i, ov, s, pm = t
        cfg = deep_update(COHORT_CONFIG, ov)
        metrics, yearly = _run_one(cfg, s, n_years, new_entrants_per_year, pm, book_seed)
        return i, ov, s, pm, metrics, yearly

    if _HAS_JOBLIB and n_jobs != 1 and len(tasks) > 1:
        out = Parallel(n_jobs=n_jobs, backend='threading')(delayed(work)(t) for t in tasks)
    else:
        out = [work(t) for t in tasks]

    rows, yearly_rows = [], []
    for i, ov, s, pm, metrics, yearly in out:
        rows.append({'scenario': i, 'pricing_model': pm,
                     'overrides': repr(ov) if ov else 'base',
                     'seed': s, **metrics})
        for year, lr in yearly.items():
            yearly_rows.append({'scenario': i, 'pricing_model': pm, 'seed': s,
                                'SIM_YEAR': int(year), 'loss_ratio': lr})
    metrics_df = pd.DataFrame(rows)
    yearly_df = pd.DataFrame(yearly_rows)

    summ = []
    for i in range(len(overrides)):
        for pm in pricing_models:
            g = metrics_df[(metrics_df['scenario'] == i) & (metrics_df['pricing_model'] == pm)]
            if len(g) == 0:
                continue
            summ.append({
                'scenario': i, 'pricing_model': pm, 'overrides': g['overrides'].iloc[0],
                'n_seeds': len(g),
                'lr_mean': g['overall_lr'].mean(), 'lr_std': g['overall_lr'].std(),
                'lr_p05': g['overall_lr'].quantile(0.05),
                'lr_p50': g['overall_lr'].median(),
                'lr_p95': g['overall_lr'].quantile(0.95),
                'freq_mean': g['claim_freq'].mean(),
                'premium_mean': g['avg_premium'].mean(),
                'retention_mean': g['retention'].mean(),
            })
    summary_df = pd.DataFrame(summ)
    return metrics_df, summary_df, yearly_df


# ============================================================================
# 7. PRICING MODELS (Tariff | GLM | GLM+Telematics) - all pricing together
#    Price is placed post-simulation; simulate_cohort is premium-independent.
# ============================================================================

# --- ML feature specification -------------------------------------------------

_PRICE_FEATURES_GLM = ['DRIVER_AGE', 'CAR_AGE', 'NCD_LEVEL', 'VEHICLE_TYPE',
                       'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION']

_PRICE_FEATURES_TELEM = _PRICE_FEATURES_GLM + ['telematics_score']


def _pricing_features(method):
    if method == 'glm':
        return list(_PRICE_FEATURES_GLM)
    if method == 'telem':
        return list(_PRICE_FEATURES_TELEM)
    raise ValueError('unknown pricing method: ' + str(method))


def _encode_features(df, features):
    _CAT = ['VEHICLE_TYPE', 'COVERAGE_TYPE', 'REGION']
    X = df[features].copy()
    for col in _CAT:
        if col in features:
            X[col] = X[col].astype('category').cat.codes
    return X


def _require_simulated(book):
    """Fail fast if the book was not produced by simulate_cohort().
    Training/pricing must always run on a simulated book, never on raw inputs."""
    required = ['SIM_YEAR', 'COHORT_YEAR', 'POLID', 'CLAIM_COUNT', 'CLAIM_AMOUNT']
    missing = [c for c in required if c not in book.columns]
    if missing:
        raise ValueError(
            'train_pricing/price_book requires a SIMULATED book, but these columns '
            f'are missing: {missing}. Run simulate_cohort() before pricing.')
    if book['CLAIM_COUNT'].isnull().any() or book['CLAIM_AMOUNT'].isnull().any():
        raise ValueError('book has null claim fields - run simulate_cohort() first.')


# --- Cached model training (avoid re-simulating the 5-yr training book) --------

_TRAIN_BOOK_CACHE = {}   # (train_seed, cfg_key) -> training book
_PRICER_CACHE = {}       # (method, train_seed, cfg_key) -> {features, model, avg_sev_by_cov}


def _cfg_key(cfg):
    """Stable fingerprint of the data-generating config (excludes premium-only levers)."""
    c = {k: v for k, v in cfg.items() if k not in ('expense_loading', 'telemetric_load')}
    return json.dumps(c, sort_keys=True, default=str)


def _fit_frequency(tr, features):
    return PoissonRegressor(alpha=1e-3, max_iter=1000).fit(
        _encode_features(tr, features), tr['CLAIM_COUNT'])


def _avg_sev_by_cov(book):
    return book.groupby('COVERAGE_TYPE').apply(
        lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum(),
        include_groups=False).to_dict()


def train_pricing(book, method='tariff', cfg=COHORT_CONFIG, train_seed=None):
    """Fit a GLM/telem frequency model. With train_seed, the 5-yr training book is
    simulated once and cached (shared across glm/telem and repeated price_book calls);
    expense_loading/telemetric_load are applied at pricing time, not baked into the model."""
    _require_simulated(book)
    features = _pricing_features(method)

    if train_seed is not None:
        key = (method, train_seed, _cfg_key(cfg))
        if key not in _PRICER_CACHE:
            tkey = (train_seed, _cfg_key(cfg))
            if tkey not in _TRAIN_BOOK_CACHE:
                _TRAIN_BOOK_CACHE[tkey] = simulate_cohort(
                    generate_dataset(cfg, seed=train_seed),
                    n_years=5, new_entrants_per_year=(0.5 * cfg['n']),
                    seed=train_seed, cfg=cfg, verbose=False)
            _tr_book = _TRAIN_BOOK_CACHE[tkey]
            tr_src = _tr_book[_tr_book['COHORT_YEAR'] == _tr_book['SIM_YEAR']]
            pids = tr_src['POLID'].unique()
            train_pids = set(np.random.default_rng(7).choice(
                pids, int(len(pids) * 0.6), replace=False))
            tr = tr_src[tr_src['POLID'].isin(train_pids)]
            _PRICER_CACHE[key] = {
                'features': features,
                'model': _fit_frequency(tr, features),
                'avg_sev_by_cov': _avg_sev_by_cov(_tr_book),
            }
        trained = _PRICER_CACHE[key]
    else:
        tr_src = book[book['COHORT_YEAR'] == book['SIM_YEAR']]
        pids = tr_src['POLID'].unique()
        train_pids = set(np.random.default_rng(7).choice(
            pids, int(len(pids) * 0.6), replace=False))
        tr = tr_src[tr_src['POLID'].isin(train_pids)]
        trained = {
            'features': features,
            'model': _fit_frequency(tr, features),
            'avg_sev_by_cov': _avg_sev_by_cov(book),
        }

    return {**trained,
            'expense_loading': cfg.get('expense_loading', 1.40),
            'telemetric_load': cfg.get('telemetric_load', 1.0)}


# --- The three pricing models + registry ---------------------------------------

def _price_tariff(book, cfg, train_seed=None):
    """TARIFF pricing model: FINAL = BASIC x loading x (1-NCD) x 1.1^risk x (1+SST).
    Non-lagged NCD (current NCD_LEVEL); initial cohort follows the ncd_table tiers."""
    out = book.copy()
    loading = total_loading_array(out, cfg)
    ncd = 1 - out['NCD_LEVEL'].values
    risk = 1.1 ** (out['FLOOD_RISK'].values.astype(int) + out['THEFT_RISK'].values.astype(int))
    out['FINAL_PREMIUM_SST'] = (out['BASIC_PREMIUM'].values * loading * ncd * risk * (1 + SST_RATE)).round(2)
    return out


def _price_ml(book, method, cfg, train_seed=None):
    out = book.copy()
    pricer = train_pricing(book, method, cfg, train_seed=train_seed)
    X = _encode_features(out, pricer['features'])
    pf = pricer['model'].predict(X)
    sev = out['COVERAGE_TYPE'].map(pricer['avg_sev_by_cov']).astype(float).values
    prem = (pf * sev * pricer['expense_loading'] * pricer['telemetric_load'])
    prem = prem * (1.1 ** out['FLOOD_RISK'].values.astype(int))
    prem = prem * (1.1 ** out['THEFT_RISK'].values.astype(int))
    out['FINAL_PREMIUM_SST'] = prem.round(2)
    return out


PRICING_MODELS = {
    'tariff': lambda book, cfg=COHORT_CONFIG, train_seed=None: _price_tariff(book, cfg, train_seed),
    'glm':    lambda book, cfg=COHORT_CONFIG, train_seed=None: _price_ml(book, 'glm', cfg, train_seed),
    'telem':  lambda book, cfg=COHORT_CONFIG, train_seed=None: _price_ml(book, 'telem', cfg, train_seed),
}


def price_book(book, method='tariff', cfg=COHORT_CONFIG, train_seed=None):
    """Return a copy of `book` with FINAL_PREMIUM_SST computed by `method` (one of the
    PRICING_MODELS: tariff | glm | glm+telematics)."""
    pricer = PRICING_MODELS.get(method)
    if pricer is None:
        raise ValueError('unknown pricing method: ' + str(method))
    return pricer(book, cfg, train_seed)


def price_parallel(book, methods=('tariff', 'glm', 'telem'), cfg=COHORT_CONFIG,
                   train_seed=None, n_jobs=3):
    """Price `book` under several models, parallelised with a thread backend
    (numpy releases the GIL; threads share memory). Returns {method: priced_book}."""
    def _one(m):
        return m, price_book(book, m, cfg, train_seed=train_seed)
    if _HAS_JOBLIB and n_jobs != 1 and len(methods) > 1:
        return dict(Parallel(n_jobs=n_jobs, backend='threading')(
            delayed(_one)(m) for m in methods))
    return dict(_one(m) for m in methods)


def _retained_lr(res, decline_pct=0.15):
    p = res.groupby('POLID').agg(claims=('CLAIM_AMOUNT', 'sum'),
                                 prem=('FINAL_PREMIUM_SST', 'sum')).reset_index()
    k = int(np.floor(len(p) * decline_pct))
    p = p.sort_values('prem', ascending=False).iloc[k:]
    return p['claims'].sum() / p['prem'].sum() * 100


def _tier_spread(res):
    d = res.copy()
    d['_bin'] = pd.cut(d['telematics_score'], bins=[0, 50, 70, 85, 100],
                       labels=['<50', '50-70', '70-85', '85-100'])
    g = d.groupby('_bin', observed=False).apply(
        lambda x: x['CLAIM_AMOUNT'].sum() / x['FINAL_PREMIUM_SST'].sum() * 100)
    return g.max() - g.min()


def compare_pricing(book, methods=('tariff', 'glm', 'telem'), cfg=COHORT_CONFIG, train_seed=None):
    rows = []
    for m in methods:
        b = price_book(book, m, cfg, train_seed=train_seed)
        rows.append({
            'model': m,
            'overall_LR(%)': round(b['CLAIM_AMOUNT'].sum() / b['FINAL_PREMIUM_SST'].sum() * 100, 2),
            'retained_LR(%)': round(_retained_lr(b, 0.15), 2),
            'prem_count_rho': round(spearmanr(b['FINAL_PREMIUM_SST'], b['CLAIM_COUNT']).correlation, 4),
            'tier_spread(pp)': round(_tier_spread(b), 1),
            'avg_premium': round(b['FINAL_PREMIUM_SST'].mean(), 2),
        })
    return pd.DataFrame(rows)
