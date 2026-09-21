import json
import uuid

nb = json.load(open('main.ipynb', encoding='utf-8'))

export_cell = r'''# ============================================================================
# EXPORT SIMULATION DATA TO CSV (data/)
# Reproducible: deterministic (seed 42), regenerated on every execution
# ============================================================================
import os, shutil

os.makedirs('data', exist_ok=True)

cohort_results.to_csv('data/simulation_cohort_results.csv', index=False)
df.to_csv('data/initial_book.csv', index=False)
shutil.copy('./sources/rates.csv', 'data/rates.csv')

params = pd.DataFrame([
    {'PARAMETER': 'NCD_TABLE',           'VALUE': repr(NCD_TABLE)},
    {'PARAMETER': 'DRIVER_AGE_LOADING',  'VALUE': repr(DRIVER_AGE_LOADING)},
    {'PARAMETER': 'CAR_AGE_LOADING',     'VALUE': '1 + 0.03 * min(car_age, 10)'},
    {'PARAMETER': 'SST_RATE',            'VALUE': repr(SST_RATE)},
    {'PARAMETER': 'RISK_LOADING_FLOOD',  'VALUE': '1.10'},
    {'PARAMETER': 'RISK_LOADING_THEFT',  'VALUE': '1.10'},
    {'PARAMETER': 'PERIL_DIST',          'VALUE': repr(PERIL_DIST)},
    {'PARAMETER': 'PERIL_BASE',          'VALUE': repr(PERIL_BASE)},
    {'PARAMETER': 'NCD_ENTRY_YEARS',     'VALUE': repr(NCD_ENTRY_YEARS)},
    {'PARAMETER': 'NCD_ENTRY_WEIGHTS',   'VALUE': repr(NCD_ENTRY_WEIGHTS)},
    {'PARAMETER': 'CLAIM_LAMBDA_BASE',   'VALUE': '-2.00 (log rate)'},
    {'PARAMETER': 'TPO_FREQ_MULTIPLIER', 'VALUE': '0.45'},
    {'PARAMETER': 'COHORT_YEAR',         'VALUE': repr(COHORT_YEAR)},
    {'PARAMETER': 'NUM_DATASET',         'VALUE': repr(num_dataset)},
    {'PARAMETER': 'SIM_YEARS',           'VALUE': repr(sorted(cohort_results['SIM_YEAR'].unique()))},
    {'PARAMETER': 'SEED',                'VALUE': '42'},
    {'PARAMETER': 'AGING_CAP_CAR_AGE',   'VALUE': '10'},
])
params.to_csv('data/model_parameters.csv', index=False)

print('Exports written to data/:')
for f in sorted(os.listdir('data')):
    p = os.path.join('data', f)
    print(f'  {f:38s} {os.path.getsize(p):>12,} bytes')
print(f'cohort_results: {len(cohort_results):,} rows x {cohort_results.shape[1]} cols')
print(f'initial book  : {len(df):,} rows x {df.shape[1]} cols')'''

cell = {
    'cell_type': 'code',
    'execution_count': None,
    'metadata': {},
    'outputs': [],
    'source': export_cell.splitlines(keepends=True),
    'id': 'export-data',
}

for c in nb['cells']:
    if c.get('id') == 'export-data':
        raise SystemExit('export-data cell already exists')

nb['cells'].append(cell)

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Appended export cell. Total cells:', len(nb['cells']))