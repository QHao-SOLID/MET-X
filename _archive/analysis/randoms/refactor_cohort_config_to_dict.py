import json

nb = json.load(open('main.ipynb', encoding='utf-8'))

NEW_050 = '''# ============================================================================
# INITIAL COHORT GENERATION - single function, all assumptions in COHORT_CONFIG
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
    'n': 100000,
    'coverage_pct': {'Comprehensive': 0.65, 'TPFT': 0.20, 'TPO': 0.15},
    'vehicle_pct': {'ICE': 0.90, 'EV': 0.10},
    'sa_stats': {'ICE': {'lambda': 50000, 'spread': 0.5},
                 'EV': {'lambda': 80000, 'spread': 0.5}},
    'region_pct': {'Peninsular Malaysia': 0.80,
                   'East Malaysia (Sabah, Sawarak & Labuan)': 0.20},
    'generation_pct': {'Young Adults': 0.40, 'Adults': 0.40,
                       'Mature Adults': 0.15, 'Seniors': 0.05},
    'age_bands': {'Young Adults': (18, 28), 'Adults': (28, 46),
                  'Mature Adults': (46, 66), 'Seniors': (66, 76)},
    'gender_pct': {'Male': 0.55, 'Female': 0.45},
    'marital_pct': {'Young Adults': {'Single': 0.85, 'Married': 0.15},
                    'Adults': {'Single': 0.50, 'Married': 0.50},
                    'Mature Adults': {'Single': 0.20, 'Married': 0.80},
                    'Seniors': {'Single': 0.20, 'Married': 0.80}},
    'car_age_median': {'Young Adults': 2.0, 'Adults': 3.5,
                       'Mature Adults': 5.0, 'Seniors': 5.5},
    'car_age_sigma': 1.5,
    'risk_pct': {'Peninsular Malaysia': {'FLOOD_RISK': [0.60, 0.40],
                                         'THEFT_RISK': [0.40, 0.60]},
                 'East Malaysia (Sabah, Sawarak & Labuan)': {'FLOOD_RISK': [0.00, 1.00],
                                                             'THEFT_RISK': [0.15, 0.85]}},
    'ncd_table': {0: 0.00, 1: 0.25, 2: 0.30, 3: 0.3833, 4: 0.45, 5: 0.55},
    'ncd_entry_years': [0, 1, 2, 3, 4, 5],
    'ncd_entry_weights': [0.30, 0.22, 0.16, 0.13, 0.10, 0.09],
    'cohort_year': 2026,
    'engine_weights': [0.25, 0.20, 0.18, 0.15, 0.10, 0.07, 0.03, 0.02],
    'seed': 42,
}


def age_band(age):
    """Map an exact driver age to its rating band (band upgrades with age)."""
    if age <= 27:
        return 'Young Adults'
    if age <= 45:
        return 'Adults'
    if age <= 65:
        return 'Mature Adults'
    return 'Seniors'


def _p(weights):
    """Normalise weights to sum exactly to 1 (float-safe for np.random.choice)."""
    a = np.array(list(weights), dtype=float)
    return a / a.sum()


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
    df['COVERAGE_TYPE'] = rng.choice(list(cfg['coverage_pct']), size=n, p=_p(cfg['coverage_pct'].values()))
    df['VEHICLE_TYPE'] = rng.choice(list(cfg['vehicle_pct']), size=n, p=_p(cfg['vehicle_pct'].values()))
    df['REGION'] = rng.choice(list(cfg['region_pct']), size=n, p=_p(cfg['region_pct'].values()))

    # Sum assured: log-normal per vehicle type, rounded to RM 1,000
    sa = np.zeros(n)
    for vt, stats in cfg['sa_stats'].items():
        m = df['VEHICLE_TYPE'].values == vt
        sa[m] = rng.lognormal(mean=np.log(stats['lambda']), sigma=stats['spread'],
                              size=int(m.sum()))
    df['SUM_ASSURED'] = np.round(sa / 1000) * 1000

    # Engine capacity: fixed hand-set mix (small cars dominant)
    df['ENGINE_CAPACITY'] = rng.choice(ENGINE_CAPACITY_BANDS, size=n,
                                       p=_p(cfg['engine_weights']))

    # Driver profile: category by weights, age drawn from category band
    df['DRIVER_AGE_CAT'] = rng.choice(list(cfg['generation_pct']), size=n,
                                      p=_p(cfg['generation_pct'].values()))
    cats = df['DRIVER_AGE_CAT'].values
    lo = np.array([cfg['age_bands'][c][0] for c in cats])
    hi = np.array([cfg['age_bands'][c][1] for c in cats])
    df['DRIVER_AGE'] = rng.integers(lo, hi, size=n)
    df['DRIVER_GENDER'] = rng.choice(list(cfg['gender_pct']), size=n,
                                     p=_p(cfg['gender_pct'].values()))
    marital = np.empty(n, dtype=object)
    for cat, probs in cfg['marital_pct'].items():
        m = cats == cat
        marital[m] = rng.choice(list(probs), size=int(m.sum()), p=_p(probs.values()))
    df['MARITAL_STATUS'] = marital

    # Vehicle age at inception, capped 0-10
    car_age = np.zeros(n)
    for cat, med in cfg['car_age_median'].items():
        m = cats == cat
        car_age[m] = np.clip(np.round(med + rng.normal(0, cfg['car_age_sigma'],
                                                       size=int(m.sum()))), 0, 10)
    df['CAR_AGE'] = car_age.astype(int)

    # Region flood/theft risk flags
    for col in ('FLOOD_RISK', 'THEFT_RISK'):
        out = np.zeros(n, dtype=bool)
        for region, probs in cfg['risk_pct'].items():
            m = df['REGION'].values == region
            out[m] = rng.choice([True, False], size=int(m.sum()), p=_p(probs[col]))
        df[col] = out

    # NCD entry mix
    df['NCD_YEARS'] = rng.choice(cfg['ncd_entry_years'], size=n, p=_p(cfg['ncd_entry_weights']))
    df['NCD_LEVEL'] = df['NCD_YEARS'].apply(lambda y: cfg['ncd_table'].get(int(min(y, 5)), 0.55))
    df['COHORT_YEAR'] = base_year

    # POLID: deterministic prefix-year-sequence (INIT/ENT)
    df['POLID'] = [f"{polid_prefix}{base_year}-{i + 1:06d}" for i in range(n)]

    # Premium: BASIC from tariff, TOTAL_LOADING, FINAL with SST
    df['BASIC_PREMIUM'] = df.apply(calculate_premium, axis=1)
    df['TOTAL_LOADING'] = df.apply(
        lambda r: total_loading(r['DRIVER_AGE_CAT'], r['CAR_AGE']), axis=1
    )
    df['FINAL_PREMIUM_SST'] = df.apply(compute_final_premium, axis=1)

    # Apply the canonical schema dtypes
    for col, dt in dtype_dict.items():
        if col in df.columns:
            df[col] = df[col].astype(dt)
    return df
'''

