"""Tariff pricing method — owns the 2015 schedule tables, knobs and formula.

Rule sheet
----------
Comp / TPFT : BASIC x loading x (1 - NCD) x risk_step^flags x (1 + sst)
TPO         : (BASIC + tpo_sa_pct x SA) x tpo_loading x risk_step^flags x (1 + sst)
BASIC       : Schedule of Motor Tariff 2015, graduated:
              Comp = first-RM1,000 rate + PER_EXTRA per extra RM1,000 of SA
              TPFT = 75% of Comp; TPO = flat table rate (SA slice added above)
loading     : driver band (1.20 / 1.05 / 1.00 / 1.05) x (1 + 0.03 x min(CAR_AGE, 10))

Band labels must match base_template.json "engine_bands" exactly (validated at
price time). Scenarios may override any declared CARD parameter, e.g.
`"pricing": {"tariff": {"tpo_loading": 1.35}}`.
"""

import numpy as np

from ..pricing import register_pricer
from ..simulate import loading

CARD = {
    'sst':         {'default': 0.08,  'unit': 'fraction',       'note': 'premium tax on the tariff leg'},
    'tpo_sa_pct':  {'default': 0.005, 'unit': 'fraction of SA', 'note': 'TPO SA-linked premium slice'},
    'tpo_loading': {'default': 1.10,  'unit': 'multiplier',     'note': 'TPO fixed loading (no cover loading / NCD)'},
    'risk_step':   {'default': 1.1,   'unit': 'per flag',       'note': 'multiplier for each true risk flag (flood/theft)'},
}

# Schedule of Motor Tariff 2015 — RM rates by region and engine band.
TARIFF_BANDS = [
    "0 to 1,400 cc / EV up to 70 kW",
    "1,401 to 1,650 cc / EV 71 - 100 kW",
    "1,651 - 2,200 cc / EV 101 - 125 kW",
    "2,201 - 3,050 cc / EV 126 - 150 kW",
    "3,051 - 4,100 cc / EV 151 - 200 kW",
    "4,101 - 4,250 cc / EV 201 - 250 kW",
    "4,251 - 4,400 cc / EV 251 - 300 kW",
    "Over 4,400 cc / EV > 300 kW",
]
BASIC_COMP = {
    "Peninsular Malaysia": [273.8, 305.5, 339.1, 372.6, 404.3, 436.0, 469.6, 501.3],
    "East Malaysia (Sabah, Sawarak & Labuan)": [196.2, 220.0, 243.9, 266.5, 290.4, 313.0, 336.9, 359.5],
}
BASIC_TPO = {
    "Peninsular Malaysia": [120.6, 135.0, 151.2, 167.4, 181.8, 196.2, 212.4, 226.8],
    "East Malaysia (Sabah, Sawarak & Labuan)": [67.5, 75.6, 85.2, 93.6, 101.7, 110.1, 118.2, 126.6],
}
PER_EXTRA = {
    "Peninsular Malaysia": 26.0,
    "East Malaysia (Sabah, Sawarak & Labuan)": 20.3,
}


def basic_premium(book):
    """Tariff base premium per policy, before loadings / NCD / risk / tax."""
    band_index = {band: i for i, band in enumerate(TARIFF_BANDS)}
    unknown = set(book['ENGINE_CAPACITY']) - set(band_index)
    if unknown:
        raise ValueError(f"tariff tables missing bands {sorted(unknown)} — "
                         "update methods/tariff.py or base_template engine_bands")
    region = book['REGION'].values
    band = book['ENGINE_CAPACITY'].values
    comp_rate = np.array([BASIC_COMP[r][band_index[b]] for r, b in zip(region, band)])
    extra_rate = np.array([PER_EXTRA[r] for r in region])
    units = np.ceil(np.maximum(0, book['SUM_ASSURED'].values - 1000) / 1000)
    comp_basic = comp_rate + extra_rate * units
    tpo_rate = np.array([BASIC_TPO[r][band_index[b]] for r, b in zip(region, band)])
    coverage = book['COVERAGE_TYPE'].values
    basic = np.where(coverage == 'Comprehensive', comp_basic,
                     np.where(coverage == 'TPFT', np.round(0.75 * comp_basic, 2), tpo_rate))
    return np.round(basic, 2)


def price_tariff(book, card, cfg, base_cfg=None):
    """Standard method interface: (book, card, cfg, base_cfg) -> + FINAL_PREMIUM_SST."""
    out = book.copy()
    base = basic_premium(out)
    ncd = 1 - out['NCD_LEVEL'].values
    flags = out['FLOOD_RISK'].values.astype(int) + out['THEFT_RISK'].values.astype(int)
    risk = card.risk_step ** flags
    prem = base * loading(out, cfg) * ncd * risk * (1 + card.sst)
    tpo = out['COVERAGE_TYPE'].values == 'TPO'
    prem[tpo] = ((base[tpo] + card.tpo_sa_pct * out['SUM_ASSURED'].values[tpo])
                 * card.tpo_loading * risk[tpo] * (1 + card.sst))
    return out.assign(FINAL_PREMIUM_SST=prem.round(2))


register_pricer('tariff', price_tariff, card=CARD, info={
    'label': 'Tariff',
    'color': '#94a3b8',
    'formula': ('Comp/TPFT = BASIC x loading x (1-NCD) x risk_step^flags x (1+sst); '
                'TPO = (BASIC + tpo_sa_pct x SA) x tpo_loading x risk_step^flags x (1+sst)'),
})
