import json

nb = json.load(open('main.ipynb', encoding='utf-8'))


def get(cid):
    for c in nb['cells']:
        if c['id'] == cid:
            return c
    raise KeyError(cid)


def rep(cid, old, new, expect=1):
    c = get(cid)
    s = ''.join(c['source'])
    n = s.count(old)
    assert n == expect, f"{cid}: found {n} of {old[:60]!r}, expected {expect}"
    c['source'] = s.replace(old, new).splitlines(keepends=True)
    c['outputs'] = []
    c['execution_count'] = None
    print(f'ok {cid}: {n}x {old[:55]!r}')


def set_source(cid, src):
    c = get(cid)
    c['source'] = src.splitlines(keepends=True)
    c['outputs'] = []
    c['execution_count'] = None
    print(f'ok {cid}: full rewrite ({len(src)} chars)')


# 1. Coverage mix -> 3 types
rep('b2bc12b6',
    'comprehensive_pct = 0.80\ntpo_pct = 0.20',
    'comprehensive_pct = 0.65\ntpft_pct = 0.20\ntpo_pct = 0.15')

rep('b2bc12b6',
    '''df["COVERAGE_TYPE"] = random.choices(
    ["Comprehensive", "TPO"],
    weights = (comprehensive_pct, tpo_pct),
    k = num_dataset
)''',
    '''df["COVERAGE_TYPE"] = random.choices(
    ["Comprehensive", "TPFT", "TPO"],
    weights = (comprehensive_pct, tpft_pct, tpo_pct),
    k = num_dataset
)''')

# 2. calculate_premium -> graduated Motor Tariff 2015 + TPFT = 0.75 x Comp
set_source('403f8b5e', r'''# ============================================================================
# BASIC PREMIUM - Schedule of Motor Tariff 2015 (Form 5 Mathematics Ch.3)
# Graduated tariff:
#   Comprehensive = first-RM1,000 rate + PER_EXTRA x ceil((SA-1000)/1000)
#   TPFT (Third Party, Fire & Theft) = 0.75 x Comprehensive basic (Example 3)
#   TPO = flat tariff rate (no sum-assured scaling)
# ============================================================================

PER_EXTRA = {
    'Peninsular Malaysia': 26.00,
    'East Malaysia (Sabah, Sawarak & Labuan)': 20.30,
}

MOTOR_TARIFF = {
    'Peninsular Malaysia': {
        'Comprehensive': {
            '0 to 1,400 cc / EV up to 70 kW': 273.80,
            '1,401 to 1,650 cc / EV 71 - 100 kW': 305.50,
            '1,651 - 2,200 cc / EV 101 - 125 kW': 339.10,
            '2,201 - 3,050 cc / EV 126 - 150 kW': 372.60,
            '3,051 - 4,100 cc / EV 151 - 200 kW': 404.30,
            '4,101 - 4,250 cc / EV 201 - 250 kW': 436.00,
            '4,251 - 4,400 cc / EV 251 - 300 kW': 469.60,
            'Over 4,400 cc / EV > 300 kW': 501.30,
        },
        'TPO': {
            '0 to 1,400 cc / EV up to 70 kW': 120.60,
            '1,401 to 1,650 cc / EV 71 - 100 kW': 135.00,
            '1,651 - 2,200 cc / EV 101 - 125 kW': 151.20,
            '2,201 - 3,050 cc / EV 126 - 150 kW': 167.40,
            '3,051 - 4,100 cc / EV 151 - 200 kW': 181.80,
            '4,101 - 4,250 cc / EV 201 - 250 kW': 196.20,
            '4,251 - 4,400 cc / EV 251 - 300 kW': 212.40,
            'Over 4,400 cc / EV > 300 kW': 226.80,
        },
    },
    'East Malaysia (Sabah, Sawarak & Labuan)': {
        'Comprehensive': {
            '0 to 1,400 cc / EV up to 70 kW': 196.20,
            '1,401 to 1,650 cc / EV 71 - 100 kW': 220.00,
            '1,651 - 2,200 cc / EV 101 - 125 kW': 243.90,
            '2,201 - 3,050 cc / EV 126 - 150 kW': 266.50,
            '3,051 - 4,100 cc / EV 151 - 200 kW': 290.40,
            '4,101 - 4,250 cc / EV 201 - 250 kW': 313.00,
            '4,251 - 4,400 cc / EV 251 - 300 kW': 336.90,
            'Over 4,400 cc / EV > 300 kW': 359.50,
        },
        'TPO': {
            '0 to 1,400 cc / EV up to 70 kW': 67.50,
            '1,401 to 1,650 cc / EV 71 - 100 kW': 75.60,
            '1,651 - 2,200 cc / EV 101 - 125 kW': 85.20,
            '2,201 - 3,050 cc / EV 126 - 150 kW': 93.60,
            '3,051 - 4,100 cc / EV 151 - 200 kW': 101.70,
            '4,101 - 4,250 cc / EV 201 - 250 kW': 110.10,
            '4,251 - 4,400 cc / EV 251 - 300 kW': 118.20,
            'Over 4,400 cc / EV > 300 kW': 126.60,
        },
    },
}


def comprehensive_basic(row):
    first = MOTOR_TARIFF[row['REGION']]['Comprehensive'][row['ENGINE_CAPACITY']]
    units = int(np.ceil(max(0.0, (row['SUM_ASSURED'] - 1000.0) / 1000.0)))
    return first + PER_EXTRA[row['REGION']] * units


def calculate_premium(row):
    """Basic premium per Schedule of Motor Tariff 2015 (graduated)."""
    coverage = row['COVERAGE_TYPE']
    if coverage == 'Comprehensive':
        basic = comprehensive_basic(row)
    elif coverage == 'TPFT':
        basic = 0.75 * comprehensive_basic(row)
    else:  # TPO - flat tariff rate
        basic = MOTOR_TARIFF[row['REGION']]['TPO'][row['ENGINE_CAPACITY']]
    return round(float(basic), 2)


# Textbook cross-check (Form 5 Example 3: Peninsular, 1,650cc band, SA 60,000)
def _mk(cov):
    return pd.Series({'COVERAGE_TYPE': cov, 'REGION': 'Peninsular Malaysia',
                      'ENGINE_CAPACITY': '1,401 to 1,650 cc / EV 71 - 100 kW',
                      'SUM_ASSURED': 60000.0})


assert abs(calculate_premium(_mk('Comprehensive')) - 1839.50) < 0.01
assert abs(calculate_premium(_mk('TPFT')) - 1379.63) < 0.01
assert abs(calculate_premium(_mk('TPO')) - 135.00) < 0.01
print('Tariff check OK (Form 5 Ex.3): Comp RM1,839.50 | TPFT RM1,379.63 | TPO RM135.00')

df["BASIC_PREMIUM"] = df.apply(calculate_premium, axis=1)
print(f"Avg basic premium: RM{df['BASIC_PREMIUM'].mean():.2f}")''')

