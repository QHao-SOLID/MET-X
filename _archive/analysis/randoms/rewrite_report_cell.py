import json
import os

NB = 'main.ipynb'
SRC = r'C:\Users\Admin\AppData\Local\Temp\opencode\report_cell_source.txt'

nb = json.load(open(NB, encoding='utf-8'))

with open(SRC, encoding='utf-8') as fh:
    code_source = fh.read().splitlines(keepends=True)

md_source = (
    '# Consolidated Actuarial Report\n'
    '\n'
    'This cell runs the full report generation **data-driven**: '
    '`generate_actuarial_report(cohort_results, config)` consumes the single '
    'tariff book produced by the simulation and derives every section from it - '
    'cohort summary, validation (core + reproducibility + enhanced), EDA, EV '
    'analysis, and pricing progression. Pricing is re-derived row-by-row from '
    'the same book (GLM and GLM+Telematics premium columns computed on the '
    '`cohort_results` frame - **no re-simulation**), so the pricing-progression '
    'metrics and the validation metrics describe the **same book**.\n'
    '\n'
    'Sections:\n'
    '1. Cohort Summary\n'
    '2. Validation - Core Tests\n'
    '3. Validation - Reproducibility + EDA Enrichment\n'
    '4. Validation - Enhanced Tests\n'
    '5. EDA - Policy Trajectories\n'
    '6. EDA - Actuarial Heatmaps\n'
    '7. EV Market Analysis\n'
    '8. Pricing Progression (Tariff -> GLM -> GLM+Telematics)\n'
    '9. Risk-Based Pricing - premium by behavior tier\n'
    '\n'
    'Outputs: `report/actuarial_report.md` + figures in `report/figures/`.\n'
    '\n'
    'Sub-sections that inherently need re-simulation (reproducibility, EV '
    'adoption scenarios) use the initial cohort `df` when available and skip '
    'gracefully otherwise.\n'
    '\n'
    'Run this cell **after** the simulation cell (needs `cohort_results`, '
    '`COHORT_CONFIG`).'
).splitlines(keepends=True)

found = {'generate-report-run': False, 'generate-report-md': False}
for c in nb['cells']:
    if c.get('id') == 'generate-report-run':
        c['source'] = code_source
        found['generate-report-run'] = True
    elif c.get('id') == 'generate-report-md':
        c['source'] = md_source
        found['generate-report-md'] = True

if not all(found.values()):
    raise SystemExit(f'cells not found: {[k for k, v in found.items() if not v]}')

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(f'Replaced report cells. Total cells: {len(nb["cells"])}')
