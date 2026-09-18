"""Shared helpers for ML pricing methods (used by 02b/02c CALC cells).

These are method-side utilities — the connector (pricing.py) never calls them.
Feature LISTS stay in each method notebook (the method owns its features).
"""

import numpy as np
import pandas as pd
import json

from sklearn.linear_model import PoissonRegressor
from .simulate import gen, simulate  # noqa: F401  (re-exported for method cells)


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
    EVs price at EV severity where observed, pooled average where not."""
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


def cfg_fingerprint(cfg):
    """DGP fingerprint for caching — pricing/reporting blobs excluded."""
    engine = {k: v for k, v in cfg.items() if k not in ('pricing', 'reporting')}
    return json.dumps(engine, sort_keys=True, default=str)
