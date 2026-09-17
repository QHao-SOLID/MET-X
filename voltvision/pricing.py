"""Pricing connector — pricing is a BLACK BOX behind a standard rate card.

What the system knows (and nothing more):
  - the interface:   func(book, card, cfg, base_cfg) -> book + FINAL_PREMIUM_SST
    (cfg = scenario assumptions, base_cfg = the unpatched template; methods may
    use them for loadings or to build their own training data — they carry no
    pricing knowledge)
  - the standard card: one Card per regime; params are declared BY THE METHOD
  - resolution order: method defaults <- cfg['pricing'][regime]
                      <- scenario['pricing'][regime]   (later wins)
  - output naming:   schema.PREM_<regime> for combined result files

The connector never interprets a parameter: values are opaque and forwarded.
How a premium is computed lives in the 02x notebooks' CALC cells, which
declare their card and register themselves:

    CARD = {'sst': {'default': 0.08, 'unit': 'fraction', 'note': '...'}, ...}
    register_pricer('tariff', price_tariff, card=CARD, info={'label': 'Tariff'})

Rules for every method cell:
  - input is a SIMULATED book (never raw gen() output);
  - do not mutate the input (copy first);
  - output = input columns + FINAL_PREMIUM_SST (RM, SST-inclusive);
  - read every number from the card (defaults declared in the cell);
  - always compare regimes side by side — never show one regime alone.
"""

import pandas as pd
from scipy.stats import spearmanr

from .assumptions import deep_merge
from .schema import check_regime_name

# Fallback bar colors for regimes that do not declare one.
_PALETTE = ['#8b5cf6', '#06b6d4', '#ef4444', '#10b981', '#f97316', '#a3e635']


class Card(dict):
    """Resolved rate card for ONE regime: standard container, opaque contents.

    Access reads like the method cell: card.tpo_loading == card['tpo_loading'].
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(
                f"card has no parameter {name!r} — declared: {sorted(self)}") from None


# Registry: name -> {'func', 'card' (declared defaults), 'info' (label/formula/color)}
PRICERS = {}


def reg_label(name):
    """Display label for a regime: method-declared, else the raw name."""
    return PRICERS.get(name, {}).get('info', {}).get('label', name)


def reg_color(name):
    """Bar color for a regime: method-declared, else deterministic fallback."""
    info = PRICERS.get(name, {}).get('info', {})
    if 'color' in info:
        return info['color']
    return _PALETTE[abs(hash(name)) % len(_PALETTE)]


# Columns a book must have before quoting (i.e. it came from simulate.py).
_REQUIRED_BOOK_COLS = ('SIM_YEAR', 'COHORT_YEAR', 'POLID', 'CLAIM_COUNT',
                       'CLAIM_AMOUNT', 'NCD_LEVEL')


def register_pricer(name, func, card=None, info=None):
    """A method cell calls this last: name it, hand over the function, declare
    the card (defaults + unit + note per param) and optional presentation info
    ({'label', 'formula', 'color'}). Same name twice = latest wins.
    """
    check_regime_name(name)
    if not callable(func):
        raise TypeError("pricer must be callable(book, card)")
    if card:
        unknown = [k for k, v in card.items()
                   if not (isinstance(v, dict) and 'default' in v)]
        if unknown:
            raise ValueError(
                f"regime {name!r}: card entries must be "
                f"{{'default': ..., 'unit': ..., 'note': ...}} — bad: {unknown}")
    PRICERS[name] = {'func': func, 'card': dict(card or {}), 'info': dict(info or {})}
    return func


def describe_pricer(name):
    """Interface sheet for one regime, rendered from the method's declaration."""
    entry = PRICERS.get(name)
    if entry is None:
        return {'regime': name, 'label': name, 'params': [], 'formula': 'not registered'}
    return {
        'regime': name,
        'label': reg_label(name),
        'formula': entry['info'].get('formula', ''),
        'params': [{'name': k, **v} for k, v in entry['card'].items()],
    }


def card_defaults(name):
    """The method's declared default parameters ({param: value})."""
    entry = PRICERS.get(name)
    if entry is None:
        raise ValueError(f"unknown pricing regime {name!r}; "
                         f"registered: {sorted(PRICERS)}")
    return {k: v['default'] for k, v in entry['card'].items()}


def resolve_cards(cfg, scenario=None, regimes=None):
    """Build one resolved rate card per regime.

    Precedence: method defaults <- template pricing[regime] <- scenario
    pricing[regime]. Overrides must name a declared parameter — typos fail
    loud here instead of silently doing nothing deep inside a pricer.
    """
    regimes = list(regimes or cfg['regimes'])
    template_overrides = cfg.get('pricing', {}) or {}
    scenario_overrides = (scenario or {}).get('pricing', {}) or {}

    unknown_regimes = set(template_overrides) | set(scenario_overrides)
    unknown_regimes -= set(regimes)
    if unknown_regimes:
        raise ValueError(f"pricing overrides for regimes not run: {sorted(unknown_regimes)} "
                         f"(running: {regimes})")

    cards = {}
    for regime in regimes:
        defaults = card_defaults(regime)
        for source, blob in (('template', template_overrides), ('scenario', scenario_overrides)):
            override = blob.get(regime, {})
            unknown = [k for k in override if k not in defaults]
            if unknown:
                raise ValueError(
                    f"unknown param(s) {unknown} for regime {regime!r} in {source} pricing — "
                    f"declared: {sorted(defaults)}")
            defaults = deep_merge(defaults, override)
        cards[regime] = defaults
    return cards


