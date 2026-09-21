"""Shared helpers for ML pricing methods (glm.py / telem.py).

These are method-side utilities — the connector (pricing.py) never calls them.
Feature LISTS stay in each method module (the method owns its features).
"""

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import PoissonRegressor

from .assumptions import deep_merge
from .simulate import simulate_book  # noqa: F401  (re-exported for method modules)


def encode_features(d, feats):
    """Category-code the categoricals: the Poisson model needs numbers, and
    codes are fine because the model treats them as ordered proxies."""
    X = d[feats].copy()
    for c in ('VEHICLE_TYPE', 'COVERAGE_TYPE', 'REGION'):
        if c in feats:
            X[c] = X[c].astype('category').cat.codes
    return X


def fit_frequency(tr, feats, alpha, max_iter=1000):
    """Fit the Poisson frequency model on a training slice."""
    return PoissonRegressor(alpha=alpha, max_iter=max_iter).fit(
        encode_features(tr, feats), tr['CLAIM_COUNT'])


def severity_table(book):
    """Mean paid per claim by (coverage, vehicle) with coverage fallback:
    vehicle rows price at their observed severity, pooled average where not."""
    sev = book.groupby(['COVERAGE_TYPE', 'VEHICLE_TYPE']).apply(
        lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum(),
        include_groups=False).to_dict()
    covsev = book.groupby('COVERAGE_TYPE').apply(
        lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum(),
        include_groups=False).to_dict()
    return sev, covsev


def severity_by_row(book, sev, covsev):
    """Per-row severity: (coverage, vehicle) value with coverage fallback."""
    keys = list(zip(book['COVERAGE_TYPE'].values, book['VEHICLE_TYPE'].values))
    return np.array([sev.get(k, np.nan) if not np.isnan(sev.get(k, np.nan)) else covsev[k[0]]
                     for k in keys], float)


def training_history(card, cfg, base_cfg, vehicle=None):
    """Training dataset for the ML methods: a book from the BASE template
    world, one window earlier than the priced cohort.

    Why: historical experience is fixed. If the training book were generated
    under the scenario's stressed DGP, the model would pre-price a shock it
    never lived through and stress tests would show fake stability at the cost
    of inflated premiums. `train_dgp` adds explicit training-world overrides;
    `train_book_seed = null` reverts to in-sample training (comparison only).
    `vehicle` overrides the training fleet mix explicitly (e.g. an all-EV book
    for the telematics EV model); None = card.train_vehicle → world mix.
    """
    world = base_cfg if base_cfg is not None else cfg
    train_cfg = deep_merge(world, card.train_dgp or {})
    train_cfg['cohort_year'] = cfg['cohort_year'] - card.train_window_years
    vehicle = vehicle if vehicle is not None else (
        card.train_vehicle or train_cfg['vehicle_ramp']['from'])
    return simulate_book(train_cfg, vehicle, card.train_book_seed,
                         n_years=card.train_window_years, cache=True)


def cfg_fingerprint(cfg):
    """DGP fingerprint for caching — pricing/reporting blobs excluded."""
    engine = {k: v for k, v in cfg.items() if k not in ('pricing', 'reporting')}
    return json.dumps(engine, sort_keys=True, default=str)
