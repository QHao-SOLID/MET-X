import nbformat

p = r'C:\Users\Admin\Documents\Visual Studio Code\Typst\IFoA_VoltVison\analysis\main.ipynb'
nb = nbformat.read(p, as_version=4)

def set_src(cell, text):
    cell.source = text

# ---- cell 17: add _require_simulated guard + call it in train_pricing ----
c17 = nb.cells[17]
s = c17.source if isinstance(c17.source, str) else ''.join(c17.source)

anchor1 = (
    "    return X\n"
    "\n"
    "\n"
    "def train_pricing(book, method='tariff', cfg=COHORT_CONFIG):"
)
guard_def = (
    "    return X\n"
    "\n"
    "\n"
    "def _require_simulated(book):\n"
    '    """Fail fast if the book was not produced by simulate_cohort().\n'
    "    Training/pricing must always run on a simulated book, never on raw inputs.\n"
    '    """\n'
    "    required = ['SIM_YEAR', 'COHORT_YEAR', 'POLID', 'CLAIM_COUNT', 'CLAIM_AMOUNT']\n"
    "    missing = [c for c in required if c not in book.columns]\n"
    "    if missing:\n"
    "        raise ValueError(\n"
    "            'train_pricing/price_book requires a SIMULATED book, but these columns '\n"
    "            f'are missing: {missing}. Run simulate_cohort() before pricing.')\n"
    "    if book['CLAIM_COUNT'].isnull().any() or book['CLAIM_AMOUNT'].isnull().any():\n"
    "        raise ValueError('book has null claim fields - run simulate_cohort() first.')\n"
    "\n"
    "\n"
    "def train_pricing(book, method='tariff', cfg=COHORT_CONFIG):"
)
assert anchor1 in s, 'anchor1 not found in cell 17'
s = s.replace(anchor1, guard_def, 1)

anchor2 = (
    "def train_pricing(book, method='tariff', cfg=COHORT_CONFIG):\n"
    '    """Fit a frequency model on entrant policy-years (no claim-history endogeneity).\n'
    "\n"
    "    Target = CLAIM_COUNT; severity priced separately from avg severity by coverage.\n"
    '    """\n'
    "    features = _pricing_features(method)"
)
anchor2_new = (
    "def train_pricing(book, method='tariff', cfg=COHORT_CONFIG):\n"
    '    """Fit a frequency model on entrant policy-years (no claim-history endogeneity).\n'
    "\n"
    "    Target = CLAIM_COUNT; severity priced separately from avg severity by coverage.\n"
    '    """\n'
    "    _require_simulated(book)\n"
    "    features = _pricing_features(method)"
)
assert anchor2 in s, 'anchor2 not found in cell 17'
s = s.replace(anchor2, anchor2_new, 1)
set_src(c17, s)
print('cell 17: guard added')

# ---- cell 30: remove dead _CAT_COLS + nested _encode_features ----
c30 = nb.cells[30]
s30 = c30.source if isinstance(c30.source, str) else ''.join(c30.source)
old30 = (
    "_CAT_COLS = ['VEHICLE_TYPE', 'COVERAGE_TYPE', 'REGION']\n"
    "\n"
    "\n"
    "def _encode_features(df, features):\n"
    "    X = df[features].copy()\n"
    "    for col in _CAT_COLS:\n"
    "        if col in features:\n"
    "            X[col] = X[col].astype('category').cat.codes\n"
    "    return X\n"
)
assert old30 in s30, 'old30 not found in cell 30'
s30 = s30.replace(old30, '', 1)
set_src(c30, s30)
print('cell 30: nested def removed')

# ---- cell 36: remove dead _CAT_COLS + nested _encode_features ----
c36 = nb.cells[36]
s36 = c36.source if isinstance(c36.source, str) else ''.join(c36.source)
old36 = (
    "    _CAT_COLS = ['VEHICLE_TYPE', 'COVERAGE_TYPE', 'REGION']\n"
    "\n"
    "    def _encode_features(df, features):\n"
    "        X = df[features].copy()\n"
    "        for col in _CAT_COLS:\n"
    "            if col in features:\n"
    "                X[col] = X[col].astype('category').cat.codes\n"
    "        return X\n"
)
assert old36 in s36, 'old36 not found in cell 36'
s36 = s36.replace(old36, '', 1)
set_src(c36, s36)
print('cell 36: nested def removed')

nbformat.write(nb, p)
print('SAVED')
