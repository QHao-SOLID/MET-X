import json, re

nb = json.load(open('main.ipynb', encoding='utf-8'))
cells = nb['cells']


def get(cid):
    for c in cells:
        if c['id'] == cid:
            return c
    raise KeyError(cid)


def block(text, start_re, end_re):
    lines = text.splitlines(keepends=True)
    si = next(i for i, l in enumerate(lines) if re.match(start_re, l))
    ei = next(i for i, l in enumerate(lines) if i > si and re.match(end_re, l))
    return ''.join(lines[si:ei]).strip('\n')


def norm(s):
    return s.strip('\n') + '\n\n'


src050 = ''.join(get('050b235c')['source'])
src2e9 = ''.join(get('2e942bfaa252')['source'])
srcsev = ''.join(get('claim-model-severity')['source'])

# 1. extract blocks verbatim from their defining cells
eng = block(src050, r'^ENGINE_CAPACITY_BANDS = \[', r'^COHORT_CONFIG = \{')
cfg = block(src050, r'^COHORT_CONFIG = \{', r'^DTYPE_DICT = \{')
dtd = block(src050, r'^DTYPE_DICT = \{', r'^def age_band')
dal = block(src2e9, r'^DRIVER_AGE_LOADING = \{', r'^def driver_age_loading')
pd = block(srcsev, r'^PERIL_DIST = \{', r'^PERIL_BASE = \{')
pb = block(srcsev, r'^PERIL_BASE = \{', r'^def sample_claim_peril')

assert 'Young Adults' in cfg and 'Seniors' in cfg
assert 'Adults' in dal and 'Seniors' in dal
assert 'TPFT' in pd and 'TPO' in pd
assert 'TPBI' in pb

# 2. new consolidated assumptions cell (inserted before 050b235c)
header = (
    '# ============================================================================\n'
    '# ALL MODELLING ASSUMPTIONS / CONFIG - single source of truth\n'
    '#   ENGINE_CAPACITY_BANDS : tariff engine bands\n'
    '#   COHORT_CONFIG         : cohort-generation assumptions\n'
    '#   DTYPE_DICT            : canonical column schema\n'
    '#   DRIVER_AGE_LOADING    : rating loading by driver band\n'
    '#   PERIL_DIST / PERIL_BASE : claim severity model constants\n'
    '# ============================================================================\n\n'
)
new_source = header + ''.join(norm(b) for b in (eng, cfg, dtd, dal, pd, pb))

idx = next(i for i, c in enumerate(cells) if c['id'] == '050b235c')
new_cell = {
    'id': 'config-assumptions',
    'cell_type': 'code',
    'execution_count': None,
    'metadata': {},
    'outputs': [],
    'source': new_source.splitlines(keepends=True),
}
cells.insert(idx, new_cell)
print('inserted config-assumptions before 050b235c')

# 3. strip duplicated definitions (keep logic only)
def rewrite(cid, new_src):
    c = get(cid)
    old = ''.join(c['source'])
    assert old != new_src, f'{cid}: no change'
    c['source'] = new_src.splitlines(keepends=True)
    c['outputs'] = []
    c['execution_count'] = None
    print('rewrote', cid)


# 050b235c: header (before ENGINE block) + everything after DTYPE_DICT
lines = src050.splitlines(keepends=True)
si_eng = next(i for i, l in enumerate(lines) if re.match(r'^ENGINE_CAPACITY_BANDS = \[', l))
ei_dtd = next(i for i, l in enumerate(lines) if i > si_eng and re.match(r'^DTYPE_DICT = \{', l))
ei_age = next(i for i, l in enumerate(lines) if i > ei_dtd and re.match(r'^def age_band', l))
keep = ''.join(lines[:si_eng]).rstrip('\n') + '\n\n' + ''.join(lines[ei_age:]).lstrip('\n')
rewrite('050b235c', keep)

# 2e942bfaa252: header comments + functions (drop DRIVER_AGE_LOADING literal)
lines = src2e9.splitlines(keepends=True)
si = next(i for i, l in enumerate(lines) if re.match(r'^DRIVER_AGE_LOADING = \{', l))
ei = next(i for i, l in enumerate(lines) if i > si and re.match(r'^def driver_age_loading', l))
keep = ''.join(lines[:si]).rstrip('\n') + '\n\n' + ''.join(lines[ei:]).lstrip('\n')
rewrite('2e942bfaa252', keep)

# claim-model-severity: header + functions + prints (drop PERIL_DIST / PERIL_BASE)
lines = srcsev.splitlines(keepends=True)
si = next(i for i, l in enumerate(lines) if re.match(r'^PERIL_DIST = \{', l))
ei = next(i for i, l in enumerate(lines) if i > si and re.match(r'^def sample_claim_peril', l))
keep = ''.join(lines[:si]).rstrip('\n') + '\n\n' + ''.join(lines[ei:]).lstrip('\n')
rewrite('claim-model-severity', keep)


# 4. config-lookup swaps (orphaned globals -> COHORT_CONFIG keys)
def rep(cid, old, new, expect=1):
    c = get(cid)
    s = ''.join(c['source'])
    n = s.count(old)
    assert n == expect, f'{cid}: found {n} of {old!r}, expected {expect}'
    c['source'] = s.replace(old, new).splitlines(keepends=True)
    c['outputs'] = []
    c['execution_count'] = None
    print(f'ok {cid}: {n}x {old!r}')


rep('cohort-simulation', 'year = COHORT_YEAR + year_offset',
    "year = COHORT_CONFIG['cohort_year'] + year_offset")
rep('cohort-simulation', 'lambda yrs: NCD_TABLE.get(min(yrs, 6), 0.55)',
    "lambda yrs: COHORT_CONFIG['ncd_table'].get(min(yrs, 6), 0.55)")
rep('validation-core', "results['SIM_YEAR'] == COHORT_YEAR",
    "results['SIM_YEAR'] == COHORT_CONFIG['cohort_year']")


# 5. post-edit verification: each constant defined exactly once, in config-assumptions
final = {c['id']: ''.join(c['source']) for c in cells}
for nm in ('COHORT_CONFIG', 'ENGINE_CAPACITY_BANDS', 'DTYPE_DICT',
           'DRIVER_AGE_LOADING', 'PERIL_DIST', 'PERIL_BASE'):
    defs = [cid for cid, s in final.items()
            if re.search(r'^' + nm + r'\s*=', s, re.M)]
    assert defs == ['config-assumptions'], f'{nm} defined in {defs}'
    print('defined once:', nm, '->', defs)
for nm in ('COHORT_YEAR + year_offset', 'NCD_TABLE.get', "SIM_YEAR'] == COHORT_YEAR"):
    assert not any(nm in s for s in final.values()), f'leftover {nm}'
print('no orphaned global refs')

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Saved')