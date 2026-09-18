"""VoltVision motor helpers: premium-independent simulation + pricing connector.

Layout (assumptions in JSON, calculations in notebooks, system connects):
  schema.py       COLS, PREM_<regime> naming rule, structural checks
  assumptions.py  base_template.json + scenario patches + seeds.json
  simulate.py     gen / claim_lambda / loading / simulate / simulate_book
  pricing.py      BLACK BOX connector: Card, registry, quote / price_many,
                  resolve_cards, reporting helpers
  ml.py           shared helpers for ML pricing methods (fit/severity/encode)
  loader.py       replays 02x CALC cells so every caller quotes identical methods
  io.py           shared/results read/write: combined books + manifest
  runner.py       the scenario x seed loop (used by run_scenarios.py)
"""

from .schema import COLS, PREM_PREFIX, premium_column, check_regime_name
from .assumptions import (
    load_template, load_seeds, build_cfg, validate, describe_patch, deep_merge,
)
from .simulate import gen, claim_lambda, loading, simulate, simulate_book
from .pricing import (
    Card, PRICERS, register_pricer, describe_pricer, card_defaults, resolve_cards,
    quote, price_many, api_quote, discover_methods, ensure_core_methods,
    reg_label, reg_color, lr, lr_by, rho, retained_lr, summary, compare_all,
)
from .loader import ensure_methods, CORE_METHODS
from .runner import run_scenarios
from . import io

__version__ = "0.2.0"

__all__ = [
    "COLS", "PREM_PREFIX", "premium_column", "check_regime_name",
    "load_template", "load_seeds", "build_cfg", "validate", "describe_patch", "deep_merge",
    "gen", "claim_lambda", "loading", "simulate", "simulate_book",
    "Card", "PRICERS", "register_pricer", "describe_pricer", "card_defaults",
    "resolve_cards", "quote", "price_many", "api_quote",
    "discover_methods", "ensure_core_methods", "ensure_methods", "CORE_METHODS",
    "reg_label", "reg_color",
    "lr", "lr_by", "rho", "retained_lr", "summary", "compare_all",
    "run_scenarios", "io",
]
