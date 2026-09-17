"""Live pricing desk CONNECTOR (calculation lives in the 02x notebooks).

Pricing is ACTIVE: rules and numbers change in 02a_tariff.ipynb,
02b_glm.ipynb, 02c_telem.ipynb — each owns its premium calculation cell.
This module only connects: registry, RateCard, quote/api_quote, reporting.
Everything below assumes N regimes: no function hardcodes tariff/glm/telem.

Connector (API shape):
  request  = simulated book + regime name + RateCard
  response = book + FINAL_PREMIUM_SST
  quote(book, regime, card)               single regime
  price_many(book, cfg, regimes, cards)   N regimes, optional per-regime cards
  api_quote(book, regime, card)           standard output dict

Standard pricer format — every method cell follows it:
  func(book: pd.DataFrame, card: RateCard) -> pd.DataFrame
Rules:
  - Input is a SIMULATED book (simulate.py output). Never price raw gen() output.
  - Do not mutate the input (copy first).
  - Output = input columns + FINAL_PREMIUM_SST (RM, SST-inclusive).
  - Read every number from `card`, never from cfg or literals.
  - Cell ends with register_pricer(name, func, info).
  - Always compare regimes side by side — never show one regime alone.
Shared primitives for method cells: FEATS_G, encode_features,
fit_frequency, severity_table (plus loading from simulate).
Core methods load from their notebooks via ensure_core_methods().
"""

from dataclasses import dataclass
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import PoissonRegressor

from .config import LABEL, REGIMES, COLOR, N_YEARS, CFG as DEFAULT_CFG
from .simulate import loading

# Fallback bar colors for regimes beyond the core three (deterministic by name).
_PALETTE = ['#8b5cf6', '#06b6d4', '#ef4444', '#10b981', '#f97316', '#a3e635']


def reg_color(m):
    """Bar color for any regime: core palette or deterministic fallback."""
    if m in COLOR:
        return COLOR[m]
    return _PALETTE[abs(hash(m)) % len(_PALETTE)]


def reg_label(m):
    """Display label for any regime: known label or the raw name."""
    return LABEL.get(m, m)


# Shared GLM feature list (telem appends 'telematics_score' in its own cell).
FEATS_G = ['DRIVER_AGE', 'CAR_AGE', 'NCD_LEVEL', 'VEHICLE_TYPE',
           'COVERAGE_TYPE', 'FLOOD_RISK', 'THEFT_RISK', 'REGION']

# Columns a priced book must have before quoting (i.e. it came from simulate).
_REQUIRED_BOOK_COLS = ('SIM_YEAR', 'COHORT_YEAR', 'POLID', 'CLAIM_COUNT',
                       'CLAIM_AMOUNT', 'BASIC_PREMIUM', 'NCD_LEVEL')


@dataclass
class RateCard:
    """Every live pricing number. Built from CFG, overridden in the notebook."""
    sst: float = 0.08               # sales/service tax on premium; raise -> dearer cover, lower LR
    expense_loading: float = 1.5    # GLM pure-premium multiplier; raise -> lower GLM LR
    tpo_sa_pct: float = 0.005       # TPO tariff SA slice (fraction of sum assured)
    tpo_loading: float = 1.10       # TPO fixed loading; raise -> lower TPO LR (see TODO)
    risk_step: float = 1.1          # per-flag multiplier for flood/theft
    glm_alpha: float = 1e-3         # Poisson regularization; raise -> smoother, less segmented
    train_frac: float = 0.6         # share of same-year rows training the GLM
    train_seed: int = 7             # train split seed (fixed so re-quotes compare like-for-like)
    train_book_seed: "int | None" = 42  # default: fit on a SEPARATE historical book (seed 42,
                                    # window one period back = 2021-2025) so the priced book's
                                    # own outcomes never train the model; None = legacy
                                    # in-sample training (parity/debug comparisons only)

    @classmethod
    def from_cfg(cls, cfg, **overrides):
        # Start from CFG so desk and engine agree, then apply live tweaks.
        base = {'sst': cfg['SST'], 'expense_loading': cfg['expense_loading'],
                'tpo_sa_pct': cfg['tpo_sa_pct'], 'tpo_loading': cfg['tpo_loading']}
        base.update(overrides)
        unknown = set(base) - {f.name for f in cls.__dataclass_fields__.values()}
        if unknown:
            raise ValueError(f"unknown rate fields: {sorted(unknown)}")
        obj = cls(**base)
        # Keep the source config on the card so training_book(card) can build a
        # separate training book with the same assumptions (out-of-sample mode).
        obj._cfg = cfg
        return obj


