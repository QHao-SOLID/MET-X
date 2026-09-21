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


rep('ed52012d',
    '"NCD_LEVEL": "int64",',
    '"NCD_LEVEL": "float64",')

rep('validation-core',
    "car_age_med = results['CAR_AGE'].median()",
    "# Fleet age at inception (year-1 policies), not the aged 20-yr book\n"
    "car_age_med = results.loc[results['SIM_YEAR'] == COHORT_YEAR, 'CAR_AGE'].median()")

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Saved')