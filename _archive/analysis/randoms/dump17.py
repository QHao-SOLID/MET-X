import nbformat
nb = nbformat.read('main.ipynb', as_version=4)
def src(c):
    return c.source if isinstance(c.source, str) else ''.join(c.source)
s = src(nb.cells[17])
# print lines mentioning _encode_features or _CAT_COLS or train_pricing or price_book def
for j, ln in enumerate(s.split('\n')):
    if any(k in ln for k in ['_encode_features', '_CAT_COLS', 'def train_pricing', 'def price_book', 'def _retained_lr', 'features']):
        print(j, ln)
