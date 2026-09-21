import nbformat
nb = nbformat.read('main.ipynb', as_version=4)

def src(c):
    return c.source if isinstance(c.source, str) else ''.join(c.source)

for idx, c in enumerate(nb.cells):
    if c.cell_type != 'code':
        continue
    s = src(c)
    has_sim = 'simulate_cohort(' in s
    has_price = ('price_book(' in s) or ('train_pricing(' in s)
    if has_sim or has_price:
        # print lines in order they appear
        order = []
        for ln in s.split('\n'):
            if 'simulate_cohort(' in ln:
                order.append('SIM')
            if 'price_book(' in ln:
                order.append('PRICE')
            if 'train_pricing(' in ln and 'def train_pricing' not in ln:
                order.append('TRAIN')
        print(f'cell {idx}: sim={has_sim} price={has_price} -> order: {order}')
