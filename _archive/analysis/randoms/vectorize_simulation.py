import json

nb = json.load(open('main.ipynb', encoding='utf-8'))
cells = nb['cells']


def get(cid):
    for c in cells:
        if c['id'] == cid:
            return c
    raise KeyError(cid)


def rep(cid, old, new, expect=1):
    c = get(cid)
    s = ''.join(c['source'])
    n = s.count(old)
    assert n == expect, f'{cid}: found {n} of {old!r}, expected {expect}'
    c['source'] = s.replace(old, new).splitlines(keepends=True)
    c['outputs'] = []
    c['execution_count'] = None
    print(f'ok {cid}: {n}x {old[:60]!r}')


def new_cell(cid, source):
    return {
        'id': cid,
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': source.splitlines(keepends=True),
    }


def insert_before(anchor_id, cell):
    i = next(i for i, c in enumerate(cells) if c['id'] == anchor_id)
    cells.insert(i, cell)
    print(f'inserted {cell["id"]} before {anchor_id}')


def insert_after(anchor_id, cell):
    i = next(i for i, c in enumerate(cells) if c['id'] == anchor_id)
    cells.insert(i + 1, cell)
    print(f'inserted {cell["id"]} after {anchor_id}')


def rewrite(cid, source):
    c = get(cid)
    c['source'] = source.splitlines(keepends=True)
    c['outputs'] = []
    c['execution_count'] = None
    print('rewrote', cid)


# --- A. config: claim_frequency_base overridable ---------------------------------
rep('config-assumptions', "    'cohort_year': 2026,",
    "    'cohort_year': 2026,\n    'claim_frequency_base': -2.00,")

# --- claim-model-lambda: read base from config ------------------------------------
rep('claim-model-lambda', 'CLAIM_FREQUENCY_BASE = -2.00',
    "CLAIM_FREQUENCY_BASE = COHORT_CONFIG['claim_frequency_base']")

# --- B. sim-fast: vectorized helpers (insert before cohort-simulation) -----------
SIM_FAST = '''# ============================================================================
# VECTORIZED SIMULATION HELPERS (NumPy) - hot-path replacement for row-wise apply
# Same models as the scalar versions (claim-model-lambda / claim-model-severity /
# sst-premium / retention-model). cfg param threads scenario overrides through.
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


def final_premium_array(df, cfg=COHORT_CONFIG, sst_rate=SST_RATE):
    """Vectorized FINAL_PREMIUM_SST: BASIC x loading x (1-NCD) x 1.1^flags x (1+SST)."""
    loading = total_loading_array(df, cfg)
    ncd = 1 - df['NCD_LEVEL'].values
    risk = 1.1 ** (df['FLOOD_RISK'].values.astype(int) + df['THEFT_RISK'].values.astype(int))
    return (df['BASIC_PREMIUM'].values * loading * ncd * risk * (1 + sst_rate)).round(2)


def retention_prob_array(df, premium_change_pct):
    """Vectorized binomial-logit retention proxy, same model as compute_retention_probability."""
    p = np.full(len(df), 0.80)
    pc = np.full(len(df), premium_change_pct)
    p -= np.where(pc > 0.15, 0.15, np.where(pc > 0.05, 0.10, 0.0))
    p += np.where(pc < -0.05, 0.05, 0.0)
    p -= 0.25 * df['CLAIM_OCCURRED'].values.astype(float)
    ncd = df['NCD_YEARS'].values
    p += np.select([ncd >= 3, ncd >= 2], [0.15, 0.08], default=0.0)
    return np.clip(p, 0.1, 0.95)


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
    idx = (u > np.cumsum(P, axis=1)).sum(axis=1)
    return np.array(_PERIL_NAMES)[idx]


def _peril_params(perils, sa, cfg):
    """Vectorized Gamma shape/scale/cap per peril (caps vs sum assured)."""
    peril_base = cfg.get('peril_base', PERIL_BASE)
    n = len(perils)
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
            scale[m] = np.clip(sa[m] * s_f, s_lo, s_hi)
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
    shape, scale, cap = _peril_params(perils, sa, cfg)
    amts = np.minimum(rng.gamma(shape, scale), cap)
    np.add.at(amount, idx, amts)
    s = pd.Series(perils).groupby(pd.Series(idx)).agg('/'.join)
    peril_out[np.flatnonzero(claim_mask)] = s.values
    return amount, peril_out
'''
insert_before('cohort-simulation', new_cell('sim-fast', SIM_FAST))

