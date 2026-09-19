"""Shared result store: one combined file per (scenario, seed) + a manifest.

Files (all generated — never hand-edit):
  shared/results/<scenario>_s<seed>.pkl   combined book: sim columns +
                                          one PREM_<regime> column per regime
  shared/results/<scenario>_s<seed>.csv   optional copy (runner --csv)
  shared/results/manifest.json            run index: cfg + cards snapshot and
                                          metrics per (scenario, seed)

Naming rule for premiums lives in schema.py (PREM_<regime>); this module is
the only place that reads/writes it.
"""

import datetime as dt
import json
from pathlib import Path

import pandas as pd

from .schema import COLS, PREM_PREFIX, premium_column

SHARED = Path(__file__).resolve().parent.parent / 'shared'
RESULTS = SHARED / 'results'
MANIFEST = RESULTS / 'manifest.json'


def result_stem(scenario, seed):
    """File stem for one run — always seed-suffixed, e.g. 'MIX_s42'."""
    return f'{scenario}_s{int(seed)}'


def _write(df, stem):
    # parquet when pyarrow is available, pickle otherwise. Built by string
    # concatenation (never Path.with_suffix) so scenario names may contain dots.
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / f'{stem}.parquet'
    try:
        df.to_parquet(p)
    except Exception:
        p = RESULTS / f'{stem}.pkl'
        df.to_pickle(p)
    return p


def _read(stem):
    for ext, reader in (('.parquet', pd.read_parquet), ('.pkl', pd.read_pickle)):
        p = RESULTS / f'{stem}{ext}'
        if p.exists():
            return reader(p)
    raise FileNotFoundError(f'shared/results/{stem}.pkl missing — run run_scenarios.py first')


def save_result(scenario, seed, combined, csv=False):
    """Save one combined result; optional CSV copy for eyeballing."""
    p = _write(combined, result_stem(scenario, seed))
    if csv:
        combined.to_csv(RESULTS / f'{result_stem(scenario, seed)}.csv', index=False)
    return p


def load_result(scenario, seed):
    """Load one combined result (sim columns + PREM_<regime> columns)."""
    return _read(result_stem(scenario, seed))


def pick_result(preferred=None):
    """Choose a run to analyse: `preferred` = (scenario, seed) when it exists,
    else the most recently saved run in the manifest. Raises FileNotFoundError
    when no run has been produced yet."""
    manifest = load_manifest()
    if preferred and result_stem(*preferred) in manifest:
        return tuple(preferred)
    if manifest:
        newest = max(manifest.values(), key=lambda e: e.get('saved_at', ''))
        return newest['scenario'], int(newest['seed'])
    raise FileNotFoundError('no results yet - run `python run_scenarios.py` first')


def combine(book, priced):
    """Combine a simulated book and its priced books into ONE wide frame.

    Result = sim columns + PREM_<regime> per regime. Claims stay shared;
    only the premium columns differ per regime.
    """
    out = book.copy()
    for regime, priced_book in priced.items():
        out[premium_column(regime)] = priced_book['FINAL_PREMIUM_SST'].values
    return out


def premium_columns(df):
    """Regime names present in a combined result, in column order."""
    return [c[len(PREM_PREFIX):] for c in df.columns if c.startswith(PREM_PREFIX)]


def split_premiums(df):
    """{regime: premium Series} from a combined result."""
    return {regime: df[premium_column(regime)] for regime in premium_columns(df)}


def sim_book(df):
    """The simulated book (attributes + claims) without any PREM_ columns."""
    return df[COLS].copy()


def books_from_result(df):
    """{regime: DataFrame} where each frame looks like a traditionally priced
    book (single FINAL_PREMIUM_SST column) — so every reporting helper works
    unchanged for any number of regimes."""
    out = {}
    base = df[COLS].copy()
    for regime, premium in split_premiums(df).items():
        b = base.copy()
        b['FINAL_PREMIUM_SST'] = premium.values
        out[regime] = b
    return out


def load_manifest():
    """Run index {stem: entry}; empty dict when no run has happened yet."""
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding='utf-8'))
    return {}


def update_manifest(scenario, seed, path, cfg, cards, metrics):
    """Record one run: where it lives, what it assumed, how it scored."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    manifest[result_stem(scenario, seed)] = {
        'scenario': scenario,
        'seed': int(seed),
        'file': Path(path).name,
        'saved_at': dt.datetime.now().isoformat(timespec='seconds'),
        'cfg': cfg,
        'cards': {regime: dict(card) for regime, card in cards.items()},
        'metrics': metrics,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1, default=str), encoding='utf-8')
    return manifest
