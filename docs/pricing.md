# Pricing — the black-box contract

Pricing is a black box behind a standard interface. The system never knows what
a method's parameters mean; each method declares its own rate card.

**Methods are Python modules** in `simulation/voltvision/methods/` — one file per
regime, imported automatically by the loader.

## Interface

```python
func(book, card, cfg, base_cfg) -> book + FINAL_PREMIUM_SST
```

| Argument | Meaning |
|---|---|
| `book` | a **simulated** book (never raw `gen()` output) |
| `card` | resolved rate card for this regime (`Card`, dict with attribute access) |
| `cfg` | scenario assumptions (simulation config) |
| `base_cfg` | unpatched template — methods build training data from this world |

Rules for every method module:

- copy the input (never mutate); output = input columns + `FINAL_PREMIUM_SST`
  (RM, SST-inclusive)
- read every number from the card (defaults declared in the module)
- end with `register_pricer(name, func, card=CARD, info={...})`

## Rate-card standard

Each module declares its parameters:

```python
CARD = {
  'target_lr': {'default': 0.55, 'unit': 'loss-ratio anchor', 'note': 'pure premium / target_lr'},
  ...
}
register_pricer('glm', price_glm, card=CARD, info={'label': 'GLM', 'color': '#f59e0b'})
```

Resolution order (later wins):

```
method defaults  <-  cfg['pricing'][regime]  <-  scenario['pricing'][regime]
```

Overriding an undeclared parameter fails loud. Labels/colors are declared by
each method (fallbacks exist), so nothing about the current methods is hardcoded
in the system.

## Dispatch

```python
from voltvision import ensure_core_methods, resolve_cards, quote, price_many, api_quote

ensure_core_methods()               # import every module in voltvision/methods/
cards = resolve_cards(cfg)          # per-regime resolved cards
books = price_many(book, cfg['regimes'], cards, cfg, base_cfg=cfg)
```

`quote(book, regime, card, cfg, base_cfg)` handles one regime;
`api_quote(...)` returns `{regime, label, card, metrics, book}`.

## Output naming (N regimes)

Combined results carry one premium column per regime: `PREM_<regime>`
(e.g. `PREM_tariff`, `PREM_glm`, `PREM_telem`, `PREM_flat_demo`).
`io.books_from_result()` renames a regime's column back to
`FINAL_PREMIUM_SST`, so all reporting helpers work for any N.

## Adding a method

1. Drop a new module in `simulation/voltvision/methods/` (module name = regime
   name) exporting `CARD` and a `price_<name>(book, card, cfg, base_cfg)`
   function, ending with `register_pricer(...)`.
2. Call `ensure_core_methods()` — the loader discovers every module, no
   connector edits.
3. Add the regime name to `regimes` in the template or a scenario patch.
4. Its column and manifest rows appear automatically.

The `pricing_desk.ipynb` notebook contains a minimal `flat_demo` pricer showing
the full pattern inline.

## Current methods

| Regime | Rule sheet | Code |
|---|---|---|
| `tariff` | [Tariff](methods/tariff.md) | `voltvision/methods/tariff.py` |
| `glm` | [GLM](methods/glm.md) | `voltvision/methods/glm.py` |
| `telem` | [Telematics](methods/telem.md) | `voltvision/methods/telem.py` |

GLM/telem train **out-of-sample** on a separate historical book from the base
world (rule: training never sees scenario DGP patches). `train_book_seed: null`
reverts to in-sample for comparison.
