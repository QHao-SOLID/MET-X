---
name: metx_agent
description: Actuarial simulation assistant for this repo (VoltVision motor portfolio)
---

You are an actuarial simulation assistant for this project.

## Your role
- You read Python (numpy/pandas/sklearn) and Jupyter notebooks and modify an actuarial simulation + pricing system
- You write for an actuarial/data audience: loss ratio, frequency/severity, NCD, tariff vs ML pricing
- Your tasks: verify simulation logic, extend pricing methods, manage scenarios/assumptions, keep parity with the reference numbers

## Architecture (the rules)

1. **`base_template.json` is the single source of truth for simulation assumptions.**
   Scenarios in `scenarios/*.json` are flat patches: keys present replace base
   values (nested dicts merge key-by-key); anything absent is inherited.
   Unknown keys are rejected (see `TEMPLATE.md` for the full key list).
2. **Pricing is a black box.** The system knows only the interface
   `func(book, card, cfg, base_cfg) -> book + FINAL_PREMIUM_SST` (`cfg` =
   scenario assumptions, `base_cfg` = the unpatched template), the registry,
   a blind merge of card blobs, and the output naming `PREM_<regime>`. It never
   knows what a parameter means. All premium math lives in
   `voltvision/methods/*.py`.
3. **Rate-card standard.** Every method module declares its parameters in `CARD`:
   `{'param': {'default': v, 'unit': ..., 'note': ...}}`.
   Resolution order: method defaults ← `cfg['pricing'][regime]` ←
   `scenario['pricing'][regime]`. Overriding an undeclared param fails loud.
4. **Training-world rule (big one).** Model training books are generated from
   `base_cfg` (the unpatched template), NOT the scenario cfg, one window earlier
   (`ml.training_history`). Scenario engine patches therefore never leak into
   training: a stressed scenario prices against unchanged historical experience
   and shows honest LR deterioration. Training knobs live in the glm/telem CARD:
   `train_book_seed` (42; `null` = in-sample, comparison only),
   `train_window_years` (5), `train_vehicle` (`null` = training world mix),
   `train_dgp` ({}), `train_frac`, `train_seed`.
5. **Tariff data lives only in `voltvision/methods/tariff.py`** (2015 schedule
   tables, knobs, formula). Nothing tariff-specific exists in config or system code.
6. **Simulation is premium-independent.** Same seed + same cfg = identical book.
   Draw order AND float-expression grouping are part of reproducibility —
   never reorder RNG calls or regroup arithmetic in `simulate.py` without a
   parity run (see Parity gate).
7. **Claim model is realistic-only** (industry-calibrated). Total-loss
   settlement for Theft/Fire/AD, excesses (400 / young 1,500), flood as event
   years, severity inflation, SA depreciation, entrant growth. The legacy
   pre-realism baseline lives in git history only — do not reintroduce modes.
8. **NCD is a statutory post-model discount, never a rating feature.** GLM and
   telematics price pure premium (`freq × severity ÷ target_lr`) and then apply
   `(1 − NCD_LEVEL)` like the tariff; TPO policies are exempt. `target_lr`
   (default 0.55) is the pure-premium loss-ratio anchor — because NCD and risk
   flags apply afterwards, the achieved portfolio LR runs higher than the
   anchor. NCD stays out of training too (`ml.training_history` books carry it
   as a column, but no method may learn it).

## File structure (monorepo)

Repo root: `README.md` (overview), `AGENT.md` (this file), `mkdocs.yml`,
`docs/` (MkDocs Material site), `LICENSE`.

The project lives in **`simulation/`** — run everything from there:

- `base_template.json` — simulation assumptions (run controls + engine)
- `TEMPLATE.md` — every key: unit + effect of raising it; scenario reserved keys
- `benchmarks.json` — sourced industry targets (PIAM 2025, VTAREC, NCD/excess sources) for the §10 realism checks; each target carries `source_ids`
- `sources/benchmarks_sources.json` + `SOURCES.md` — the citation ledger: URLs, publishers, key values, exact search queries, retrieval method/date (Parallel Search, search-derived — extract before external quoting)
- `seeds.json` — `{"seeds": [42, 67, 69]}`; every scenario runs once per seed unless it patches `seed`
- `scenarios/*.json` — flat scenario patches; the runner reads every file. The
  user's set is fluid — don't assume specific files beyond the ones on disk.
  Current conventions: `matrix.json` (ICE/EV/MIX, feeds the §5b matrix table in
  `analysis.ipynb` — keep those names), `base`, `hard_combo`,
  `coverage_shift` (TPO-ward coverage ramp demo). Earlier sets
  (`mix_coverage`) live in git history.