def encode_features(d, feats):
    # Category-code the categoricals: tree-free Poisson needs numbers,
    # codes are fine because the model treats them as ordered proxies.
    X = d[feats].copy()
    for c in ('VEHICLE_TYPE', 'COVERAGE_TYPE', 'REGION'):
        if c in feats:
            X[c] = X[c].astype('category').cat.codes
    return X


_enc = encode_features  # short alias used inside method cells


def fit_frequency(tr, feats, alpha):
    # Poisson GLM for claim counts: the right model for 0/1/2-type event data.
    return PoissonRegressor(alpha=alpha, max_iter=1000).fit(
        encode_features(tr, feats), tr['CLAIM_COUNT'])


def severity_table(book):
    # Mean paid per claim, by (coverage, vehicle) with coverage fallback:
    # EVs price at EV severity where observed, pooled average where not.
    sev = book.groupby(['COVERAGE_TYPE', 'VEHICLE_TYPE']).apply(
        lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum(),
        include_groups=False).to_dict()
    covsev = book.groupby('COVERAGE_TYPE').apply(
        lambda d: d['CLAIM_AMOUNT'].sum() / d['CLAIM_COUNT'].sum(),
        include_groups=False).to_dict()
    return sev, covsev


# Cached out-of-sample training books: (train_book_seed, DGP fingerprint) -> book.
# Building one costs a full simulation, so repeated quotes reuse the same book.
_TRAIN_BOOK_CACHE = {}


def _cfg_key(cfg):
    # DGP fingerprint for the training-book cache. Premium-only levers are
    # excluded so RateCard tweaks (loading, SST...) never rebuild the book;
    # anything that changes claims/features (n, seeds, freq base...) does.
    c = {k: v for k, v in cfg.items()
         if k not in ('expense_loading', 'tpo_sa_pct', 'tpo_loading', 'SST')}
    return json.dumps(c, sort_keys=True, default=str)


def training_book(card):
    # Default training source: a book from its OWN historical window, fully
    # disjoint from the priced book. Cohort year shifts back one full period
    # (2021 vs priced 2026) and the seed differs (42 vs priced 20260916), so
    # no policy, claim or year ever trains the price of itself or its future.
    from .simulate import gen, simulate
    from .config import SCEN
    base = getattr(card, '_cfg', None) or DEFAULT_CFG
    cfg = {**base}                                   # shallow copy is enough here
    cfg['cohort_year'] = int(base['cohort_year']) - N_YEARS   # 2026 -> 2021
    key = (card.train_book_seed, _cfg_key(cfg))
    if key not in _TRAIN_BOOK_CACHE:
        book = simulate(gen(cfg, SCEN['MIX'], card.train_book_seed),
                        cfg, SCEN['MIX'], seed=card.train_book_seed,
                        n_years=N_YEARS, verbose=False)
        # Fail loud if the windows ever overlap (would silently reintroduce leakage).
        train_years = set(book['SIM_YEAR'].unique())
        priced_years = set(range(int(base['cohort_year']), int(base['cohort_year']) + N_YEARS))
        assert train_years.isdisjoint(priced_years), \
            f'training window {sorted(train_years)} overlaps priced window {sorted(priced_years)}'
        _TRAIN_BOOK_CACHE[key] = book
    return _TRAIN_BOOK_CACHE[key]


