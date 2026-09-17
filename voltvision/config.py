"""Single source of truth for config, tariff tables, and column order.

ONLY edit the CFG dict / VEHICLE_SCENARIO values to re-run scenarios.
DGP coefficients live in simulate.py; premium formulas live in the 02x
notebooks' CALC cells (pricing.py only connects); live numbers in RateCard.
"""

REGIMES = ('tariff', 'glm', 'telem')
LABEL = {
    'tariff': 'Tariff',
    'glm': 'GLM',
    'telem': 'GLM+Telematics'
}
COLOR = {
    'tariff': '#94a3b8',
    'glm': '#f59e0b',
    'telem': '#2563eb'
}
N_YEARS, SEED = 5, 20260916

# ---- Run choice: ONLY config notebooks need to touch ----
VEHICLE_SCENARIO = "ALL"   # "ICE" | "EV" | "MIX" | "ALL"
SCEN = {
    "ICE": {"ICE": 1.0, "EV": 0.0},
    "EV": {"ICE": 0.0, "EV": 1.0},
    "MIX": {"ICE": 0.9, "EV": 0.1}
}

CFG = {
    # Book size / horizon / reproducibility. n=10000 keeps GLM fits stable;
    # drop to 1000 for smoke runs (QUICK flag in the notebooks).
    'n': 10000, 'cohort_year': 2026, 'seed': SEED,
    # Product mix. TPO share drives portfolio LR (TPO tariff underprices).
    'coverage_pct': {
        'Comprehensive': 0.65,
        'TPFT': 0.20,
        'TPO': 0.15
    },
    'region_pct': {
        'Peninsular Malaysia': 0.80,
        'East Malaysia (Sabah, Sawarak & Labuan)': 0.20
    },
    # Driver mix + exact age span per band (upper bound exclusive in draws).
    'generation_pct': {
        'Young Adults': 0.40,
        'Adults': 0.40,
        'Mature Adults': 0.15,
        'Seniors': 0.05
    },
    'age_bands': {
        'Young Adults': (18, 28),
        'Adults': (28, 46),
        'Mature Adults': (46, 66),
        'Seniors': (66, 76)
    },
    'gender_pct': {
        'Male': 0.55,
        'Female': 0.45
    },
    # Car age at inception: band median + sigma noise, clipped 0-10.
    'car_age_median': {
        'Young Adults': 2.0,
        'Adults': 3.5,
        'Mature Adults': 5.0,
        'Seniors': 5.5
    },
    'car_age_sigma': 1.5,
    # Frequency base (log scale): -2.00 ~= 13.5% base rate before rating.
    'claim_frequency_base': -2.00,
    # EV repair loading on own-damage severity only (AD/Theft/Fire).
    'ev_severity_factor': 1.20,
    # Global severity shock applied to EVERY peril (stress lever):
    # 1.00 baseline, 1.20 = +20% claim costs. Multiplies the EV loading.
    'severity_multiplier': 1.00,
    # Pricing legs (also RateCard defaults): GLM multiplier, TPO SA slice
    # + fixed loading (too low today — TPO LR >100%), premium tax.
    'expense_loading': 1.5, 'tpo_sa_pct': 0.005, 'tpo_loading': 1.10, 'SST': 0.08,
    # Sum assured log-normal (median, spread) per fuel type, rounded to RM1k.
    'sa_stats': {
        'ICE': (50000, 0.5),
        'EV': (80000, 0.5)
    },
    # NCD discount by claim-free years (cap with min(y,5) at lookup).
    'ncd_table': {0: 0.0, 1: 0.25, 2: 0.30, 3: 0.3833, 4: 0.45, 5: 0.55},
    # Engine-band mix: small cars dominate the book.
    'engine_weights': [0.25, 0.20, 0.18, 0.15, 0.10, 0.07, 0.03, 0.02],
    # Yearly entrants as a fraction of n (same vehicle mix, no EV ramp yet).
    'entrant_frac': 0.50,
}

