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


patch('def simulate_cohort(df_initial, n_years=5, new_entrants_per_year=None,', [
    (
        "def simulate_cohort(df_initial, n_years=5, new_entrants_per_year=None,\n"
        "                    premium_trend_annual=1.06, seed=42, cfg=COHORT_CONFIG,\n"
        "                    pricing_cfg=None, verbose=True):",
        "def simulate_cohort(df_initial, n_years=5, new_entrants_per_year=None,\n"
        "                    seed=42, cfg=COHORT_CONFIG, verbose=True):"),

    (
        "        premium_trend_annual: Annual premium inflation used for retention only\n"
        "        seed: Random seed for reproducibility (local Generator)",
        "        seed: Random seed for reproducibility (local Generator)"),

    (
        "        # Recompute frequency + premium with current ages and NCD\n"
        "        # (NCD_LEVEL here still reflects claims through the PRIOR year -> one-year lag)\n"
        "        df_active['CLAIM_LAMBDA'] = claim_lambda_array(df_active, cfg)\n"
        "        df_active['TOTAL_LOADING'] = total_loading_array(df_active, cfg)\n"
        "        df_active['NCD_LEVEL_PRICED'] = df_active['NCD_LEVEL']\n"
        "        if pricing_cfg is None:\n"
        "            df_active['FINAL_PREMIUM_SST'] = final_premium_array(df_active, cfg)\n"
        "        else:\n"
        "            pf = pricing_cfg['model'].predict(\n"
        "                pricing_cfg['encode'](df_active, pricing_cfg['features']))\n"
        "            sev_map = pricing_cfg.get('avg_sev_by_cov')\n"
        "            if sev_map is not None:\n"
        "                sev = df_active['COVERAGE_TYPE'].map(sev_map).astype(float).values\n"
        "            else:\n"
        "                sev = np.full(len(df_active), pricing_cfg['avg_sev'])\n"
        "            prem = (pf * sev * pricing_cfg['expense_loading']\n"
        "                    * pricing_cfg['telemetric_load'])\n"
        "            prem = prem * (1.1 ** df_active['FLOOD_RISK'].values.astype(int))\n"
        "            prem = prem * (1.1 ** df_active['THEFT_RISK'].values.astype(int))\n"
        "            df_active['FINAL_PREMIUM_SST'] = prem.round(2)",
        "        # Recompute frequency + loadings with current ages and NCD\n"
        "        # (NCD_LEVEL here still reflects claims through the PRIOR year -> one-year lag)\n"
        "        df_active['CLAIM_LAMBDA'] = claim_lambda_array(df_active, cfg)\n"
        "        df_active['TOTAL_LOADING'] = total_loading_array(df_active, cfg)\n"
        "        df_active['NCD_LEVEL_PRICED'] = df_active['NCD_LEVEL']"),

    (
        "        # Premium change signal (retention only - not stored premium)\n"
        "        premium_change_pct = premium_trend_annual ** year_offset - 1\n"
        "        df_active['PREMIUM_CHANGE_PCT'] = premium_change_pct",
        "        # Retention is premium-independent (driver A: experience + telematics)"),

    (
        "        df_active['RENEWAL_PROB'] = retention_prob_array(df_active, premium_change_pct)",
        "        df_active['RENEWAL_PROB'] = retention_prob_array(df_active)"),

    (
        "                        'BASIC_PREMIUM', 'FINAL_PREMIUM_SST', 'TOTAL_LOADING',",
        "                        'BASIC_PREMIUM', 'TOTAL_LOADING',"),

    (
        "                        'CLAIM_PERIL', 'PREMIUM_CHANGE_PCT',",
        "                        'CLAIM_PERIL',"),

    (
        "        if verbose:\n"
        "            print(f\"Year {year}: {len(df_active)} active policies, \"\n"
        "                  f\"claims: {df_active['CLAIM_COUNT'].sum()}, \"\n"
        "                  f\"freq: {df_active['CLAIM_OCCURRED'].mean():.1%}, \"\n"
        "                  f\"avg NCD priced: {df_active['NCD_LEVEL_PRICED'].mean():.2%}, \"\n"
        "                  f\"avg premium: RM{df_active['FINAL_PREMIUM_SST'].mean():.2f}, \"\n"
        "                  f\"retention: {df_active['RENEWED'].mean():.1%}\")",
        "        if verbose:\n"
        "            print(f\"Year {year}: {len(df_active)} active policies, \"\n"
        "                  f\"claims: {df_active['CLAIM_COUNT'].sum()}, \"\n"
        "                  f\"freq: {df_active['CLAIM_OCCURRED'].mean():.1%}, \"\n"
        "                  f\"avg NCD priced: {df_active['NCD_LEVEL_PRICED'].mean():.2%}, \"\n"
        "                  f\"retention: {df_active['RENEWED'].mean():.1%}\")"),
])

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved simulate_cohort patch')