# Registry starts empty: 02x notebooks own the calculations and register them.
# ensure_core_methods() (below) loads them for hub/03/desk/runner use.
PRICERS = {}

PRICER_INFO = {}


def describe_pricer(name):
    # Interface sheet for one regime: label, editable card params, formula.
    # Unknown names get a neutral sheet so custom regimes still display.
    info = PRICER_INFO.get(name, {'label': reg_label(name), 'params': [], 'formula': 'custom'})
    return {'regime': name, **info}


def register_pricer(name, func, info=None):
    # A method cell calls this last: name the regime, hand over the function,
    # optionally pin its interface sheet. Same name twice = latest wins.
    if not callable(func):
        raise TypeError("pricer must be callable(book, card)")
    PRICERS[name] = func
    if info is not None:
        PRICER_INFO[name] = info
    return func


def discover_methods(root=None, pattern='02*.ipynb'):
    # Find every method notebook (any 02*.ipynb with a tagged calc cell)
    # and register whatever each one owns. New 02d_x.ipynb joins with
    # zero connector edits — just add the file. Returns {regime: notebook}.
    from .loader import calc_source, CORE_METHODS
    from pathlib import Path
    root = Path(root or '.')
    found = {}
    for nb in sorted(root.glob(pattern)):
        # Peek at calc tags without executing: cheap scan of cell metadata.
        try:
            import json
            tags = {t for c in json.loads(nb.read_text(encoding='utf-8'))['cells']
                    if c['cell_type'] == 'code'
                    for t in c.get('metadata', {}).get('tags', [])}
        except Exception:
            continue
        for tag in sorted(tags - {'calc'}):
            if tag not in PRICERS:
                exec(compile(calc_source(nb, tag), nb.name, 'exec'),
                     {'__name__': f'voltvision_method_{tag}'})
            found[tag] = nb.name
    # Core regimes must exist after discovery — fail loud, not silent.
    missing = [m for m in CORE_METHODS if m not in PRICERS]
    if missing:
        raise RuntimeError(f"core regimes missing after discovery: {missing}")
    return found


def ensure_core_methods(root=None):
    # Load tariff/glm/telem calculations from their 02x notebooks.
    # Call once in hub/03/desk/runner before quoting. No-op if registered.
    from .loader import ensure_methods, CORE_METHODS
    return ensure_methods(root=root, methods=CORE_METHODS)


def _check_book(book, regime):
    # Fail fast with a useful message: pricing a raw gen() book (no claims)
    # or a wrong frame is the classic wiring mistake — catch it here,
    # not three stack frames deep inside a pricer.
    missing = [c for c in _REQUIRED_BOOK_COLS if c not in book.columns]
    if missing:
        raise ValueError(
            f"cannot quote {regime!r}: book lacks {missing} — "
            "price SIMULATED books (01/runner output), never raw gen() output")


def quote(book, regime, card):
    # Connector: price one simulated book under one regime.
    # Request  = (book, regime, card). Response = book + FINAL_PREMIUM_SST.
    _check_book(book, regime)
    try:
        pricer = PRICERS[regime]
    except KeyError:
        raise ValueError(f"unknown pricing regime {regime!r}; "
                         f"registered: {sorted(PRICERS)}") from None
    out = pricer(book, card)
    if 'FINAL_PREMIUM_SST' not in out.columns:
        raise RuntimeError(f"pricer {regime!r} did not set FINAL_PREMIUM_SST")
    return out


def price_book(book, method, cfg, **overrides):
    # Single-regime dispatch with a card built from cfg + live overrides.
    return quote(book, method, RateCard.from_cfg(cfg, **overrides))


def price_all3(book, cfg, **overrides):
    # Core three, kept as the default full-set call.
    return price_many(book, cfg, REGIMES, **overrides)


