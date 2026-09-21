import nbformat

p = r'C:\Users\Admin\Documents\Visual Studio Code\Typst\IFoA_VoltVison\analysis\main.ipynb'
nb = nbformat.read(p, as_version=4)

def_src = (
    "\n"
    "def deep_update(base, overrides):\n"
    '    """Deep-copy base and recursively merge overrides (None-safe)."""\n'
    "    out = copy.deepcopy(base)\n"
    "    if not overrides:\n"
    "        return out\n"
    "    for k, v in overrides.items():\n"
    "        if isinstance(v, dict) and isinstance(out.get(k), dict):\n"
    "            out[k] = deep_update(out[k], v)\n"
    "        else:\n"
    "            out[k] = v\n"
    "    return out\n"
)

# remove from markdown cell 0 if present
m0 = nb.cells[0].source
if isinstance(m0, list):
    m0 = ''.join(m0)
if 'def deep_update' in m0:
    m0 = m0.replace(def_src, '')
    nb.cells[0].source = m0
    print('removed from cell0 markdown')

# add to imports code cell 1
c1 = nb.cells[1].source
if isinstance(c1, list):
    c1 = ''.join(c1)
if 'def deep_update' not in c1:
    nb.cells[1].source = c1 + def_src
    print('added to cell1 imports')
else:
    print('already in cell1')

nbformat.write(nb, p)
print('done')
