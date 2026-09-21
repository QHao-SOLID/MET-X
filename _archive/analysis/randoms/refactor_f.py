import json

NB = 'main.ipynb'
nb = json.load(open(NB, encoding='utf-8'))


def fc(anchor):
    for c in nb['cells']:
        if anchor in ''.join(c.get('source', [])):
            return c
    raise SystemExit('not found: ' + anchor)


def patch(anchor, repls):
    c = fc(anchor)
    s = ''.join(c.get('source', []))
    for o, n in repls:
        k = s.count(o)
        if k != 1:
            raise SystemExit('match %d for %r' % (k, o[:70]))
        s = s.replace(o, n)
    c['source'] = s.splitlines(keepends=True)
    print('patched', anchor)


# 1) Main-run cell: simulate labels, then place premium via engine
patch('# Run simulation (single trajectory, full detail - feeds all downstream cells)', [
    (
        "# Run simulation (single trajectory, full detail - feeds all downstream cells)\n"
        "cohort_results = simulate_cohort(\n"
        "    df, n_years=20, new_entrants_per_year=None)",
        "# Run simulation (single trajectory, premium-independent / labels only)\n"
        "cohort_results = simulate_cohort(\n"
        "    df, n_years=5, new_entrants_per_year=None)\n"
        "# Place premium via the hot-swappable pricing engine (telem = primary regime)\n"
        "cohort_results = price_book(cohort_results, 'telem', COHORT_CONFIG)"),
])

# 2) Cell PR: one simulation, re-price under 3 regimes via the engine
patch('# --- three identical initial cohorts (same seed) ---', [
    (
        "# --- three identical initial cohorts (same seed) ---\n"
        "df_tariff, df_glm, df_telem = df.copy(), df.copy(), df.copy()\n"
        "\n"
        "# --- Act 1: traditional tariff (unchanged premium) ---\n"
        "cohort_results_tariff = simulate_cohort(\n"
        "    df_tariff, n_years=20, new_entrants_per_year=None, seed=42)\n"
        "\n"
        "avg_sev = (cohort_results_tariff['CLAIM_AMOUNT'].sum()\n"
        "           / cohort_results_tariff['CLAIM_COUNT'].sum())\n"
        "avg_sev_by_cov = cohort_results_tariff.groupby('COVERAGE_TYPE').apply(\n"
        "    lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum(), include_groups=False).to_dict()\n"
        "exp_loading = COHORT_CONFIG.get('expense_loading', 1.40)\n"
        "telem_load = COHORT_CONFIG.get('telemetric_load', 1.0)\n"
        "\n"
        "# --- train set: entrant-only policy-years (entry NCD semantics, no claim-history\n"
        "#     endogeneity), 60% of unique policies held out of fitting ---\n"
        "tr_src = cohort_results_tariff[\n"
        "    cohort_results_tariff['COHORT_YEAR'] == cohort_results_tariff['SIM_YEAR']]\n"
        "_pids = tr_src['POLID'].unique()\n"
        "_train_pids = set(np.random.default_rng(7).choice(_pids, int(len(_pids) * 0.6), replace=False))\n"
        "tr = tr_src[tr_src['POLID'].isin(_train_pids)]\n"
        "print(f'training rows: {len(tr):,} (entrant policy-years, 60% of policies)')\n"
        "print(f'GLM NCD feature: NCD_LEVEL_PRICED (the value priced at simulation time, '\n"
        "      f'not the end-of-year post-update level)')\n"
        "\n"
        "# --- Act 2: GLM (traditional factors only -> blind to behavior) ---\n"
        "glm_model = PoissonRegressor(alpha=1e-3, max_iter=1000).fit(\n"
        "    _encode_features(tr, GLM_FEATURES), tr['CLAIM_COUNT'])\n"
        "pricing_glm = {'model': glm_model, 'features': GLM_FEATURES,\n"
        "               'encode': _encode_features, 'avg_sev': avg_sev,\n"
        "               'avg_sev_by_cov': avg_sev_by_cov,\n"
        "               'expense_loading': exp_loading, 'telemetric_load': 1.0}\n"
        "cohort_results_glm = simulate_cohort(\n"
        "    df_glm, n_years=20, new_entrants_per_year=None, seed=42, pricing_cfg=pricing_glm)\n"
        "\n"
        "# --- Act 3: GLM + telematics (sees telematics_score) ---\n"
        "telem_model = PoissonRegressor(alpha=1e-3, max_iter=1000).fit(\n"
        "    _encode_features(tr, TELEM_FEATURES), tr['CLAIM_COUNT'])\n"
        "pricing_telem = {'model': telem_model, 'features': TELEM_FEATURES,\n"
        "                 'encode': _encode_features, 'avg_sev': avg_sev,\n"
        "                 'avg_sev_by_cov': avg_sev_by_cov,\n"
        "                 'expense_loading': exp_loading, 'telemetric_load': telem_load}\n"
        "cohort_results_telem = simulate_cohort(\n"
        "    df_telem, n_years=20, new_entrants_per_year=None, seed=42, pricing_cfg=pricing_telem)\n"
        "\n"
        "print(f'avg severity/claim: RM{avg_sev:,.0f} | by coverage: ' +\n"
        "      ', '.join(f'{k} RM{v:,.0f}' for k, v in sorted(avg_sev_by_cov.items())) +\n"
        "      f' | expense_loading: {exp_loading:.2f} | telemetric_load: {telem_load:.2f}')",
        "# --- ONE simulation (premium-independent), then re-price under 3 regimes ---\n"
        "cohort_results = simulate_cohort(\n"
        "    df, n_years=5, new_entrants_per_year=None, seed=42)\n"
        "\n"
        "cohort_results_tariff = price_book(cohort_results, 'tariff', COHORT_CONFIG)\n"
        "cohort_results_glm = price_book(cohort_results, 'glm', COHORT_CONFIG)\n"
        "cohort_results_telem = price_book(cohort_results, 'telem', COHORT_CONFIG)\n"
        "\n"
        "avg_sev = (cohort_results['CLAIM_AMOUNT'].sum()\n"
        "           / cohort_results['CLAIM_COUNT'].sum())\n"
        "avg_sev_by_cov = cohort_results.groupby('COVERAGE_TYPE').apply(\n"
        "    lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum(), include_groups=False).to_dict()\n"
        "exp_loading = COHORT_CONFIG.get('expense_loading', 1.40)\n"
        "telem_load = COHORT_CONFIG.get('telemetric_load', 1.0)\n"
        "print(f'avg severity/claim: RM{avg_sev:,.0f} | by coverage: ' +\n"
        "      ', '.join(f'{k} RM{v:,.0f}' for k, v in sorted(avg_sev_by_cov.items())) +\n"
        "      f' | expense_loading: {exp_loading:.2f} | telemetric_load: {telem_load:.2f}')"),
])

