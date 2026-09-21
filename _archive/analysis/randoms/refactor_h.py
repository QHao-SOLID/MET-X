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


# Standalone EV TREND MARKET ANALYSIS cell: price re-simulated scenario book
patch('# EV TREND MARKET ANALYSIS - descriptive EV/ICE split + adoption scenarios', [
    (
        "    _sim = simulate_cohort(df, n_years=20, new_entrants_per_year=None,\n"
        "                           seed=42, cfg=_cfg, verbose=False)",
        "    _sim = simulate_cohort(df, n_years=20, new_entrants_per_year=None,\n"
        "                           seed=42, cfg=_cfg, verbose=False)\n"
        "    _sim = price_book(_sim, 'telem', _cfg)"),
])

# Report _sec_ev_analysis: price re-simulated scenario book
patch("                _sim = simulate_cohort(df0, n_years=20, new_entrants_per_year=None, seed=42, cfg=_cfg, verbose=False)", [
    (
        "                _sim = simulate_cohort(df0, n_years=20, new_entrants_per_year=None, seed=42, cfg=_cfg, verbose=False)",
        "                _sim = simulate_cohort(df0, n_years=20, new_entrants_per_year=None, seed=42, cfg=_cfg, verbose=False)\n"
        "                _sim = price_book(_sim, 'telem', _cfg)"),
])

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved scenario pricing fix')
