import json

nb = json.load(open('main.ipynb', encoding='utf-8'))


def get(cid):
    for c in nb['cells']:
        if c['id'] == cid:
            return c
    raise KeyError(cid)


def rep(cid, old, new, expect=1):
    c = get(cid)
    s = ''.join(c['source'])
    n = s.count(old)
    assert n == expect, f"{cid}: found {n} of {old[:70]!r}, expected {expect}"
    c['source'] = s.replace(old, new).splitlines(keepends=True)
    c['outputs'] = []
    c['execution_count'] = None
    print(f'ok {cid}: {n}x {old[:55]!r}')


def set_source(cid, src):
    c = get(cid)
    c['source'] = src.splitlines(keepends=True)
    c['outputs'] = []
    c['execution_count'] = None
    print(f'ok {cid}: full rewrite ({len(src)} chars)')


def insert_after(cid, new_id, src):
    idx = next(i for i, c in enumerate(nb['cells']) if c['id'] == cid)
    nb['cells'].insert(idx + 1, {
        'cell_type': 'code', 'execution_count': None, 'id': new_id,
        'metadata': {}, 'outputs': [], 'source': src.splitlines(keepends=True)
    })
    print(f'ok insert {new_id} after {cid}')


# 1. Imports: drop uuid/random, add dataclass
rep('3800d4d9',
    'import numpy as np\nimport pandas as pd\nimport uuid\nimport random',
    'import numpy as np\nimport pandas as pd\nfrom dataclasses import dataclass, field')