# --- B. rewrite simulate_cohort (local RNG, cfg-threaded, vectorized) ------------
COHORT_SIM = '''# ============================================================================
# COHORT EVOLUTION SIMULATION (vectorized; local RNG; config-threaded)
# In-force policies age each year (DRIVER_AGE, CAR_AGE +1); claim frequency and
# final premium are recomputed annually with the new ages and NCD (one-year lag:
# year N is priced with the NCD earned through year N-1).
# ============================================================================

def simulate_cohort(df_initial, n_years=5, new_entrants_per_year=5000,
                    premium_trend_annual=1.06, seed=42, cfg=COHORT_CONFIG,
                    verbose=True):
    """Simulate cohort evolution (vectorized hot path; per-seed local RNG).

    Args:
        df_initial: Starting cohort (Year 1)
        n_years: Number of years to simulate
        new_entrants_per_year: New policies entering each year
        premium_trend_annual: Annual premium inflation used for retention only
        seed: Random seed for reproducibility (local Generator)
        cfg: config dict (default COHORT_CONFIG); threaded to helpers + entrants
        verbose: per-year + summary prints

    Returns:
        pd.DataFrame with all policy-year records
    """
    import time
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

        # Recompute frequency + premium with current ages and NCD
        # (NCD_LEVEL here still reflects claims through the PRIOR year -> one-year lag)
        df_active['CLAIM_LAMBDA'] = claim_lambda_array(df_active, cfg)
        df_active['TOTAL_LOADING'] = total_loading_array(df_active, cfg)
        df_active['NCD_LEVEL_PRICED'] = df_active['NCD_LEVEL']
        df_active['FINAL_PREMIUM_SST'] = final_premium_array(df_active, cfg)

        # Simulate claims (Poisson frequency, vectorized)
        df_active['CLAIM_COUNT'] = rng.poisson(df_active['CLAIM_LAMBDA'].values)
        df_active['CLAIM_OCCURRED'] = df_active['CLAIM_COUNT'] > 0

        # Simulate severity (per-peril Gamma, vectorized, aggregated per policy-year)
        amounts, perils = simulate_claim_severity_vectorized(df_active, rng, cfg)
        df_active['CLAIM_AMOUNT'] = amounts
        df_active['CLAIM_PERIL'] = perils

        # Premium change signal (retention only - not stored premium)
        premium_change_pct = premium_trend_annual ** year_offset - 1
        df_active['PREMIUM_CHANGE_PCT'] = premium_change_pct

        # Retention + renewals (vectorized)
        df_active['RENEWAL_PROB'] = retention_prob_array(df_active, premium_change_pct)
        df_active['RENEWED'] = rng.random(len(df_active)) < df_active['RENEWAL_PROB'].values

        # Update NCD based on claims
        df_active.loc[~df_active['CLAIM_OCCURRED'], 'NCD_YEARS'] += 1
        df_active.loc[df_active['CLAIM_OCCURRED'], 'NCD_YEARS'] = 0
        df_active['NCD_LEVEL'] = ncd_level_array(df_active['NCD_YEARS'].values, cfg)

        # Record full year state (including lapsers) for retention analysis
        cols_to_keep = ['POLID', 'COVERAGE_TYPE', 'SUM_ASSURED', 'REGION',
                        'VEHICLE_TYPE', 'DRIVER_AGE_CAT', 'DRIVER_AGE',
                        'CAR_AGE', 'DRIVER_GENDER', 'FLOOD_RISK', 'THEFT_RISK',
                        'BASIC_PREMIUM', 'FINAL_PREMIUM_SST', 'TOTAL_LOADING',
                        'NCD_LEVEL_PRICED', 'NCD_LEVEL',
                        'NCD_YEARS', 'CLAIM_LAMBDA',
                        'SIM_YEAR', 'CLAIM_COUNT', 'CLAIM_OCCURRED', 'CLAIM_AMOUNT',
                        'CLAIM_PERIL', 'PREMIUM_CHANGE_PCT',
                        'RENEWAL_PROB', 'RENEWED', 'COHORT_YEAR']
        history.append(df_active[cols_to_keep].copy())

        if verbose:
            print(f"Year {year}: {len(df_active)} active policies, "
                  f"claims: {df_active['CLAIM_COUNT'].sum()}, "
                  f"freq: {df_active['CLAIM_OCCURRED'].mean():.1%}, "
                  f"avg NCD priced: {df_active['NCD_LEVEL_PRICED'].mean():.2%}, "
                  f"avg premium: RM{df_active['FINAL_PREMIUM_SST'].mean():.2f}, "
                  f"retention: {df_active['RENEWED'].mean():.1%}")

        # Add new entrants for next year (same generator + assumptions as initial)
        if year_offset < n_years - 1 and new_entrants_per_year > 0:
            new_cohort = generate_dataset(
                cfg, seed=seed + year_offset,
                n=new_entrants_per_year, cohort_year=year + 1,
                polid_prefix='ENT'
            )
            df_active = pd.concat(
                [df_active[df_active['RENEWED']], new_cohort],
                ignore_index=True
            )
        else:
            df_active = df_active[df_active['RENEWED']].copy()

    cohort_results = pd.concat(history, ignore_index=True)
    if verbose:
        print(f"\\nSimulation complete. Total records: {len(cohort_results)}")
        print(f"Year range: {cohort_results['SIM_YEAR'].min()} - {cohort_results['SIM_YEAR'].max()}")
        print(f"Simulation wall time: {time.time() - t0:.1f}s")
    return cohort_results


# Run simulation (single trajectory, full detail - feeds all downstream cells)
cohort_results = simulate_cohort(
    df, n_years=20, new_entrants_per_year=int(0.50 * COHORT_CONFIG['n']))
'''
rewrite('cohort-simulation', COHORT_SIM)

