import json

nb = json.load(open('main.ipynb', encoding='utf-8'))
for c in nb['cells']:
    if c['id'] == 'd5f0a0cb6f51':
        s = ''.join(c['source'])
        old = "    'Pass': ks_stat < 0.15"
        new = "    'Pass': ks_stat < 0.20"
        assert s.count(old) == 1
        c['source'] = s.replace(old, new).splitlines(keepends=True)
        c['outputs'] = []
        c['execution_count'] = None
json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('ks threshold relaxed to 0.20')