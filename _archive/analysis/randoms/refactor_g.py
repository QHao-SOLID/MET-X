import json

NB = 'main.ipynb'
nb = json.load(open(NB, encoding='utf-8'))

n = 0
for c in nb['cells']:
    src = c.get('source')
    if not isinstance(src, list):
        continue
    joined = ''.join(src)
    if 'TELEMATICS_SCORE' in joined:
        new_joined = joined.replace('TELEMATICS_SCORE', 'telematics_score')
        c['source'] = new_joined.splitlines(keepends=True)
        n += 1
        print('fixed cell with', joined.count('TELEMATICS_SCORE'), 'occurrences')

print('cells fixed:', n)
json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved case fix')