# 3. Claim frequency multiplier for TPFT (0.60: between TPO 0.45 and Comp 1.00)
rep('claim-model-lambda',
    "    mult = 0.45 if row['COVERAGE_TYPE'] == 'TPO' else 1.00",
    "    # Coverage multiplier: TPO no own-damage; TPFT fire/theft only (0.60)\n"
    "    mult = 0.45 if row['COVERAGE_TYPE'] == 'TPO' else (0.60 if row['COVERAGE_TYPE'] == 'TPFT' else 1.00)")

rep('claim-model-lambda',
    "print(f\"Comp mean lambda: {df.loc[df['COVERAGE_TYPE']=='Comprehensive', 'CLAIM_LAMBDA'].mean():.4f}\")",
    "print(f\"Comp mean lambda: {df.loc[df['COVERAGE_TYPE']=='Comprehensive', 'CLAIM_LAMBDA'].mean():.4f}\")\n"
    "print(f\"TPFT mean lambda: {df.loc[df['COVERAGE_TYPE']=='TPFT', 'CLAIM_LAMBDA'].mean():.4f}\")")

# 4. Severity: TPFT perils (TPPD/TPBI/Theft/Fire, no AD/Windscreen)
rep('claim-model-severity',
    "    'TPO': {\n"
    "        'TPPD': 0.78, 'TPBI': 0.22\n"
    "    }\n"
    "}",
    "    'TPO': {\n"
    "        'TPPD': 0.78, 'TPBI': 0.22\n"
    "    },\n"
    "    'TPFT': {\n"
    "        'TPPD': 0.444, 'TPBI': 0.111,\n"
    "        'Theft': 0.296, 'Fire': 0.148\n"
    "    }\n"
    "}")

rep('claim-model-severity',
    "print('  TPO perils:          ', list(PERIL_DIST['TPO'].keys()))",
    "print('  TPO perils:          ', list(PERIL_DIST['TPO'].keys()))\n"
    "print('  TPFT perils:         ', list(PERIL_DIST['TPFT'].keys()))")

