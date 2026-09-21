import json

nb = json.load(open('main.ipynb', encoding='utf-8'))


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


# Fixed engine-capacity mix (replaces random exponential weights)
rep('050b235c',
    '    engine_exp_lambda: float = 1.0\n'
    '    engine_seed: int = 42\n'
    '    seed: int = 42',
    '    engine_weights: list = field(default_factory=lambda: [0.25, 0.20, 0.18, 0.15, 0.10, 0.07, 0.03, 0.02])\n'
    '    seed: int = 42')

rep('050b235c',
    '''    # Engine capacity: fixed exponential-weighted mix (own rng, as before)
    ew_rng = np.random.default_rng(cfg.engine_seed)
    exp_vals = np.sort(ew_rng.exponential(1 / cfg.engine_exp_lambda, len(ENGINE_CAPACITY_BANDS)))[::-1]
    df['ENGINE_CAPACITY'] = rng.choice(ENGINE_CAPACITY_BANDS, size=n,
                                       p=exp_vals / exp_vals.sum())''',
    '''    # Engine capacity: fixed hand-set mix (small cars dominant)
    df['ENGINE_CAPACITY'] = rng.choice(ENGINE_CAPACITY_BANDS, size=n,
                                       p=_p(cfg.engine_weights))''')

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Saved')