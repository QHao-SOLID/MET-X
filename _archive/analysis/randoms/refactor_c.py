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


patch('def run_monte_carlo(overrides=None, seeds=(42,), n_years=20,', [
    (
        "def _run_one(cfg, seed, n_years, new_entrants_per_year,\n"
        "             book_seed=COHORT_CONFIG['seed']):\n"
        "    df0 = generate_dataset(cfg, seed=book_seed)\n"
        "    res = simulate_cohort(df0, n_years=n_years,\n"
        "                          new_entrants_per_year=new_entrants_per_year,\n"
        "                          seed=seed, cfg=cfg, verbose=False)\n"
        "    return summarize(res)",
        "def _run_one(cfg, seed, n_years, new_entrants_per_year, pricing_model='tariff',\n"
        "             book_seed=COHORT_CONFIG['seed']):\n"
        "    df0 = generate_dataset(cfg, seed=book_seed)\n"
        "    res = simulate_cohort(df0, n_years=n_years,\n"
        "                          new_entrants_per_year=new_entrants_per_year,\n"
        "                          seed=seed, cfg=cfg, verbose=False)\n"
        "    res = price_book(res, pricing_model, cfg)\n"
        "    return summarize(res)"),

    (
        "def run_monte_carlo(overrides=None, seeds=(42,), n_years=20,\n"
        "                    new_entrants_per_year=None, n_jobs=4, book_seed=None):",
        "def run_monte_carlo(overrides=None, seeds=(42,), n_years=20,\n"
        "                    new_entrants_per_year=None, n_jobs=4, book_seed=None,\n"
        "                    pricing_models=('tariff',)):"),

    (
        "        n_jobs: parallel workers (threading backend; numpy releases the GIL)\n"
        "        book_seed: initial-cohort RNG seed (default COHORT_CONFIG['seed']).",
        "        n_jobs: parallel workers (threading backend; numpy releases the GIL)\n"
        "        pricing_models: pricing models evaluated per (scenario, seed);\n"
        "                        e.g. ('tariff', 'glm', 'telem')\n"
        "        book_seed: initial-cohort RNG seed (default COHORT_CONFIG['seed'])."),

    (
        "    tasks = [(i, ov, s) for i, ov in enumerate(overrides) for s in seeds]",
        "    if isinstance(pricing_models, str):\n"
        "        pricing_models = (pricing_models,)\n"
        "    tasks = [(i, ov, s, pm) for i, ov in enumerate(overrides)\n"
        "             for s in seeds for pm in pricing_models]"),

    (
        "    def work(t):\n"
        "        i, ov, s = t\n"
        "        cfg = deep_update(COHORT_CONFIG, ov)\n"
        "        metrics, yearly = _run_one(cfg, s, n_years, new_entrants_per_year, book_seed)\n"
        "        return i, ov, s, metrics, yearly",
        "    def work(t):\n"
        "        i, ov, s, pm = t\n"
        "        cfg = deep_update(COHORT_CONFIG, ov)\n"
        "        metrics, yearly = _run_one(cfg, s, n_years, new_entrants_per_year,\n"
        "                                    pm, book_seed)\n"
        "        return i, ov, s, pm, metrics, yearly"),

    (
        "    rows, yearly_rows = [], []\n"
        "    for i, ov, s, metrics, yearly in out:\n"
        "        rows.append({'scenario': i, 'overrides': repr(ov) if ov else 'base',\n"
        "                     'seed': s, **metrics})\n"
        "        for year, lr in yearly.items():\n"
        "            yearly_rows.append({'scenario': i, 'seed': s, 'SIM_YEAR': int(year),\n"
        "                                'loss_ratio': lr})",
        "    rows, yearly_rows = [], []\n"
        "    for i, ov, s, pm, metrics, yearly in out:\n"
        "        rows.append({'scenario': i, 'pricing_model': pm,\n"
        "                     'overrides': repr(ov) if ov else 'base',\n"
        "                     'seed': s, **metrics})\n"
        "        for year, lr in yearly.items():\n"
        "            yearly_rows.append({'scenario': i, 'pricing_model': pm, 'seed': s,\n"
        "                                'SIM_YEAR': int(year), 'loss_ratio': lr})"),

    (
        "    summ = []\n"
        "    for i in range(len(overrides)):\n"
        "        g = metrics_df[metrics_df['scenario'] == i]\n"
        "        summ.append({\n"
        "            'scenario': i,\n"
        "            'overrides': g['overrides'].iloc[0],\n"
        "            'n_seeds': len(g),\n"
        "            'lr_mean': g['overall_lr'].mean(),\n"
        "            'lr_std': g['overall_lr'].std(),\n"
        "            'lr_p05': g['overall_lr'].quantile(0.05),\n"
        "            'lr_p50': g['overall_lr'].median(),\n"
        "            'lr_p95': g['overall_lr'].quantile(0.95),\n"
        "            'freq_mean': g['claim_freq'].mean(),\n"
        "            'premium_mean': g['avg_premium'].mean(),\n"
        "            'retention_mean': g['retention'].mean(),\n"
        "        })\n"
        "    summary_df = pd.DataFrame(summ)",
        "    summ = []\n"
        "    for i in range(len(overrides)):\n"
        "        for pm in pricing_models:\n"
        "            g = metrics_df[(metrics_df['scenario'] == i) &\n"
        "                           (metrics_df['pricing_model'] == pm)]\n"
        "            if len(g) == 0:\n"
        "                continue\n"
        "            summ.append({\n"
        "                'scenario': i,\n"
        "                'pricing_model': pm,\n"
        "                'overrides': g['overrides'].iloc[0],\n"
        "                'n_seeds': len(g),\n"
        "                'lr_mean': g['overall_lr'].mean(),\n"
        "                'lr_std': g['overall_lr'].std(),\n"
        "                'lr_p05': g['overall_lr'].quantile(0.05),\n"
        "                'lr_p50': g['overall_lr'].median(),\n"
        "                'lr_p95': g['overall_lr'].quantile(0.95),\n"
        "                'freq_mean': g['claim_freq'].mean(),\n"
        "                'premium_mean': g['avg_premium'].mean(),\n"
        "                'retention_mean': g['retention'].mean(),\n"
        "            })\n"
        "    summary_df = pd.DataFrame(summ)"),

    (
        "_demo_metrics, _demo_summary, _demo_yearly = run_monte_carlo(\n"
        "    overrides = [\n"
        "        None,\n"
        "        {'claim_frequency_base': -1.80}\n"
        "    ],\n"
        "    seeds = (0,1,2,3,4,5,6,7,8,9,10),\n"
        "    n_years = 5,\n"
        "    n_jobs = 5\n"
        ")",
        "_demo_metrics, _demo_summary, _demo_yearly = run_monte_carlo(\n"
        "    overrides = [\n"
        "        None,\n"
        "        {'claim_frequency_base': -1.80}\n"
        "    ],\n"
        "    seeds = (0,1,2,3,4),\n"
        "    n_years = 5,\n"
        "    n_jobs = 5,\n"
        "    pricing_models = ('tariff', 'glm', 'telem')\n"
        ")"),
])

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved monte-carlo patch')
