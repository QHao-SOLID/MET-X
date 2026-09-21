import nbformat
nb = nbformat.read('main.ipynb', as_version=4)
def src(c):
    return c.source if isinstance(c.source, str) else ''.join(c.source)
for idx in [17, 30, 36]:
    print('='*30, 'CELL', idx, '='*30)
    print(src(nb.cells[idx]))
    print()
