import json

NB = 'main.ipynb'
BK = 'backups/main-20260817-183731.ipynb'
nb = json.load(open(NB, encoding='utf-8'))
bk = json.load(open(BK, encoding='utf-8'))
cells = nb['cells']

final_block = ''.join(bk['cells'][6]['source']).rstrip('\n') + '\n\n'

gen_cell = None
for c in cells:
    if 'def generate_dataset' in ''.join(c.get('source', [])):
        gen_cell = c
        break
if gen_cell is None:
    raise SystemExit('generate_dataset cell not found')
if 'def compute_final_premium' in ''.join(gen_cell['source']):
    raise SystemExit('compute_final_premium already present')
gen_cell['source'] = (final_block + ''.join(gen_cell['source'])).splitlines(keepends=True)
print('reinserted compute_final_premium into generate_dataset cell')
print('has SST_RATE:', any('SST_RATE' in ''.join(c['source']) for c in cells))

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved fix2')
