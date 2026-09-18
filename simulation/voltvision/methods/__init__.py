"""Pricing methods — one module per regime.

Every module in this package defines its own `CARD` (declared parameters),
implements `price_<name>(book, card, cfg, base_cfg=None)`, and calls
`register_pricer(...)` at import time. The loader imports every module here,
so adding a method = dropping a new file (module name == regime name).

Core methods: tariff, glm, telem. See `docs/pricing.md` for the contract and
`docs/methods/*.md` for each method's rule sheet.
"""

CORE_METHODS = ('tariff', 'glm', 'telem')