# 2. Blueprint cell -> CohortConfig + generate_dataset (vectorized, no extra helpers)
set_source('050b235c', r'''# ============================================================================
# INITIAL COHORT GENERATION - single function, all assumptions in CohortConfig
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


@dataclass
class CohortConfig:
    """All settings/assumptions for initial cohort generation."""

    n: int = 100000
    coverage_pct: dict = field(default_factory=lambda: {
        'Comprehensive': 0.65, 'TPFT': 0.20, 'TPO': 0.15})
    vehicle_pct: dict = field(default_factory=lambda: {'ICE': 0.90, 'EV': 0.10})
    sa_stats: dict = field(default_factory=lambda: {
        'ICE': {'lambda': 50000, 'spread': 0.5},
        'EV': {'lambda': 80000, 'spread': 0.5}})
    region_pct: dict = field(default_factory=lambda: {
        'Peninsular Malaysia': 0.80,
        'East Malaysia (Sabah, Sawarak & Labuan)': 0.20})
    generation_pct: dict = field(default_factory=lambda: {
        'Gen-Z': 0.40, 'Millennial': 0.40, 'Boomers': 0.15, 'Senior': 0.05})
    age_bands: dict = field(default_factory=lambda: {
        'Gen-Z': (18, 28), 'Millennial': (28, 46),
        'Boomers': (46, 66), 'Senior': (66, 76)})
    gender_pct: dict = field(default_factory=lambda: {'Male': 0.55, 'Female': 0.45})
    marital_pct: dict = field(default_factory=lambda: {
        'Gen-Z': {'Single': 0.85, 'Married': 0.15},
        'Millennial': {'Single': 0.50, 'Married': 0.50},
        'Boomers': {'Single': 0.20, 'Married': 0.80},
        'Senior': {'Single': 0.20, 'Married': 0.80}})
    car_age_median: dict = field(default_factory=lambda: {
        'Gen-Z': 2.0, 'Millennial': 3.5, 'Boomers': 5.0, 'Senior': 5.5})
    car_age_sigma: float = 1.5
    risk_pct: dict = field(default_factory=lambda: {
        'Peninsular Malaysia': {
            'FLOOD_RISK': [0.60, 0.40], 'THEFT_RISK': [0.40, 0.60]},
        'East Malaysia (Sabah, Sawarak & Labuan)': {
            'FLOOD_RISK': [0.00, 1.00], 'THEFT_RISK': [0.15, 0.85]}})
    ncd_table: dict = field(default_factory=lambda: {
        0: 0.00, 1: 0.25, 2: 0.30, 3: 0.3833, 4: 0.45, 5: 0.55})
    ncd_entry_years: list = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    ncd_entry_weights: list = field(default_factory=lambda: [0.30, 0.22, 0.16, 0.13, 0.10, 0.09])
    cohort_year: int = 2026
    engine_exp_lambda: float = 1.0
    engine_seed: int = 42
    seed: int = 42


def _p(weights):
    """Normalise weights to sum exactly to 1 (float-safe for np.random.choice)."""
    a = np.array(list(weights), dtype=float)
    return a / a.sum()


def generate_dataset(cfg, seed=None, n=None, cohort_year=None, polid_prefix='INIT'):
    """Generate a complete policy book from CohortConfig assumptions.

    Args:
        cfg: CohortConfig with all settings/assumptions
        seed: RNG seed (defaults to cfg.seed)
        n: number of policies (defaults to cfg.n)
        cohort_year: policy base year (defaults to cfg.cohort_year)
        polid_prefix: 'INIT' for the initial book, 'ENT' for new entrants

    Returns:
        pd.DataFrame with all policy attributes + premium columns
    """
    n = int(n if n is not None else cfg.n)
    rng = np.random.default_rng(int(seed if seed is not None else cfg.seed))
    base_year = int(cohort_year if cohort_year is not None else cfg.cohort_year)

    df = pd.DataFrame(index=range(n))

    # Coverage / vehicle / region
    df['COVERAGE_TYPE'] = rng.choice(list(cfg.coverage_pct), size=n, p=_p(cfg.coverage_pct.values()))
    df['VEHICLE_TYPE'] = rng.choice(list(cfg.vehicle_pct), size=n, p=_p(cfg.vehicle_pct.values()))
    df['REGION'] = rng.choice(list(cfg.region_pct), size=n, p=_p(cfg.region_pct.values()))

    # Sum assured: log-normal per vehicle type, rounded to RM 1,000
    sa = np.zeros(n)
    for vt, stats in cfg.sa_stats.items():
        m = df['VEHICLE_TYPE'].values == vt
        sa[m] = rng.lognormal(mean=np.log(stats['lambda']), sigma=stats['spread'],
                              size=int(m.sum()))
    df['SUM_ASSURED'] = np.round(sa / 1000) * 1000

    # Engine capacity: fixed exponential-weighted mix (own rng, as before)
    ew_rng = np.random.default_rng(cfg.engine_seed)
    exp_vals = np.sort(ew_rng.exponential(1 / cfg.engine_exp_lambda, len(ENGINE_CAPACITY_BANDS)))[::-1]
    df['ENGINE_CAPACITY'] = rng.choice(ENGINE_CAPACITY_BANDS, size=n,
                                       p=exp_vals / exp_vals.sum())

    # Driver profile: category by weights, age drawn from category band
    df['DRIVER_AGE_CAT'] = rng.choice(list(cfg.generation_pct), size=n,
                                      p=_p(cfg.generation_pct.values()))
    cats = df['DRIVER_AGE_CAT'].values
    lo = np.array([cfg.age_bands[c][0] for c in cats])
    hi = np.array([cfg.age_bands[c][1] for c in cats])
    df['DRIVER_AGE'] = rng.integers(lo, hi, size=n)
    df['DRIVER_GENDER'] = rng.choice(list(cfg.gender_pct), size=n,
                                     p=_p(cfg.gender_pct.values()))
    marital = np.empty(n, dtype=object)
    for cat, probs in cfg.marital_pct.items():
        m = cats == cat
        marital[m] = rng.choice(list(probs), size=int(m.sum()), p=_p(probs.values()))
    df['MARITAL_STATUS'] = marital

    # Vehicle age at inception, capped 0-10
    car_age = np.zeros(n)
    for cat, med in cfg.car_age_median.items():
        m = cats == cat
        car_age[m] = np.clip(np.round(med + rng.normal(0, cfg.car_age_sigma,
                                                       size=int(m.sum()))), 0, 10)
    df['CAR_AGE'] = car_age.astype(int)

    # Region flood/theft risk flags
    for col in ('FLOOD_RISK', 'THEFT_RISK'):
        out = np.zeros(n, dtype=bool)
        for region, probs in cfg.risk_pct.items():
            m = df['REGION'].values == region
            out[m] = rng.choice([True, False], size=int(m.sum()), p=_p(probs[col]))
        df[col] = out

    # NCD entry mix
    df['NCD_YEARS'] = rng.choice(cfg.ncd_entry_years, size=n, p=_p(cfg.ncd_entry_weights))
    df['NCD_LEVEL'] = df['NCD_YEARS'].apply(lambda y: cfg.ncd_table.get(int(min(y, 5)), 0.55))
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
    return df''')

