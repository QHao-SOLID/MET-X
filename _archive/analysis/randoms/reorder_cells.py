import json, uuid

NB = 'main.ipynb'
nb = json.load(open(NB, encoding='utf-8'))
cells = nb['cells']


def find(anchor):
    hits = [c for c in cells if anchor in ''.join(c.get('source', []))]
    if len(hits) != 1:
        raise SystemExit(f'anchor {anchor!r} matched {len(hits)} cells')
    return hits[0]


# ---- unique anchors -> existing cells ----
A = {
    'imports': 'import os, shutil',
    'ctx': 'bengkelbergerak.my',
    'config': 'COHORT_CONFIG = {',
    'ageband': 'def age_band(age):',
    'driverload': 'Youngsters highest',
    'gen': 'df = generate_dataset(',
    'freq': 'lambda = exp(log_lambda)',
    'sev': 'Peril mix follows',
    'ret': 'def compute_retention_probability',
    'vec': '# VECTORIZED SIMULATION HELPERS',
    'engine': '# PREMIUM PRICING ENGINE',
    'pricehelp': 'def compare_pricing',
    'sim': 'def simulate_cohort',
    'mc': '# MONTE CARLO API',
    'analyze': 'def analyze_cohort',
    'sample': 'def generate_sample_claims',
    'validA': '# Statistical Validation (Part A: Core Tests)',
    'validB': '# Statistical Validation (Part B)',
    'traj': 'def plot_policy_trajectories',
    'overvalid': '# OVERTHINKER-STYLE VALIDATION',
    'ev': '# EV TREND MARKET ANALYSIS',
    'mdprog': 'Pricing Model Progression: Tariff',
    'prog': '# PRICING PROGRESSION RUN',
    'overeda': '# OVERTHINKER-STYLE EDA',
    'export': '# EXPORT SIMULATION DATA TO CSV',
    'mdreport': 'This cell runs the full report generation',
    'report': '# CONSOLIDATED ACTUARIAL REPORT - data-driven',
}
located = {k: find(v) for k, v in A.items()}


# ---- Edit A: split simulate_cohort cell into def (12a) + extracted main run (12b) ----
sim = located['sim']
sim_src = ''.join(sim['source'])
marker = '# Run simulation (single trajectory'
i = sim_src.rfind(marker)
if i < 0:
    raise SystemExit('sim main-run marker not found')
def_part = sim_src[:i].rstrip('\n') + '\n'
main_part = sim_src[i:].lstrip('\n')
if 'cohort_results = simulate_cohort(' not in main_part:
    raise SystemExit('main_part missing sim call')
sim['source'] = def_part.splitlines(keepends=True)
mainrun = {
    'cell_type': 'code', 'execution_count': None, 'metadata': {},
    'outputs': [], 'id': uuid.uuid4().hex[:8],
    'source': main_part.splitlines(keepends=True),
}


# ---- Edit B: de-dup progression run (reuse baseline book, no re-simulation) ----
prog = located['prog']
prog_src = ''.join(prog['source'])
old = ("# --- ONE simulation (premium-independent), then re-price under 3 regimes ---\n"
       "cohort_results = simulate_cohort(\n"
       "    df, n_years=5, new_entrants_per_year=None, seed=42)\n"
       "\n"
       "cohort_results_tariff = price_book(cohort_results, 'tariff', COHORT_CONFIG)")
new = ("# Re-price the single baseline book (Ch.6 Baseline Run) under three regimes.\n"
       "# No re-simulation: only pricing differs (same policies, same claims).\n"
       "cohort_results_tariff = price_book(cohort_results, 'tariff', COHORT_CONFIG)")
if prog_src.count(old) != 1:
    raise SystemExit(f'prog sim block matched {prog_src.count(old)}')
prog_src = prog_src.replace(old, new)
prog['source'] = prog_src.splitlines(keepends=True)


# ---- markdown headers ----
def md(text):
    return {'cell_type': 'markdown', 'metadata': {},
            'id': uuid.uuid4().hex[:8], 'source': text.splitlines(keepends=True)}


