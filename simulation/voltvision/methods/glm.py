"""GLM pricing method — Poisson frequency x observed severity x loading.

Rule sheet
----------
Frequency : PoissonRegressor(alpha=glm_alpha) on FEATURES below; trained on
            `train_frac` of the first-year rows of a SEPARATE historical book
Severity  : mean CLAIM_AMOUNT per CLAIM_COUNT by (COVERAGE_TYPE, VEHICLE_TYPE),
            falling back to the by-coverage average
Premium   : freq x severity x expense_loading x risk_step^flags

Training world: generated from the BASE template one window earlier (see
`ml.training_history`) — scenario DGP patches never leak into training, so
stressed scenarios show honest loss-ratio deterioration.

Scenarios may override any declared CARD parameter, e.g.
`"pricing": {"glm": {"expense_loading": 1.8}}`.
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

# Features this method prices on (the method owns its feature list).
FEATURES = ['DRIVER_AGE', 'CAR_AGE', 'NCD_LEVEL', 'VEHICLE_TYPE',
            'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION']


def price_glm(book, card, cfg, base_cfg=None):
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


register_pricer('glm', price_glm, card=CARD, info={
    'label': 'GLM',
    'color': '#f59e0b',
    'formula': ('Poisson freq (features above) x avg severity x expense_loading '
                'x risk_step^flags'),
})