NEW_NCD = '''# NCD setup - exact PIAM table progression (single source: COHORT_CONFIG)
COHORT_YEAR = COHORT_CONFIG['cohort_year']
NCD_TABLE = COHORT_CONFIG['ncd_table']
NCD_ENTRY_YEARS = COHORT_CONFIG['ncd_entry_years']
NCD_ENTRY_WEIGHTS = COHORT_CONFIG['ncd_entry_weights']

print('NCD setup ready (from COHORT_CONFIG). Entry NCD mix:')
print(pd.Series(NCD_ENTRY_WEIGHTS, index=NCD_ENTRY_YEARS)
      .map(lambda x: f'{x:.1%}').to_string())
'''


def set_cell(cid, source):
    for c in nb['cells']:
        if c['id'] == cid:
            assert ''.join(c['source']) != source, f'{cid}: already new'
            c['source'] = source.splitlines(keepends=True)
            c['outputs'] = []
            c['execution_count'] = None
            print(f'replaced {cid}')
            return
    raise KeyError(cid)


set_cell('050b235c', NEW_050)
set_cell('ncd-setup', NEW_NCD)


def rep(cid, old, new, expect=1):
    for c in nb['cells']:
        if c['id'] == cid:
            s = ''.join(c['source'])
            n = s.count(old)
            assert n == expect, f"{cid}: found {n} of {old[:60]!r}"
            c['source'] = s.replace(old, new).splitlines(keepends=True)
            c['outputs'] = []
            c['execution_count'] = None
            print(f'ok {cid}: {n}x {old[:50]!r}')
            return
    raise KeyError(cid)


rep('cohort-generation', 'seed=COHORT_CONFIG.seed', "seed=COHORT_CONFIG['seed']")
rep('cohort-generation', 'year {COHORT_CONFIG.cohort_year}', "year {COHORT_CONFIG['cohort_year']}")

# drop now-unused dataclass import if no other usage remains
for c in nb['cells']:
    s = ''.join(c['source'])
    if 'dataclass' in s and c['id'] != '3800d4d9':
        print('dataclass still used in', c['id'])

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Saved')