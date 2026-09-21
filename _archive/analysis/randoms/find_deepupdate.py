t = open('backups/main-20260817-183731.ipynb', encoding='utf-8').read()
i = t.find('def deep_update')
seg = t[i-20:i+700]
print('=== DEF SEGMENT ===')
print(seg)
print('=== import copy present? ===', 'import copy' in t)
