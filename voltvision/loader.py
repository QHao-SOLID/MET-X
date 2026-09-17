"""Method loader: calculation cells live in the 02x notebooks.

The pricing connector never implements math — it replays the tagged calc
cell of each method notebook so hub/03/desk/runner quote the exact same
functions the method owners edit. Tag convention: code cell metadata
tags ["calc", "<regime>"]. Already-registered regimes are skipped,
so calling ensure twice is harmless.
"""

import json
from pathlib import Path

# Core set: every full-set run expects these three to exist afterwards.
CORE_METHODS = {
    'tariff': '02a_tariff.ipynb',
    'glm': '02b_glm.ipynb',
    'telem': '02c_telem.ipynb',
}


def calc_source(nb_path, tag):
    # Pull the raw source of a notebook's calc cell without running anything.
    # Raises KeyError naming notebook + tag when the cell is absent/mistagged.
    j = json.loads(Path(nb_path).read_text(encoding='utf-8'))
    srcs = [''.join(c['source']) for c in j['cells']
            if c['cell_type'] == 'code'
            and 'calc' in c.get('metadata', {}).get('tags', [])
            and tag in c.get('metadata', {}).get('tags', [])]
    if not srcs:
        raise KeyError(f"no cell tagged ['calc', {tag!r}] in {nb_path}")
    return '\n'.join(srcs)


def ensure_methods(root=None, methods=None):
    # Exec each missing regime's calc cell; the cell registers itself.
    # Runs in a fresh namespace so notebook globals can't leak in —
    # the cell must be self-contained (its own imports).
    # Raises RuntimeError if a cell runs but forgets to register.
    from .pricing import PRICERS
    root = Path(root or '.')
    for name, nb in (methods or CORE_METHODS).items():
        if name in PRICERS:
            continue
        print(f"loader: {nb} -> regime '{name}'")
        src = calc_source(root / nb, name)
        exec(compile(src, nb, 'exec'), {'__name__': f'voltvision_method_{name}'})
        if name not in PRICERS:
            raise RuntimeError(f"{nb} calc cell did not register {name!r}")
    return PRICERS