TITLE = """# VoltVision Motor Portfolio - Simulation, Pricing & Actuarial Report

**Objective.** A premium-independent cohort simulation (claims & retention driven by
experience + telematics, *not* by premium) plus a hot-swappable pricing engine
(tariff -> GLM -> GLM+Telematics) so pricing can be swapped without re-simulation.

**How to read.** Chapters 1-6 build the machinery and run one baseline book. Chapter 7 is
the long analysis report (validation -> EDA -> EV -> pricing progression). Chapter 8 is the
Monte Carlo stress test. Chapter 9 exports data and writes `report/actuarial_report.md`."""

CH1 = ("## 1 - Configuration & Assumptions\n\n"
       "All portfolio assumptions live in `COHORT_CONFIG` (vehicle bands, loadings, NCD table, "
       "expense / telematics loadings).")
CH2 = ("## 2 - Initial Portfolio\n\n"
       "Generate the starting book of policies from `COHORT_CONFIG` (single deterministic call, seed 42).")
CH3 = ("## 3 - Risk Models - claims & retention (premium-independent)\n\n"
       "Claim frequency (Poisson), claim severity (per-peril Gamma), and retention (driver A: experience + "
       "telematics only). None of these touch premium.")
CH4 = ("## 4 - Simulation Engine\n\n"
       "Vectorized, config-threaded cohort evolution. `simulate_cohort` ages the book, applies loadings / NCD, "
       "and emits *labels only* (no premium).")
CH5 = ("## 5 - Pricing Engine (hot-swappable)\n\n"
       "`price_book(book, method)` places premium post-simulation via the registry: `tariff` (rule-based), "
       "`glm` (traditional factors), `telem` (adds `telematics_score`). `compare_pricing` summarises all three.")
CH6 = ("## 6 - Baseline Run\n\n"
       "One trajectory, priced with the primary `telem` regime. This `cohort_results` book feeds every downstream analysis.")
CH7 = ("## 7 - Analysis Report\n\n"
       "Validation, exploratory analysis, EV market analysis, and the tariff -> GLM -> telem pricing progression - "
       "run consecutively as one continuous report.")
CH8 = ("## 8 - Monte Carlo Stress Test\n\n"
       "Scenario x seed x pricing-model grid (`run_monte_carlo`) for uncertainty around the baseline.")
CH9 = ("## 9 - Export & Consolidated Report\n\n"
       "Persist the simulated book to `data/`, then render the full `actuarial_report.md` (re-derived from the priced book).")


# ---- new order ----
order = [
    ('md', TITLE),
    ('cell', 'imports'),
    ('cell', 'ctx'),
    ('md', CH1),
    ('cell', 'config'),
    ('cell', 'ageband'),
    ('cell', 'driverload'),
    ('md', CH2),
    ('cell', 'gen'),
    ('md', CH3),
    ('cell', 'freq'),
    ('cell', 'sev'),
    ('cell', 'ret'),
    ('md', CH4),
    ('cell', 'vec'),
    ('cell', 'sim'),
    ('md', CH5),
    ('cell', 'engine'),
    ('cell', 'pricehelp'),
    ('md', CH6),
    ('mainrun',),
    ('md', CH7),
    ('cell', 'sample'),
    ('cell', 'validA'),
    ('cell', 'validB'),
    ('cell', 'overvalid'),
    ('cell', 'analyze'),
    ('cell', 'traj'),
    ('cell', 'overeda'),
    ('cell', 'ev'),
    ('cell', 'mdprog'),
    ('cell', 'prog'),
    ('md', CH8),
    ('cell', 'mc'),
    ('md', CH9),
    ('cell', 'export'),
    ('cell', 'mdreport'),
    ('cell', 'report'),
]

new_cells = []
for entry in order:
    if entry[0] == 'md':
        new_cells.append(md(entry[1]))
    elif entry[0] == 'mainrun':
        new_cells.append(mainrun)
    else:
        new_cells.append(located[entry[1]])

if len(new_cells) != 38:
    raise SystemExit(f'expected 38 cells, got {len(new_cells)}')
nb['cells'] = new_cells
json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('reordered -> 38 cells; split sim def/main-run; de-duped progression run')