BANDS = [
    "0 to 1,400 cc / EV up to 70 kW", "1,401 to 1,650 cc / EV 71 - 100 kW",
    "1,651 - 2,200 cc / EV 101 - 125 kW", "2,201 - 3,050 cc / EV 126 - 150 kW",
    "3,051 - 4,100 cc / EV 151 - 200 kW", "4,101 - 4,250 cc / EV 201 - 250 kW",
    "4,251 - 4,400 cc / EV 251 - 300 kW", "Over 4,400 cc / EV > 300 kW",
]
BASIC_COMP = {
    "Peninsular Malaysia": [273.8, 305.5, 339.1, 372.6, 404.3, 436.0, 469.6, 501.3],
    "East Malaysia (Sabah, Sawarak & Labuan)": [196.2, 220.0, 243.9, 266.5, 290.4, 313.0, 336.9, 359.5]
}
BASIC_TPO = {
    "Peninsular Malaysia": [120.6, 135.0, 151.2, 167.4, 181.8, 196.2, 212.4, 226.8],
    "East Malaysia (Sabah, Sawarak & Labuan)": [67.5, 75.6, 85.2, 93.6, 101.7, 110.1, 118.2, 126.6]
}
PER_EXTRA = {
    "Peninsular Malaysia": 26.0,
    "East Malaysia (Sabah, Sawarak & Labuan)": 20.3
}
PERIL_DIST = {
    'Comprehensive': {
        'AD': 0.58,
        'Windscreen': 0.15,
        'Theft': 0.08,
        'Fire': 0.04,
        'TPPD': 0.12,
        'TPBI': 0.03
    },
    'TPO': {
        'TPPD': 0.78,
        'TPBI': 0.22
    },
    'TPFT': {
        'TPPD': 0.444,
        'TPBI': 0.111,
        'Theft': 0.296,
        'Fire': 0.148
    }
}

# ---- Canonical simulated-book column order (attributes + claims only).
# vs voltvision_all cols_to_keep: ENGINE_CAPACITY kept, BASIC_PREMIUM dropped
# — the tariff base is computed by the tariff pricer (02a) from attributes. ----
COLS = ['POLID', 'COVERAGE_TYPE', 'SUM_ASSURED', 'REGION', 'VEHICLE_TYPE',
        'ENGINE_CAPACITY',
        'DRIVER_AGE_CAT', 'DRIVER_AGE', 'CAR_AGE', 'DRIVER_GENDER',
        'FLOOD_RISK', 'THEFT_RISK',
        'NCD_LEVEL_PRICED', 'NCD_LEVEL',
        'NCD_YEARS', 'CLAIM_LAMBDA',
        'SIM_YEAR', 'CLAIM_COUNT', 'CLAIM_OCCURRED', 'CLAIM_AMOUNT',
        'CLAIM_PERIL',
        'RENEWAL_PROB', 'RENEWED', 'COHORT_YEAR',
        'BEHAVIOR_RISK', 'telematics_score']


# ---- Self-export -------------------------------------------------------------
# Names dumped by export_config(): every data constant this module owns.
# Dunder names, imports and the function itself are intentionally excluded.
EXPORT_NAMES = ['REGIMES', 'LABEL', 'COLOR', 'N_YEARS', 'SEED',
                'VEHICLE_SCENARIO', 'SCEN', 'CFG',
                'BANDS', 'BASIC_COMP', 'BASIC_TPO', 'PER_EXTRA',
                'PERIL_DIST', 'COLS']


def export_config(path=None, cfg=None, scen=None):
    """Dump this module's contents to JSON (provenance for a run).

    Writes every name in EXPORT_NAMES plus an `exported_at` timestamp.
    `cfg` / `scen` replace the CFG / SCEN entries when a caller (e.g.
    run_all.py) ran with one-off overrides — the record then matches the run.
    Tuples inside CFG (age bands, SA stats) serialise as strings — this is
    a record for audit, not a reloadable config; edits belong in this file.
    Default target: shared/config_export.json. Returns the written path.
    Run directly:  python voltvision/config.py  (or python -m voltvision.config)
    """
    import datetime as _dt
    import json
    from pathlib import Path

    out = {name: globals()[name] for name in EXPORT_NAMES}
    if cfg is not None:
        out['CFG'] = cfg
    if scen is not None:
        out['SCEN'] = scen
    out['exported_at'] = _dt.datetime.now().isoformat(timespec='seconds')
    p = Path(path) if path else (Path(__file__).resolve().parent.parent
                                 / 'shared' / 'config_export.json')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding='utf-8')
    return p


if __name__ == '__main__':
    print('wrote', export_config())
