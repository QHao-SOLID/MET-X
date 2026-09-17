"""VoltVision motor helpers: premium-independent simulation + pricing connector.

Layout (calculations live in notebooks; package only connects):
  config.py    constants, CFG, tariff tables, canonical column order
  simulate.py  gen(), claim_lambda(), loading(), simulate() — the engine
  pricing.py   RateCard, registry, quote/api_quote/price_many, reporting
  loader.py    replays 02x CALC cells so hub/runner quote notebook-owned math
  io.py        shared/ artifact read/write (parquet, pickle fallback)
"""

from .config import (
    REGIMES, LABEL, COLOR, N_YEARS, SEED,
    VEHICLE_SCENARIO, SCEN, CFG,
    BANDS, BASIC_COMP, BASIC_TPO, PER_EXTRA, PERIL_DIST, COLS,
)
from .simulate import gen, claim_lambda, loading, simulate
from .pricing import (
    RateCard, FEATS_G, PRICERS, PRICER_INFO, describe_pricer,
    register_pricer, ensure_core_methods, discover_methods,
    encode_features, fit_frequency, severity_table,
    quote, api_quote, price_many,
    reg_color, reg_label, lr, lr_by, rho,
    retained_lr, summary, compare_all,
)
from .loader import ensure_methods, CORE_METHODS
from .stress import deep_update, run_stress, stress_summary, stress_pivot
from . import io

__version__ = "0.1.0"

__all__ = [
    "REGIMES", "LABEL", "COLOR", "N_YEARS", "SEED",
    "VEHICLE_SCENARIO", "SCEN", "CFG",
    "BANDS", "BASIC_COMP", "BASIC_TPO", "PER_EXTRA", "PERIL_DIST", "COLS",
    "gen", "claim_lambda", "loading", "simulate",
    "RateCard", "FEATS_G", "PRICERS", "PRICER_INFO", "describe_pricer",
    "register_pricer", "ensure_core_methods", "discover_methods",
    "ensure_methods", "CORE_METHODS",
    "encode_features", "fit_frequency", "severity_table",
    "quote", "api_quote", "price_many",
    "reg_color", "reg_label",
    "lr", "lr_by", "rho", "retained_lr", "summary",
    "compare_all", "io",
    "deep_update", "run_stress", "stress_summary", "stress_pivot",
]
