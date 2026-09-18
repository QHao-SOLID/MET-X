# MET-X — monorepo

Malaysian motor insurance simulation + pricing lab (IFoA VoltVision),
organised as a monorepo:

| Component | Path | What it is |
|---|---|---|
| **Simulator** | [`simulation/`](simulation/) | The project: premium-independent engine, blackbox pricing methods, scenario runner, notebooks, results |
| **Documentation** | [`docs/`](docs/) | MkDocs (Material) site — architecture, assumptions, guides, sources |
| **Agent playbook** | [`AGENT.md`](AGENT.md) | Rules and parity discipline for AI/agent work on this repo |

## Quickstart

```bash
pip install numpy pandas matplotlib seaborn scipy scikit-learn openpyxl   # simulator
pip install mkdocs-material                                               # docs

cd simulation
python run_scenarios.py --quick            # smoke run -> shared/results/
python run_scenarios.py                    # full sweep (all scenarios x seeds.json)
```

Docs:

```bash
mkdocs serve        # http://127.0.0.1:8000
mkdocs build        # static site -> site/
```

## Read the docs

- [Overview](docs/index.md)
- [Getting started](docs/getting-started.md)
- [How the simulation works](docs/how-the-simulation-works.md)
- [Assumptions (base_template)](docs/assumptions.md)
- [Scenarios](docs/scenarios.md)
- [Claim settlement & realism](docs/claim-model.md)
- [Pricing (blackbox contract)](docs/pricing.md)
- [Analysis](docs/analysis.md)
- [Benchmarks & sources](docs/sources.md)

## Layout

```
MET-X/
├─ README.md            <- you are here (monorepo overview)
├─ AGENT.md             <- agent rules, parity gate, boundaries
├─ mkdocs.yml           <- docs site config
├─ docs/                <- documentation source (Markdown + Mermaid)
├─ LICENSE
└─ simulation/          <- the project
   ├─ base_template.json  seeds.json  benchmarks.json
   ├─ scenarios/*.json    shared/results/<scenario>_s<seed>.pkl + manifest.json
   ├─ sources/            SOURCES.md  benchmarks ledger
   ├─ voltvision/         engine, connector, runner, io
   │  └─ methods/         pricing methods: tariff.py, glm.py, telem.py
   ├─ pricing_desk.ipynb  pricing desk
   └─ analysis.ipynb      analysis (reads results only)
```