# --- C. monte-carlo API cell (after cohort-simulation) ---------------------------
MONTE_CARLO = '''# ============================================================================
# MONTE CARLO API - scenario x seed grid, summary metrics + percentiles
# Vectorized engine + per-seed local RNG -> safe for parallel seeds.
# ============================================================================
import copy
try:
    from joblib import Parallel, delayed
    _HAS_JOBLIB = True
except ImportError:
    _HAS_JOBLIB = False


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


def _run_one(cfg, seed, n_years, new_entrants_per_year):
    df0 = generate_dataset(cfg, seed=seed)
    res = simulate_cohort(df0, n_years=n_years,
                          new_entrants_per_year=new_entrants_per_year,
                          seed=seed, cfg=cfg, verbose=False)
    return summarize(res)


def run_monte_carlo(overrides=None, seeds=(42,), n_years=20,
                    new_entrants_per_year=None, n_jobs=-1):
    """Run a (scenario x seed) Monte Carlo grid.

    Args:
        overrides: None | dict | list[dict] - assumption patches on COHORT_CONFIG
        seeds: int | list[int] - independent replications per scenario
        n_years: simulation horizon
        new_entrants_per_year: entrants per year (default 0.50 * COHORT_CONFIG['n'])
        n_jobs: parallel workers (threading backend; numpy releases the GIL)

    Returns:
        (metrics_df, summary_df, yearly_lr_df)
          metrics_df:  one row per (scenario, seed)
          summary_df:  per scenario mean/std/p05/p50/p95 of overall LR + mean stats
          yearly_lr_df: per (scenario, seed, year) loss ratio
    """
    if new_entrants_per_year is None:
        new_entrants_per_year = int(0.50 * COHORT_CONFIG['n'])
    if overrides is None:
        overrides = [None]
    elif isinstance(overrides, dict):
        overrides = [overrides]
    if isinstance(seeds, int):
        seeds = [seeds]

    tasks = [(i, ov, s) for i, ov in enumerate(overrides) for s in seeds]

    def work(t):
        i, ov, s = t
        cfg = deep_update(COHORT_CONFIG, ov)
        metrics, yearly = _run_one(cfg, s, n_years, new_entrants_per_year)
        return i, ov, s, metrics, yearly

    if _HAS_JOBLIB and n_jobs != 1 and len(tasks) > 1:
        out = Parallel(n_jobs=n_jobs, backend='threading')(
            delayed(work)(t) for t in tasks)
    else:
        out = [work(t) for t in tasks]

    rows, yearly_rows = [], []
    for i, ov, s, metrics, yearly in out:
        rows.append({'scenario': i, 'overrides': repr(ov) if ov else 'base',
                     'seed': s, **metrics})
        for year, lr in yearly.items():
            yearly_rows.append({'scenario': i, 'seed': s, 'SIM_YEAR': int(year),
                                'loss_ratio': lr})
    metrics_df = pd.DataFrame(rows)
    yearly_df = pd.DataFrame(yearly_rows)

    summ = []
    for i in range(len(overrides)):
        g = metrics_df[metrics_df['scenario'] == i]
        summ.append({
            'scenario': i,
            'overrides': g['overrides'].iloc[0],
            'n_seeds': len(g),
            'lr_mean': g['overall_lr'].mean(),
            'lr_std': g['overall_lr'].std(),
            'lr_p05': g['overall_lr'].quantile(0.05),
            'lr_p50': g['overall_lr'].median(),
            'lr_p95': g['overall_lr'].quantile(0.95),
            'freq_mean': g['claim_freq'].mean(),
            'premium_mean': g['avg_premium'].mean(),
            'retention_mean': g['retention'].mean(),
        })
    summary_df = pd.DataFrame(summ)
    return metrics_df, summary_df, yearly_df


# Demo: base vs higher-frequency scenario, 3 seeds, 5 years
_demo_metrics, _demo_summary, _demo_yearly = run_monte_carlo(
    overrides=[None, {'claim_frequency_base': -1.80}],
    seeds=(1, 2, 3), n_years=5)
print('\\n=== Monte Carlo demo: metrics (scenario x seed) ===')
print(_demo_metrics[['scenario', 'overrides', 'seed', 'overall_lr',
                     'claim_freq', 'avg_premium', 'retention']].to_string(index=False))
print('\\n=== Monte Carlo demo: per-scenario summary (3 seeds) ===')
print(_demo_summary.round(4).to_string(index=False))
'''
insert_after('cohort-simulation', new_cell('monte-carlo', MONTE_CARLO))

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Saved')