# 3. Schema cell: keep features/dtype_dict/num_dataset, drop empty-df creation
rep('ed52012d',
    '''num_dataset = 100000

# Create DataFrame with specified dtypes
df = pd.DataFrame({col: pd.Series(dtype=dtype_dict[col]) for col in features})

# Fill POLID separately (since it needs a specific generation method)
df['POLID'] = [uuid.uuid4().hex for _ in range(num_dataset)]

print(df.dtypes)
print(f"\\nDataFrame shape: {df.shape}")''',
    '''num_dataset = 100000
print(f"num_dataset = {num_dataset}")''')

# 4. Data-gen cells -> comments (generation moved into generate_dataset)
set_source('b2bc12b6',
            '# Coverage / vehicle / sum-assured / region / engine-capacity generation\n'
            '# moved into generate_dataset() (cell 050b235c).')
set_source('243b84e2',
            '# Driver age category / age / gender / marital-status generation\n'
            '# moved into generate_dataset() (cell 050b235c).')
set_source('f406da4f',
            '# CAR_AGE generation moved into generate_dataset() (cell 050b235c).\n'
            '# age_to_cat removed: DRIVER_AGE_CAT is frozen at inception.')
set_source('0eebf856',
            '# Region flood/theft risk assignment moved into generate_dataset() (cell 050b235c).')

# 5. NCD setup: instantiate config, re-expose module globals used downstream
set_source('ncd-setup', '''# NCD setup - exact PIAM table progression (single source: CohortConfig)
COHORT_CONFIG = CohortConfig()

COHORT_YEAR = COHORT_CONFIG.cohort_year
NCD_TABLE = COHORT_CONFIG.ncd_table
NCD_ENTRY_YEARS = COHORT_CONFIG.ncd_entry_years
NCD_ENTRY_WEIGHTS = COHORT_CONFIG.ncd_entry_weights

print('NCD setup ready (from CohortConfig). Entry NCD mix:')
print(pd.Series(NCD_ENTRY_WEIGHTS, index=NCD_ENTRY_YEARS)
      .map(lambda x: f'{x:.1%}').to_string())''')

# 6. Premium cells: keep function defs, drop df mutation (moved into generator)
rep('403f8b5e',
    '''df["BASIC_PREMIUM"] = df.apply(calculate_premium, axis=1)
print(f"Avg basic premium: RM{df['BASIC_PREMIUM'].mean():.2f}")''',
    '# BASIC_PREMIUM applied inside generate_dataset (cell 050b235c)')

rep('sst-premium',
    '''df['FINAL_PREMIUM_SST'] = df.apply(compute_final_premium, axis=1)
df['TOTAL_LOADING'] = df.apply(
    lambda r: total_loading(r['DRIVER_AGE_CAT'], r['CAR_AGE']), axis=1
)

sample = df[['POLID', 'BASIC_PREMIUM', 'DRIVER_AGE_CAT', 'CAR_AGE', 'NCD_LEVEL',
             'FLOOD_RISK', 'THEFT_RISK', 'FINAL_PREMIUM_SST']].head(10)
print('Premium calculation complete:')
print(sample.to_string())
print(f"\\nAvg basic premium: RM{df['BASIC_PREMIUM'].mean():.2f}")
print(f"Avg final premium: RM{df['FINAL_PREMIUM_SST'].mean():.2f}")
print(f"Avg total loading: {df['TOTAL_LOADING'].mean():.3f}")''',
    '# FINAL_PREMIUM_SST / TOTAL_LOADING applied inside generate_dataset (cell 050b235c)')

