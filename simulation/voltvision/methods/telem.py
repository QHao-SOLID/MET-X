"""Telematics pricing method — GLM features plus the device score (EV only).

Rule sheet
----------
Telematics device data only exists for EVs (ICE cannot be instrumented), so
the method holds TWO frequency models:

  EV  model : GLM features + `telematics_score` (0-100, higher = safer),
              trained on a full-EV book (enough rows to learn the score).
  ICE model : GLM features (no score), trained on a full-ICE book.

Severity  : coverage x vehicle average (coverage fallback); EV severity from
            the EV book, ICE severity from the ICE book.
Premium   : freq x severity / target_lr x (1 - NCD_LEVEL) x risk_step^flags
            with NCD applied AFTER the model (statutory discount, TPO exempt)
Training  : identical out-of-sample setup as GLM (base template world), split
            per fuel (train_vehicle_ev / train_vehicle_ice)

Scenarios may override any declared CARD parameter, e.g.
`"pricing": {"telem": {"target_lr": 0.60}}`.
"""

import numpy as np
import pandas as pd

from ..ml import encode_features, fit_frequency, severity_by_row, severity_table, training_history
from ..pricing import register_pricer

CARD = {
    'target_lr':          {'default': 0.55, 'unit': 'loss-ratio anchor', 'note': 'pure premium / target_lr; NCD and flags apply after, so achieved LR runs higher'},
    'risk_step':          {'default': 1.1,  'unit': 'per flag',     'note': 'multiplier per true risk flag'},
    'glm_alpha':          {'default': 1e-3, 'unit': 'L2 penalty',   'note': 'Poisson regularization'},
    'train_frac':         {'default': 0.6,  'unit': 'fraction',     'note': 'share of training rows used to fit'},
    'train_seed':         {'default': 7,    'unit': 'seed',         'note': 'train-split seed'},
    'train_book_seed':    {'default': 42,   'unit': 'seed or null', 'note': 'separate historical book; null = in-sample (comparison only)'},
    'train_window_years': {'default': 5,    'unit': 'years',        'note': 'training horizon, one period before the priced cohort'},
    'train_vehicle_ev':   {'default': {'EV': 1.0},  'unit': 'share dict', 'note': 'EV model training fleet (full-EV book)'},
    'train_vehicle_ice':  {'default': {'ICE': 1.0}, 'unit': 'share dict', 'note': 'ICE model training fleet (full-ICE book)'},
    'train_dgp':          {'default': {},   'unit': 'engine overrides', 'note': 'extra training-world assumptions; {} = base template only'},
}

# Features per fuel: EV adds the telematics score; ICE has no device score.
# NCD_LEVEL is deliberately absent (statutory post-model discount, like GLM).
FEATURES_EV = ['DRIVER_AGE', 'CAR_AGE', 'VEHICLE_TYPE',
               'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION',
               'telematics_score']
FEATURES_ICE = ['DRIVER_AGE', 'CAR_AGE', 'VEHICLE_TYPE',
                'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION']


def train_model(book, card, cfg, base_cfg=None):
    """Fit the EV and ICE frequency models exactly as pricing does.

    Each model trains on a full-fuel book (EV model on an all-EV book, ICE
    model on an all-ICE book) so the EV model has enough rows to learn the
    `telematics_score` signal. Severity merges the two books (EV severity from
    the EV book, ICE severity from the ICE book).

    Returns (ev_model, ice_model, sev, covsev, training_rows) — used by the
    pricer and by the SHAP explainability section in `analysis.ipynb`.
    """
    if card.train_book_seed is not None:
        ev_src = training_history(card, cfg, base_cfg, vehicle=card.train_vehicle_ev)
        ice_src = training_history(card, cfg, base_cfg, vehicle=card.train_vehicle_ice)
    else:
        ev_src = book[book['VEHICLE_TYPE'] == 'EV']
        ice_src = book[book['VEHICLE_TYPE'] == 'ICE']
    ev_rows = ev_src[ev_src['COHORT_YEAR'] == ev_src['SIM_YEAR']].sample(
        frac=card.train_frac, random_state=card.train_seed)
    ice_rows = ice_src[ice_src['COHORT_YEAR'] == ice_src['SIM_YEAR']].sample(
        frac=card.train_frac, random_state=card.train_seed)
    ev_model = fit_frequency(ev_rows, FEATURES_EV, card.glm_alpha)
    ice_model = fit_frequency(ice_rows, FEATURES_ICE, card.glm_alpha)
    sev_ev, covsev_ev = severity_table(ev_src)
    sev_ice, covsev_ice = severity_table(ice_src)
    sev = {**sev_ev, **sev_ice}
    covsev = {c: (covsev_ev[c] + covsev_ice[c]) / 2 for c in covsev_ev}
    return ev_model, ice_model, sev, covsev, pd.concat([ev_rows, ice_rows])


def price_telem(book, card, cfg, base_cfg=None):
    """Standard method interface: (book, card, cfg, base_cfg) -> + FINAL_PREMIUM_SST."""
    out = book.copy()
    ev_model, ice_model, sev, covsev, _ = train_model(out, card, cfg, base_cfg)
    ev = out['VEHICLE_TYPE'].values == 'EV'
    ice = ~ev
    pred = np.empty(len(out))
    pred[ev] = ev_model.predict(encode_features(out[ev], FEATURES_EV))
    pred[ice] = ice_model.predict(encode_features(out[ice], FEATURES_ICE))
    premium = pred * severity_by_row(out, sev, covsev) / card.target_lr
    ncd_keep = np.where(out['COVERAGE_TYPE'].values == 'TPO', 1.0,
                        1 - out['NCD_LEVEL'].values)
    premium = (premium * ncd_keep
               * card.risk_step ** out['FLOOD_RISK'].values.astype(int)
               * card.risk_step ** out['THEFT_RISK'].values.astype(int))
    return out.assign(FINAL_PREMIUM_SST=premium.round(2))


register_pricer('telem', price_telem, card=CARD, info={
    'label': 'GLM+Telematics',
    'color': '#2563eb',
    'formula': ('EV: GLM features + telematics_score; ICE: GLM features. '
                'Same severity / target_lr / NCD / risk_step structure'),
})
