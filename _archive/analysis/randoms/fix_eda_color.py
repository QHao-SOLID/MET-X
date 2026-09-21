import json

nb = json.load(open('main.ipynb', encoding='utf-8'))
for c in nb['cells']:
    if c['id'] == '7f02ad04a87b':
        s = ''.join(c['source'])
        old = "color=['skyblue', 'coral'][i]"
        new = "color=['skyblue', 'coral', 'seagreen'][i]"
        assert s.count(old) == 1
        c['source'] = s.replace(old, new).splitlines(keepends=True)
        c['outputs'] = []
        c['execution_count'] = None
json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('color fix applied')