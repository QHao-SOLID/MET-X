# Getting started

## Install

```bash
pip install numpy pandas matplotlib seaborn scipy scikit-learn openpyxl
pip install shap                                                   # analysis §11 only
pip install mkdocs-material                                        # docs only
```

Python 3.10+. No other setup — assumptions and scenarios are JSON.

## Run the simulator

All commands run from the project folder:

```bash
cd simulation

python run_scenarios.py                        # full sweep: every group x seeds.json
python run_scenarios.py --quick                # smoke: n=1000, 2 years
python run_scenarios.py --scenarios base       # one scenario
python run_scenarios.py --seeds 0,1,2          # override seeds.json
python run_scenarios.py --csv                  # also write CSV beside each pkl
python run_scenarios.py --excel base_s42       # xlsx from an existing result
```

Each run writes **one combined file per scenario × seed**:

```
shared/results/base_s42.pkl        # sim columns + PREM_tariff / PREM_glm / PREM_telem
shared/results/manifest.json       # cfg + cards snapshot and per-regime metrics
```

## Read a result

```python
from voltvision import io

combined = io.load_result('base', 42)
raw = io.sim_book(combined)             # attributes + claims
books = io.books_from_result(combined)  # {regime: book with FINAL_PREMIUM_SST}
```

Or open `analysis.ipynb` — the loader cell picks `('base', 67)` if present,
otherwise the newest run in the manifest, and every section loops whatever
`PREM_*` columns the file contains.

## Notebooks and methods

| File | Purpose |
|---|---|
| `pricing_desk.ipynb` | pricing desk: resolve cards, quote, compare, what-if, add-a-method demo |
| `analysis.ipynb` | full analysis on one result (+ §10 realism vs benchmarks) |
| `voltvision/methods/tariff.py` / `glm.py` / `telem.py` | the pricing methods — each owns its rate card and premium math |

## Start the docs site

```bash
mkdocs serve      # from the repo root
```