def _check_book(book, regime):
    # Fail fast with a useful message: pricing a raw gen() book (no claims)
    # is the classic wiring mistake — catch it here, not three frames deep.
    missing = [c for c in _REQUIRED_BOOK_COLS if c not in book.columns]
    if missing:
        raise ValueError(
            f"cannot quote {regime!r}: book lacks {missing} — "
            "price SIMULATED books (runner output), never raw gen() output")


def quote(book, regime, card, cfg, base_cfg=None):
    """Connector: price one simulated book under one regime.

    Request = (book, regime, card, cfg, base_cfg).
    Response = book + FINAL_PREMIUM_SST.
    base_cfg: the unpatched template assumptions (None -> same as cfg).
    """
    _check_book(book, regime)
    entry = PRICERS.get(regime)
    if entry is None:
        raise ValueError(f"unknown pricing regime {regime!r}; "
                         f"registered: {sorted(PRICERS)}")
    if not isinstance(card, Card):
        card = Card(card)
    out = entry['func'](book, card, cfg, base_cfg)
    if 'FINAL_PREMIUM_SST' not in out.columns:
        raise RuntimeError(f"pricer {regime!r} did not set FINAL_PREMIUM_SST")
    return out


def price_many(book, regimes, cards, cfg, base_cfg=None):
    """Price the SAME book N ways: {regime: resolved card} -> {regime: book}."""
    return {regime: quote(book, regime, cards[regime], cfg, base_cfg)
            for regime in regimes}


def api_quote(book, regime, card, cfg, base_cfg=None):
    """Standard API output for one quote: identity + inputs + metrics + book."""
    priced = quote(book, regime, card, cfg, base_cfg)
    return {
        'regime': regime,
        'label': reg_label(regime),
        'card': dict(card),
        'metrics': {
            'lr': round(lr(priced), 2),
            'avg_prem': round(float(priced['FINAL_PREMIUM_SST'].mean()), 0),
            'rho': round(float(rho(priced)), 3),
            'rows': len(priced),
        },
        'book': priced,
    }


def discover_methods(root=None, pattern='02*.ipynb'):
    # Find every method notebook (any 02*.ipynb with a tagged calc cell) and
    # register whatever each one owns. New 02d_x.ipynb joins with zero
    # connector edits — just add the file. Returns {regime: notebook}.
    from .loader import calc_source, CORE_METHODS
    from pathlib import Path
    root = Path(root or '.')
    found = {}
    for nb in sorted(root.glob(pattern)):
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
    missing = [m for m in CORE_METHODS if m not in PRICERS]
    if missing:
        raise RuntimeError(f"core regimes missing after discovery: {missing}")
    return found


def ensure_core_methods(root=None):
    # Load tariff/glm/telem calculations from their 02x notebooks.
    # Call once before quoting. No-op for already-registered methods.
    from .loader import ensure_methods, CORE_METHODS
    return ensure_methods(root=root, methods=CORE_METHODS)


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
    # LR after dropping the top-premium `drop` share: "if we shed the dearest
    # policies, does the book heal?" Lower = healthier core.
    p = b.groupby('POLID').agg(claims=('CLAIM_AMOUNT', 'sum'),
                               prem=('FINAL_PREMIUM_SST', 'sum')).reset_index()
    k = int(len(p) * drop)
    p = p.sort_values('prem', ascending=False).iloc[k:]
    return p['claims'].sum() / p['prem'].sum() * 100


def summary(books, drop=0.15):
    # One row per priced book — works for 3 regimes or N.
    return pd.DataFrame([{'Regime': reg_label(m), 'LR (%)': round(lr(books[m]), 2),
                          'Avg prem (RM)': round(books[m]['FINAL_PREMIUM_SST'].mean(), 0),
                          'Prem-count rho': round(rho(books[m]), 3)} for m in books])


def compare_all(books, drop=0.15):
    # Full N-regime scorecard: LR, retained LR, alignment, avg premium.
    return pd.DataFrame([{
        'Regime': reg_label(m),
        'LR (%)': round(lr(books[m]), 2),
        f'Retained LR ({drop:.0%})': round(retained_lr(books[m], drop), 2),
        'Prem-count rho': round(rho(books[m]), 3),
        'Avg prem (RM)': round(books[m]['FINAL_PREMIUM_SST'].mean(), 0),
    } for m in books])
