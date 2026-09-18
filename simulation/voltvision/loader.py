"""Method loader: pricing methods live in `voltvision/methods/*.py`.

Each method module defines `CARD`, implements its pricer, and calls
`register_pricer(...)` at import time. The loader imports every module in the
package — so a new file joins the desk with zero connector edits — and then
verifies the core regimes are registered.

Module name == regime name by convention (tariff.py registers 'tariff').
"""

import importlib
import pkgutil

from . import methods as methods_pkg
from .methods import CORE_METHODS


def method_modules():
    """{module_name: source_path} for every method module in the package."""
    return {m.name: f'voltvision/methods/{m.name}.py'
            for m in pkgutil.iter_modules(methods_pkg.__path__)
            if not m.name.startswith('_')}


def ensure_methods(root=None, methods=None):
    """Import missing method modules; returns the PRICERS registry.

    `methods` optionally narrows the import set (iterable of module names);
    `root` is accepted for API compatibility and ignored.
    """
    from .pricing import PRICERS
    names = list(methods) if methods is not None else list(method_modules())
    for name in names:
        if name in PRICERS:
            continue
        print(f"loader: importing voltvision/methods/{name}.py")
        importlib.import_module(f'.methods.{name}', __package__)
    missing = [m for m in CORE_METHODS if m not in PRICERS]
    if missing:
        raise RuntimeError(f'core regimes missing after loading: {missing}')
    return PRICERS
