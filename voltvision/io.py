"""Shared artifact store: notebooks exchange books via shared/ (parquet, pickle fallback).

Files (all generated — never hand-edit):
  sim_<SCEN>            raw simulated book (simulate.py output, no premium)
  priced_<SCEN>_<reg>   priced book (FINAL_PREMIUM_SST included)
  config                CFG dict snapshot (reproducibility record)

Parquet needs pyarrow; without it we fall back to pickle automatically.
"""

from pathlib import Path

import pandas as pd

# The shared/ folder next to this package (repo root/shared).
SHARED = Path(__file__).resolve().parent.parent / "shared"


def _write(df, stem):
    # Save one book; return the path written. Parquet first (fast, typed),
    # pickle only if parquet is unavailable in this environment.
    SHARED.mkdir(parents=True, exist_ok=True)
    try:
        p = SHARED / f"{stem}.parquet"
        df.to_parquet(p)
    except Exception:
        p = SHARED / f"{stem}.pkl"
        df.to_pickle(p)
    return p


def _read(stem):
    # Load one book; parquet wins if both exist (same stem, both formats).
    for ext, fn in (("parquet", pd.read_parquet), ("pkl", pd.read_pickle)):
        p = SHARED / f"{stem}.{ext}"
        if p.exists():
            return fn(p)
    raise FileNotFoundError(
        f"shared/{stem}.parquet (or .pkl) missing — run 01_simulation.ipynb first")


def save_sim(scen, book):
    # Raw simulated book for one scenario (no premium columns).
    return _write(book, f"sim_{scen}")


def load_sim(scen):
    # Raw simulated book for one scenario.
    return _read(f"sim_{scen}")


def save_priced(scen, regime, book):
    # Priced book for one scenario + regime (FINAL_PREMIUM_SST included).
    return _write(book, f"priced_{scen}_{regime}")


def load_priced(scen, regime):
    # Priced book for one scenario + regime.
    return _read(f"priced_{scen}_{regime}")


def save_config(cfg):
    # CFG snapshot as JSON (tuples become strings — record, not reloadable).
    import json
    SHARED.mkdir(parents=True, exist_ok=True)
    p = SHARED / "config.json"
    p.write_text(json.dumps(cfg, indent=2, default=str), encoding="utf-8")
    return p
