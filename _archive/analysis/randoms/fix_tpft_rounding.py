import json

nb = json.load(open('main.ipynb', encoding='utf-8'))
for c in nb['cells']:
    if c['id'] == '403f8b5e':
        s = ''.join(c['source'])
        old = "        basic = 0.75 * comprehensive_basic(row)"
        new = "        basic = round(0.75 * comprehensive_basic(row) + 1e-9, 2)"
        assert s.count(old) == 1
        c['source'] = s.replace(old, new).splitlines(keepends=True)
        c['outputs'] = []
        c['execution_count'] = None
json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('epsilon fix applied')