# 7. Build the initial cohort (single call, after all premium functions exist)
insert_after('sst-premium', 'cohort-generation', '''# Build the initial cohort (single generator call)
df = generate_dataset(COHORT_CONFIG, seed=COHORT_CONFIG.seed)

print(f"Initial cohort: {len(df):,} policies, year {COHORT_CONFIG.cohort_year}")
print(df[['POLID', 'COVERAGE_TYPE', 'DRIVER_AGE_CAT', 'DRIVER_AGE', 'CAR_AGE',
          'NCD_LEVEL', 'BASIC_PREMIUM', 'FINAL_PREMIUM_SST']].head(5)
      .to_string(index=False))
print(df.dtypes)''')

# 8. simulate_cohort: drop unused entrant weights, freeze category, entrant via generator
rep('cohort-simulation',
    '    entrant_weights = (0.40, 0.40, 0.15, 0.05)\n'
    '    entrant_cats = ["Gen-Z", "Millennial", "Boomers", "Senior"]',
    '    # Entrants come from generate_dataset() (same assumptions as the initial cohort)')

rep('cohort-simulation',
    '''            df_active.loc[aging_mask, 'DRIVER_AGE_CAT'] = df_active.loc[
                aging_mask, 'DRIVER_AGE'
            ].apply(age_to_cat)''',
    '''            # DRIVER_AGE_CAT frozen at inception (age_to_cat removed)''')

rep('cohort-simulation',
    '''        # Add new entrants for next year (fresh ages, unique POLID)
        if year_offset < n_years - 1 and new_entrants_per_year > 0:
            new_cohort = df_initial.sample(
                n=new_entrants_per_year, replace=True,
                random_state=seed + year_offset
            ).copy()
            n_new = len(new_cohort)
            new_cohort['POLID'] = [f"ENT{year + 1}-{i}" for i in range(n_new)]
            new_cohort['DRIVER_AGE_CAT'] = np.random.choice(
                entrant_cats, size=n_new, p=entrant_weights
            )
            new_cohort['DRIVER_AGE'] = new_cohort['DRIVER_AGE_CAT'].apply(
                generate_age_by_category
            )
            new_cohort['CAR_AGE'] = new_cohort['DRIVER_AGE_CAT'].apply(
                generate_car_age
            )
            new_cohort['COHORT_YEAR'] = year + 1
            new_cohort['NCD_YEARS'] = np.random.choice(
                NCD_ENTRY_YEARS, size=n_new, p=NCD_ENTRY_WEIGHTS
            )
            new_cohort['NCD_LEVEL'] = new_cohort['NCD_YEARS'].apply(
                lambda y: NCD_TABLE.get(int(min(y, 5)), 0.55)
            )
            new_cohort['BASIC_PREMIUM'] = new_cohort.apply(calculate_premium, axis=1)
            new_cohort['CLAIM_LAMBDA'] = new_cohort.apply(compute_claim_lambda, axis=1)
            new_cohort['TOTAL_LOADING'] = new_cohort.apply(
                lambda r: total_loading(r['DRIVER_AGE_CAT'], r['CAR_AGE']), axis=1
            )
            new_cohort['FINAL_PREMIUM_SST'] = new_cohort.apply(
                compute_final_premium, axis=1
            )
            df_active = pd.concat(
                [df_active[df_active['RENEWED']], new_cohort],
                ignore_index=True
            )''',
    '''        # Add new entrants for next year (same generator + assumptions as initial)
        if year_offset < n_years - 1 and new_entrants_per_year > 0:
            new_cohort = generate_dataset(
                COHORT_CONFIG, seed=seed + year_offset,
                n=new_entrants_per_year, cohort_year=year + 1,
                polid_prefix='ENT'
            )
            df_active = pd.concat(
                [df_active[df_active['RENEWED']], new_cohort],
                ignore_index=True
            )''')

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Saved. Total cells:', len(nb['cells']))