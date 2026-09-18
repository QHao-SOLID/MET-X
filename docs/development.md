# Development

## Monorepo layout

```
MET-X/                  # monorepo root
├─ simulation/          # the project (run everything from here)
├─ docs/                # this MkDocs site
├─ mkdocs.yml
├─ AGENT.md             # engineering rules + parity gate for agent work
└─ README.md            # monorepo overview
```

## Conventions (enforced)

- **Simulation is premium-independent.** Claims are shared by all pricing
  methods; premium is applied post-simulation only.
- **Pricing is a black box.** The system knows the interface, the registry, a
  blind merge of card blobs, and `PREM_<regime>` naming. All premium math lives
  in `simulation/voltvision/methods/*.py`.
- **Assumptions are data.** Edit `base_template.json` / `scenarios/*.json`;
  unknown keys are rejected, and `TEMPLATE.md` is the key reference.
- **Reproducibility is load-bearing.** Same seed + same cfg = identical book.
  Draw order and float-expression grouping are part of that contract — never
  reorder RNG calls or regroup arithmetic in `simulate.py` without evidence.
- **Readability standard.** Step functions over clever one-liners; spelled-out
  variables; comments explain *why* (units, effect of raising).

## Parity gate

Full-size, seed 42, standard books (the unified realistic system):

| Book | Tariff | GLM | Telem |
|---|---|---|---|
| ICE | 83.38 | 64.46 | 64.87 |
| EV | 59.72 | 54.72 | 55.06 |
| MIX / base | 80.08 | 65.06 | 65.16 |

Fast engine checks (legacy-free):

- quick MIX (n=1000, 2y, seed 20260916): rows **2014**,
  `pd.util.hash_pandas_object(book).sum() == 1878879944891936264`
- full MIX (n=10000, 5y, seed 20260916): rows **54118**,
  hash `12995343068305400064`
- training book (seed 42, cohort−5, 5y): rows **54006**,
  hash `5278185049816064045`

Scenario DGP patches (frequency, severity, coverage mix) intentionally change
ML numbers — the training-world rule keeps stress honest. `analysis.ipynb` §10
scores every run against `benchmarks.json` (default book: 6/6 PASS).

## Working with agents

`AGENT.md` at the repo root is the operating manual: architecture rules, file
map, commands, parity gate, practice notes and boundaries. Keep it in sync when
the layout changes (it references `simulation/...` paths).

## Docs

```bash
mkdocs serve        # live preview
mkdocs build        # static output -> site/
```

Docs embed project files via snippets (`simulation/TEMPLATE.md`,
`simulation/SOURCES.md`) so key references cannot drift.