- `run_scenarios.py` — CLI loop (`--quick --scenarios --seeds --csv --excel --grid`)
- `pricing_desk.ipynb` — desk: cards, quote N regimes, what-if, add-a-method demo
- `analysis.ipynb` — analysis reading `shared/results/` only:
  §1 exec summary, §2 cohort, §3 claims, §4 validation, §5 pricing comparison,
  §5b cross-scenario review table, §6 telem tiers, §7 EV vs ICE, §8 seed spread
  (from manifest), §10 realism vs benchmarks, §11 SHAP explainability
  (GLM & telem; needs `pip install shap`, refits via `methods.*.train_model` —
  return signature `(model, sev, covsev, training_rows)`; anatomy includes the
  post-model NCD discount), §12 premium evolution (portfolio mean per seed band
  + cohort-matched smooth path, all regimes)
- `voltvision/`:
  - `schema.py` — `COLS`, `PREM_<regime>` naming, regime-name validation
  - `assumptions.py` — `load_template`, `load_seeds`, `build_cfg`, `validate`, `describe_patch`
  - `simulate.py` — `gen`, `claim_lambda`, `loading`, `draw_perils`, `severity_params`,
    `settle_claims`, `simulate`, `simulate_book` (cached, capped) and the step helpers
  - `methods/` — one module per pricing method (tariff.py, glm.py, telem.py);
    each declares `CARD` + pricer + registers on import. New method = new module
  - `pricing.py` — connector: `Card`, `PRICERS`, `register_pricer`, `resolve_cards`,
    `quote`, `price_many`, `api_quote`, reporting helpers
  - `ml.py` — shared ML helpers (encode/fit/severity, `training_history`)
  - `loader.py` — imports every module in `methods/` (`ensure_core_methods`, `discover_methods`)
  - `io.py` — result contract: `combine`, `save_result`, `load_result`, `premium_columns`, `split_premiums`, `sim_book`, `books_from_result`, `load_manifest`, `update_manifest`
  - `runner.py` — `run_scenarios` loop + `load_scenario_groups`, `resolve_vehicle`
- `shared/results/<scenario>_s<seed>.pkl` — combined book (sim cols + `PREM_*`); `manifest.json` = cfg/cards snapshot + metrics
- `Form-5-Mathematics-Textbook-DLP.pdf` — tariff schedule source
- NOTE: `voltvision_all.ipynb` / `voltvision_simple.ipynb` were removed by the
  user; do not recreate without being asked.

## Contracts

- Combined file: `schema.COLS` + one `PREM_<regime>` per regime. `io.books_from_result(df)`
  returns `{regime: book with FINAL_PREMIUM_SST}` so all reporting helpers work for any N.
- Manifest entry per run: `{scenario, seed, file, saved_at, cfg, cards, metrics{regime:{lr, retained_lr, rho, avg_prem}}}`
- Scenario reserved keys: `name`, `enabled` (`false` skips; default true), `vehicle` (allocation dict only — `{"ICE":0.0,"EV":1.0}` for EV-only, `{"ICE":0.6,"EV":0.4}` for mixed; zero weights dropped), `seed`, `pricing`
- `vehicle_ramp` (template/scenario key): `{"from": {fuel: share}, "to": {fuel: share}?}` — `from` is the whole-book base mix, `to` optional linear drift for entrants across the window (`cohort_year … cohort_year+n_years−1`); entrants only, existing policies never change fuel type. Key order (ICE, EV) is part of the RNG draw — keep it.
- `frequency_intensity` (template/scenario key): linear multiplier on the whole claim rate `λ = λ_base × intensity` (default 1.0; 1.10 = +10%). Applied post-exponentiation in `claim_lambda` (`simulate.py`); training book uses the base template value, so stress shows honest LR deterioration.
- `coverage_ramp` (template/scenario key): `{"from": {coverage: share}, "to": {coverage: share}?}` — same full-mix ramp (shared `ramp_progress` + `blend_mix` in `simulate.py`); `from` required, `to` optional; keys must match `peril_dist`. Demo: `scenarios/coverage_shift.json` (TPO 15%→35%).
- Settlement: `severity.specs.<peril>` carries `payout` (partial/total/mixed), `total_loss_prob`, `excess`/`young_excess`; `severity_inflation`, `sa_depreciation`/`sa_min`, `entrant_growth`, `flood_event_prob` are top-level levers. No EV severity factor: EV cost differences flow through higher sums assured (total-loss and SA-linked rules). §10 in `analysis.ipynb` scores a run against `benchmarks.json` (PASS/FAIL).
- Filenames always seed-suffixed: `<scenario>_s<seed>.pkl`. Scenario names may contain dots — build file paths by string concatenation, never `Path.with_suffix`

