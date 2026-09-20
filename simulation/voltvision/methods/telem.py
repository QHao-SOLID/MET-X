"""Telematics pricing method — GLM features plus the device score.

Rule sheet
----------
Frequency : same Poisson setup as GLM, features = GLM set + `telematics_score`
            (0-100, higher = safer; simulated per policy, rank-mapped to the
            latent BEHAVIOR_RISK, no raw trip data needed)
Severity  : identical to GLM (coverage x vehicle average, coverage fallback)
Premium   : freq x severity / target_lr x (1 - NCD_LEVEL) x risk_step^flags
            with NCD applied AFTER the model (statutory discount, TPO exempt)
Training  : identical out-of-sample setup as GLM (base template world)

Scenarios may override any declared CARD parameter, e.g.
`"pricing": {"telem": {"target_lr": 0.60}}`.
"""

import numpy as np

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
    'train_vehicle':      {'default': None, 'unit': 'share dict or null', 'note': 'training fleet mix; null = training world vehicle_ramp.from'},
    'train_dgp':          {'default': {},   'unit': 'engine overrides', 'note': 'extra training-world assumptions; {} = base template only'},
}

# Features this method prices on: the GLM set plus the telematics score.
# NCD_LEVEL is deliberately absent (statutory post-model discount, like GLM).
FEATURES = ['DRIVER_AGE', 'CAR_AGE', 'VEHICLE_TYPE',
            'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION',
            'telematics_score']


def train_model(book, card, cfg, base_cfg=None):
    """Fit the frequency model exactly as pricing does (same code path).

    Returns (model, sev, covsev, training_rows) — used by the pricer and by
    the SHAP explainability section in `analysis.ipynb`.
    """
    src = training_history(card, cfg, base_cfg) if card.train_book_seed is not None else book
    training_rows = src[src['COHORT_YEAR'] == src['SIM_YEAR']].sample(
        frac=card.train_frac, random_state=card.train_seed)
    model = fit_frequency(training_rows, FEATURES, card.glm_alpha)
    sev, covsev = severity_table(src)
    return model, sev, covsev, training_rows


def price_telem(book, card, cfg, base_cfg=None):
    """Standard method interface: (book, card, cfg, base_cfg) -> + FINAL_PREMIUM_SST."""
    out = book.copy()
    model, sev, covsev, _ = train_model(out, card, cfg, base_cfg)
    premium = (model.predict(encode_features(out, FEATURES))
               * severity_by_row(out, sev, covsev) / card.target_lr)
    ncd_keep = np.where(out['COVERAGE_TYPE'].values == 'TPO', 1.0,
                        1 - out['NCD_LEVEL'].values)
    premium = (premium * ncd_keep
               * card.risk_step ** out['FLOOD_RISK'].values.astype(int)
               * card.risk_step ** out['THEFT_RISK'].values.astype(int))
    return out.assign(FINAL_PREMIUM_SST=premium.round(2))


register_pricer('telem', price_telem, card=CARD, info={
    'label': 'GLM+Telematics',
    'color': '#2563eb',
    'formula': ('GLM features + telematics_score, same severity / target_lr / '
                'NCD / risk_step structure'),
})