# 5. Overthinker validation: include TPFT in loops, targets + new checks
rep('d5f0a0cb6f51',
    "for cov_type in ['Comprehensive', 'TPO']:",
    "for cov_type in ['Comprehensive', 'TPFT', 'TPO']:")

rep('d5f0a0cb6f51',
    "for cov in ['Comprehensive', 'TPO']:",
    "for cov in ['Comprehensive', 'TPFT', 'TPO']:")

rep('d5f0a0cb6f51',
    "    'TPO': {'mean': (8000, 30000), 'p95': (25000, 600000)}\n}",
    "    'TPO': {'mean': (8000, 30000), 'p95': (25000, 600000)},\n"
    "    'TPFT': {'mean': (5000, 15000), 'p95': (20000, 120000)}\n}")

rep('d5f0a0cb6f51',
    "    'Pass': comp_ratio > 1.8\n})",
    "    'Pass': comp_ratio > 1.8\n})\n\n"
    "# 7b. TPFT premium between TPO and Comprehensive\n"
    "tpft_avg = final_dataset[final_dataset['COVERAGE_TYPE'] == 'TPFT']['FINAL_PREMIUM_SST'].mean()\n"
    "validation_results.append({\n"
    "    'Test': 'TPFT Premium between TPO & Comp',\n"
    "    'Value': f\"RM{tpo_avg:,.0f} < RM{tpft_avg:,.0f} < RM{comp_avg:,.0f}\",\n"
    "    'Expected': 'TPO < TPFT < Comprehensive',\n"
    "    'Pass': tpo_avg < tpft_avg < comp_avg\n"
    "})")

rep('d5f0a0cb6f51',
    "enhanced_results.append({'Test': 'NCD Reset on Claim', 'Statistic': f\"{ncd_reset_failures}/{total_claims_checked} failures\", 'P-value': '-', 'Interpretation': 'Claim in year N -> NCD 0 next year', 'Pass': ncd_ok})",
    "enhanced_results.append({'Test': 'NCD Reset on Claim', 'Statistic': f\"{ncd_reset_failures}/{total_claims_checked} failures\", 'P-value': '-', 'Interpretation': 'Claim in year N -> NCD 0 next year', 'Pass': ncd_ok})\n\n"
    "# 7b. TPFT claim frequency between TPO and Comprehensive\n"
    "comp_freq_c = final_dataset[final_dataset['COVERAGE_TYPE'] == 'Comprehensive']['CLAIM_OCCURRED'].mean()\n"
    "tpo_freq_c = final_dataset[final_dataset['COVERAGE_TYPE'] == 'TPO']['CLAIM_OCCURRED'].mean()\n"
    "tpft_freq_c = final_dataset[final_dataset['COVERAGE_TYPE'] == 'TPFT']['CLAIM_OCCURRED'].mean()\n"
    "enhanced_results.append({'Test': 'TPFT Claim Frequency between TPO & Comp', 'Statistic': f\"{tpo_freq_c:.1%} < {tpft_freq_c:.1%} < {comp_freq_c:.1%}\", 'P-value': '-', 'Interpretation': 'TPFT covers TP + fire/theft only', 'Pass': tpo_freq_c < tpft_freq_c < comp_freq_c})")

# 6. EDA cell: include TPFT
rep('7f02ad04a87b',
    "pivot_covloc = pivot_covloc.reindex(['Comprehensive', 'TPO'])",
    "pivot_covloc = pivot_covloc.reindex(['Comprehensive', 'TPFT', 'TPO'])")

rep('7f02ad04a87b',
    "hue_order=['Comprehensive', 'TPO']",
    "hue_order=['Comprehensive', 'TPFT', 'TPO']")

rep('7f02ad04a87b',
    "for i, cov in enumerate(['Comprehensive', 'TPO']):",
    "for i, cov in enumerate(['Comprehensive', 'TPFT', 'TPO']):")

# 7. Export params: document TPFT frequency multiplier
rep('export-data',
    "    {'PARAMETER': 'TPO_FREQ_MULTIPLIER', 'VALUE': '0.45'},",
    "    {'PARAMETER': 'TPO_FREQ_MULTIPLIER', 'VALUE': '0.45'},\n"
    "    {'PARAMETER': 'TPFT_FREQ_MULTIPLIER', 'VALUE': '0.60'},")

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Saved. Total cells:', len(nb['cells']))