def price_many(book, cfg, regimes, cards=None, **overrides):
    # Price the SAME book N ways. Each regime may carry its own card
    # overrides via cards={name: {...}}; shared overrides apply to the rest.
    # One shared card would force every regime onto the same numbers —
    # per-regime cards are why N regimes stay comparable yet independent.
    out = {}
    for m in regimes:
        card = RateCard.from_cfg(cfg, **overrides, **(cards or {}).get(m, {}))
        out[m] = quote(book, m, card)
    return out


def api_quote(book, regime, card):
    # Standard API output for one quote: identity + inputs + metrics + book.
    # Metrics are rounded for display; the book stays full-precision.
    priced = quote(book, regime, card)
    return {
        'regime': regime,
        'label': reg_label(regime),
        # Public card fields only (skip the private _cfg snapshot).
        'card': {k: v for k, v in vars(card).items() if not k.startswith('_')}
                if hasattr(card, '__dataclass_fields__') else dict(card),
        'metrics': {
            'lr': round(lr(priced), 2),
            'avg_prem': round(float(priced['FINAL_PREMIUM_SST'].mean()), 0),
            'rho': round(float(rho(priced)), 3),
            'rows': len(priced),
        },
        'book': priced,
    }


def api_quote_many(book, cfg, regimes, cards=None, **overrides):
    # Batch API output: one api_quote dict per regime, same card rules.
    card = RateCard.from_cfg(cfg, **overrides)
    base = dict(cards or {})
    return {m: api_quote(book, m, RateCard.from_cfg(cfg, **overrides, **base.get(m, {})))
            for m in regimes}


# ---- Reporting helpers (regime comparison only, all N-safe) ----

def lr(b):
    # Portfolio loss ratio %: claims paid per 100 premium.
    return b['CLAIM_AMOUNT'].sum() / b['FINAL_PREMIUM_SST'].sum() * 100


def lr_by(b, col):
    # Loss ratio sliced by any column (coverage, vehicle, year...).
    return b.groupby(col).apply(
        lambda d: d['CLAIM_AMOUNT'].sum() / d['FINAL_PREMIUM_SST'].sum() * 100,
        include_groups=False)


def rho(b):
    # Premium-to-count rank correlation: does dearer cover track real risk?
    return spearmanr(b['FINAL_PREMIUM_SST'], b['CLAIM_COUNT']).correlation


def retained_lr(b, drop=0.15):
    # LR after dropping the top-premium `drop` share: answers "if we shed
    # the dearest policies, does the book heal?" Lower = healthier core.
    p = b.groupby('POLID').agg(claims=('CLAIM_AMOUNT', 'sum'),
                               prem=('FINAL_PREMIUM_SST', 'sum')).reset_index()
    k = int(len(p) * drop)
    p = p.sort_values('prem', ascending=False).iloc[k:]
    return p['claims'].sum() / p['prem'].sum() * 100


def summary(books):
    # One row per priced book — works for 3 regimes or N.
    return pd.DataFrame([{'Regime': reg_label(m), 'LR (%)': round(lr(books[m]), 2),
                          'Avg prem (RM)': round(books[m]['FINAL_PREMIUM_SST'].mean(), 0),
                          'Prem-count rho': round(rho(books[m]), 3)} for m in books])


def compare_all(books, drop=0.15):
    # Full N-regime scorecard: LR, retained LR, risk alignment, avg premium.
    # The one table every comparison section (desk, main, analysis) shares.
    return pd.DataFrame([{
        'Regime': reg_label(m),
        'LR (%)': round(lr(books[m]), 2),
        f'Retained LR ({drop:.0%})': round(retained_lr(books[m], drop), 2),
        'Prem-count rho': round(rho(books[m]), 3),
        'Avg prem (RM)': round(books[m]['FINAL_PREMIUM_SST'].mean(), 0),
    } for m in books])


summary3 = summary  # alias (core-3 era name)
