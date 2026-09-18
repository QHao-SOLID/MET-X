"""Telematics pricing method — GLM features plus the device score.

Rule sheet
----------
Frequency : same Poisson setup as GLM, features = GLM set + `telematics_score`
            (0-100, higher = safer; simulated per policy, rank-mapped to the
            latent BEHAVIOR_RISK, no raw trip data needed)
Severity  : identical to GLM (coverage x vehicle average, coverage fallback)
Premium   : freq x severity x expense_loading x risk_step^flags
Training  : identical out-of-sample setup as GLM (base template world)

Scenarios may override any declared CARD parameter, e.g.
`"pricing": {"telem": {"expense_loading": 1.8}}`.
"""

from ..ml import encode_features, fit_frequency, severity_by_row, severity_table, training_history
from ..pricing import register_pricer

CARD = {
    'expense_loading':    {'default': 1.5,  'unit': 'multiplier',   'note': 'pure-premium loading; raise -> lower LR'},
    'risk_step':          {'default': 1.1,  'unit': 'per flag',     'note': 'multiplier per true risk flag'},
    'glm_alpha':          {'default': 1e-3, 'unit': 'L2 penalty',   'note': 'Poisson regularization'},
    'train_frac':         {'default': 0.6,  'unit': 'fraction',     'note': 'share of training rows used to fit'},
    'train_seed':         {'default': 7,    'unit': 'seed',         'note': 'train-split seed'},
    'train_book_seed':    {'default': 42,   'unit': 'seed or null', 'note': 'separate historical book; null = in-sample (comparison only)'},
    'train_window_years': {'default': 5,    'unit': 'years',        'note': 'training horizon, one period before the priced cohort'},
    'train_vehicle':      {'default': None, 'unit': 'share dict or null', 'note': 'training fleet mix; null = training world vehicle_mix'},
    'train_dgp':          {'default': {},   'unit': 'engine overrides', 'note': 'extra training-world assumptions; {} = base template only'},
}

# Features this method prices on: the GLM set plus the telematics score.
FEATURES = ['DRIVER_AGE', 'CAR_AGE', 'NCD_LEVEL', 'VEHICLE_TYPE',
            'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION',
            'telematics_score']


def price_telem(book, card, cfg, base_cfg=None):
    """Standard method interface: (book, card, cfg, base_cfg) -> + FINAL_PREMIUM_SST."""
    out = book.copy()
    src = training_history(card, cfg, base_cfg) if card.train_book_seed is not None else out
    training_rows = src[src['COHORT_YEAR'] == src['SIM_YEAR']].sample(
        frac=card.train_frac, random_state=card.train_seed)
    model = fit_frequency(training_rows, FEATURES, card.glm_alpha)
    sev, covsev = severity_table(src)
    premium = (model.predict(encode_features(out, FEATURES))
               * severity_by_row(out, sev, covsev) * card.expense_loading)
    premium = (premium
               * card.risk_step ** out['FLOOD_RISK'].values.astype(int)
               * card.risk_step ** out['THEFT_RISK'].values.astype(int))
    return out.assign(FINAL_PREMIUM_SST=premium.round(2))


register_pricer('telem', price_telem, card=CARD, info={
    'label': 'GLM+Telematics',
    'color': '#2563eb',
    'formula': 'GLM features + telematics_score, same severity/loading structure',
})