# 3) Report pricing-progression: replace local training with engine price_book calls
patch("    avg_sev = res['CLAIM_AMOUNT'].sum() / res['CLAIM_COUNT'].sum()", [
    (
        "    avg_sev = res['CLAIM_AMOUNT'].sum() / res['CLAIM_COUNT'].sum()\n"
        "    avg_sev_by_cov = res.groupby('COVERAGE_TYPE').apply(\n"
        "        lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum()).to_dict()\n"
        "    exp_loading = cfg.get('expense_loading', 1.40)\n"
        "    telem_load = cfg.get('telemetric_load', 1.0)\n"
        "    tr_src = res[res['COHORT_YEAR'] == res['SIM_YEAR']]\n"
        "    _pids = tr_src['POLID'].unique()\n"
        "    _train_pids = set(np.random.default_rng(7).choice(_pids, int(len(_pids) * 0.6), replace=False))\n"
        "    tr = tr_src[tr_src['POLID'].isin(_train_pids)]\n"
        "    glm_model = PoissonRegressor(alpha=1e-3, max_iter=1000).fit(\n"
        "        _encode_features(tr, GLM_FEATURES), tr['CLAIM_COUNT'])\n"
        "    telem_model = PoissonRegressor(alpha=1e-3, max_iter=1000).fit(\n"
        "        _encode_features(tr, TELEM_FEATURES), tr['CLAIM_COUNT'])\n"
        "    sev_arr = res['COVERAGE_TYPE'].map(avg_sev_by_cov).astype(float).values\n"
        "    prem_g = (glm_model.predict(_encode_features(res, GLM_FEATURES)) * sev_arr * exp_loading * 1.0).round(2)\n"
        "    prem_t = (telem_model.predict(_encode_features(res, TELEM_FEATURES)) * sev_arr * exp_loading * telem_load).round(2)\n"
        "    d_tariff, d_glm, d_telem = res.copy(), res.copy(), res.copy()\n"
        "    d_glm['FINAL_PREMIUM_SST'] = prem_g\n"
        "    d_telem['FINAL_PREMIUM_SST'] = prem_t",
        "    d_tariff = price_book(res, 'tariff', cfg)\n"
        "    d_glm = price_book(res, 'glm', cfg)\n"
        "    d_telem = price_book(res, 'telem', cfg)"),
])

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved main-run + PR + report patch')
