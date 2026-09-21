import json

NB = 'main.ipynb'
nb = json.load(open(NB, encoding='utf-8'))

ENGINE_SRC = '''# ============================================================================
# PREMIUM PRICING ENGINE (hot-swappable) - placed AFTER simulation, decoupled
# from simulate_cohort (now premium-independent / labels only).
# Registry: 'tariff' (rule-based final_premium_array), 'glm', 'telem'.
# ============================================================================

from sklearn.linear_model import PoissonRegressor
from scipy.stats import spearmanr

_PRICING_FEATURES = {
    'glm': ['DRIVER_AGE', 'CAR_AGE', 'NCD_LEVEL_PRICED', 'VEHICLE_TYPE',
            'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION'],
    'telem': ['DRIVER_AGE', 'CAR_AGE', 'NCD_LEVEL_PRICED', 'VEHICLE_TYPE',
              'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION',
              'telematics_score'],
}


def _pricing_features(method):
    if method in _PRICING_FEATURES:
        return list(_PRICING_FEATURES[method])
    raise ValueError('unknown pricing method: ' + str(method))


def _encode_features(df, features):
    _CAT = ['VEHICLE_TYPE', 'COVERAGE_TYPE', 'REGION']
    X = df[features].copy()
    for col in _CAT:
        if col in features:
            X[col] = X[col].astype('category').cat.codes
    return X


def train_pricing(book, method='tariff', cfg=COHORT_CONFIG):
    """Fit a frequency model on entrant policy-years (no claim-history endogeneity).

    Target = CLAIM_COUNT; severity priced separately from avg severity by coverage.
    """
    features = _pricing_features(method)
    tr_src = book[book['COHORT_YEAR'] == book['SIM_YEAR']]
    pids = tr_src['POLID'].unique()
    train_pids = set(np.random.default_rng(7).choice(
        pids, int(len(pids) * 0.6), replace=False))
    tr = tr_src[tr_src['POLID'].isin(train_pids)]
    model = PoissonRegressor(alpha=1e-3, max_iter=1000).fit(
        _encode_features(tr, features), tr['CLAIM_COUNT'])
    avg_sev_by_cov = book.groupby('COVERAGE_TYPE').apply(
        lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum(),
        include_groups=False).to_dict()
    return {'features': features, 'model': model,
            'avg_sev_by_cov': avg_sev_by_cov,
            'expense_loading': cfg.get('expense_loading', 1.40),
            'telemetric_load': cfg.get('telemetric_load', 1.0)}


def price_book(book, method='tariff', cfg=COHORT_CONFIG):
    """Return a copy of `book` with FINAL_PREMIUM_SST computed by `method`."""
    out = book.copy()
    if method == 'tariff':
        out['FINAL_PREMIUM_SST'] = final_premium_array(out, cfg)
        return out
    pricer = train_pricing(book, method, cfg)
    X = _encode_features(out, pricer['features'])
    pf = pricer['model'].predict(X)
    sev = out['COVERAGE_TYPE'].map(pricer['avg_sev_by_cov']).astype(float).values
    prem = (pf * sev * pricer['expense_loading'] * pricer['telemetric_load'])
    prem = prem * (1.1 ** out['FLOOD_RISK'].values.astype(int))
    prem = prem * (1.1 ** out['THEFT_RISK'].values.astype(int))
    out['FINAL_PREMIUM_SST'] = prem.round(2)
    return out


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


def compare_pricing(book, methods=('tariff', 'glm', 'telem'), cfg=COHORT_CONFIG):
    rows = []
    for m in methods:
        b = price_book(book, m, cfg)
        rows.append({
            'model': m,
            'overall_LR(%)': round(b['CLAIM_AMOUNT'].sum() / b['FINAL_PREMIUM_SST'].sum() * 100, 2),
            'retained_LR(%)': round(_retained_lr(b), 2),
            'prem_count_rho': round(spearmanr(b['FINAL_PREMIUM_SST'], b['CLAIM_COUNT']).correlation, 4),
            'tier_spread(pp)': round(_tier_spread(b), 1),
            'avg_premium': round(b['FINAL_PREMIUM_SST'].mean(), 2),
        })
    return pd.DataFrame(rows)
'''

anchor = '# Run simulation (single trajectory, full detail - feeds all downstream cells)'
idx = None
for i, c in enumerate(nb['cells']):
    if anchor in ''.join(c.get('source', [])):
        idx = i
        break
if idx is None:
    raise SystemExit('main-run anchor not found')

new_cell = {
    'cell_type': 'code',
    'execution_count': None,
    'metadata': {'collapsed': False},
    'outputs': [],
    'source': ENGINE_SRC.splitlines(keepends=True),
}
nb['cells'].insert(idx, new_cell)
print('inserted engine cell before index', idx)

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved engine insert')