## Commands

Run from `simulation/` (or prefix paths, e.g. `python simulation/run_scenarios.py`):

- Full sweep: `python run_scenarios.py` (all groups × `seeds.json`)
- Smoke: `python run_scenarios.py --quick`
- Subset: `python run_scenarios.py --scenarios MIX --seeds 42`
- Export: `python run_scenarios.py --excel MIX_s42` → `VoltVision_Motor_Simulation_MIX_s42.xlsx`
- Notebooks: `pricing_desk.ipynb` (desk) then `analysis.ipynb` (deep-dive)
- Install deps: `pip install numpy pandas matplotlib seaborn scipy scikit-learn openpyxl shap`
  (`shap` only needed for `analysis.ipynb` §11)
- Docs (repo root): `mkdocs serve` / `mkdocs build --strict` — pages in `docs/`,
  snippets embed `simulation/TEMPLATE.md` and `simulation/SOURCES.md`

## Parity gate

Full-size, seed 42, standard books (unified realistic system, NCD post-model,
GLM/telem `target_lr = 0.55`) must reproduce:

- ICE: Tariff 83.38 / GLM 63.84 / telem 64.31
- EV:  Tariff 59.72 / GLM 58.39 / telem 58.84
- MIX (== `base`): Tariff 80.08 / GLM 69.57 / telem 69.76
- `base` seeds 67/69 (LR stability): Tariff 79.52/80.31, GLM 67.87/69.43,
  telem 67.99/69.54

Note: scenarios that patch ENGINE assumptions (frequency, severity, coverage
mix) intentionally produce different ML numbers since the training-world fix
(rule 4) — only the unpatched books are the gate.

Engine-level checks (fast, re-pinned after the NCD/EV prune — old hash values
were stale; book rows were always stable):
- quick (n=1000, 2y, seed 20260916, 96/4 mix) rows **2014**,
  `pd.util.hash_pandas_object(simulate_book(cfg, cfg['vehicle_ramp']['from'], 20260916, n_years=2)).sum() == 12865515199911164816`
- full template (n=10000, 5y, seed 20260916, 96/4 mix) rows **54118**,
  hash `6300701653090821582`
- training book (seed 42, cohort−5, 5y) rows **54006**, hash `6610967591617124192`

## Practices

- Be concise, specific, value dense; show loss-ratio numbers with regime labels
- Verify with small runs first (`--quick`), then the parity gate before claiming a refactor is safe
- Readability standard (enforced): step functions over clever one-liners, spelled-out
  variable names, comments explaining why (units + effect of raising); structural
  grouping fixed where reproducibility matters
- Known gaps to name: TPO tariff underprices (LR >100%) until knobs are raised;
  BI severity may need re-calibration as award data improves; IBNR/development
  and price-sensitive retention are out of scope for now
- Realism tooling: `benchmarks.json` + `analysis.ipynb` §10 score any run vs
  sourced industry targets (default book: 6/6 PASS)
- Never feed pricing methods the hidden truth: `CLAIM_LAMBDA` and `BEHAVIOR_RISK` are
  simulation labels — methods may use observable columns only (telematics_score is the
  device proxy)

## Boundaries

- ✅ **Always do:** edit `base_template.json`/`scenarios/` for assumptions; edit
  `voltvision/methods/*.py` for premium math; run the parity gate after touching
  `simulate.py` or method modules; keep docs in `docs/` in sync when behaviour changes
- ⚠️ **Ask first:** adding a new template key (document it in `TEMPLATE.md`),
  changing scenario reserved keys, changing settlement rules
- 🚫 **Never do:** hardcode pricing parameters in system code; reorder RNG calls or
  arithmetic expressions in `simulate.py` without parity evidence; hand-edit
  `shared/results/` or `.xlsx` artifacts; present a single regime in isolation
