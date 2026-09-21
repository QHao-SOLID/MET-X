import json

NB = 'main.ipynb'
BK = 'backups/main-20260817-183731.ipynb'

nb = json.load(open(NB, encoding='utf-8'))
bk = json.load(open(BK, encoding='utf-8'))
cells = nb['cells']

# --- recover premium block from backup cell 4 (BASIC PREMIUM + calculate_premium) ---
premium_block = ''.join(bk['cells'][4]['source']).rstrip('\n') + '\n\n'

# --- insert into the generate_dataset cell (anchor: def generate_dataset) ---
gen_cell = None
for c in cells:
    if 'def generate_dataset' in ''.join(c.get('source', [])):
        gen_cell = c
        break
if gen_cell is None:
    raise SystemExit('generate_dataset cell not found')
if 'def calculate_premium' in ''.join(gen_cell['source']):
    raise SystemExit('calculate_premium already present')
gen_cell['source'] = (premium_block + ''.join(gen_cell['source'])).splitlines(keepends=True)
print('reinserted calculate_premium into generate_dataset cell')

# --- dedupe identical cells (the duplicate pricing-engine cell) ---
seen = {}
kept = []
removed = 0
for c in cells:
    key = ''.join(c.get('source', []))
    if c.get('cell_type') == 'code' and key in seen:
        removed += 1
        continue
    seen[key] = True
    kept.append(c)
nb['cells'] = kept
print(f'deduped {removed} identical cell(s); cells now {len(kept)}')

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved fix')
