"""The loop: for each scenario × seed → simulate → price → combine → save.

One combined file per run: shared/results/<scenario>_s<seed>.pkl (sim columns
plus one PREM_<regime> column per regime) and a manifest entry holding the
cfg/cards snapshot and the per-regime metrics. Analysis reads only these.

Pricing is a black box here: the runner resolves each method's rate card from
declared defaults + template/scenario overrides and hands it over untouched.
"""

import json
import time
from pathlib import Path

import pandas as pd

from .assumptions import (
    TEMPLATE_KEYS, build_cfg, deep_merge, describe_patch, load_seeds,
    load_template,
)
from .pricing import (
    ensure_core_methods, lr, price_many, reg_label, resolve_cards, retained_lr,
    rho,
)
from .simulate import normalize_mix, simulate_book
from . import io


def load_scenario_groups(grid):
    """Scenario groups from a directory of *.json files (or a single file).

    Each file is a JSON list of scenario dicts; the file stem becomes the
    group name. Returns [(group_name, [scenario, ...]), ...] in file order.
    """
    p = Path(grid)
    files = sorted(p.glob('*.json')) if p.is_dir() else [p]
    if not files:
        raise FileNotFoundError(f'no scenario files found in {grid}')
    groups = []
    for f in files:
        scenarios = json.loads(f.read_text(encoding='utf-8'))
        if not isinstance(scenarios, list) or not scenarios:
            raise ValueError(f'{f.name}: expected a non-empty JSON list of scenarios')
        groups.append((f.stem, scenarios))
    return groups


def resolve_vehicle(vehicle, cfg):
    """Vehicle allocation for one scenario.

    Explicit allocation dict wins (e.g. {"ICE": 0.0, "EV": 1.0} for an
    EV-only book); absent -> the template's `vehicle_ramp.from`. Zero weights
    are dropped, so a fuel at 0% behaves exactly like an absent fuel.
    """
    if vehicle is None:
        return normalize_mix(cfg['vehicle_ramp']['from'])
    if not isinstance(vehicle, dict):
        raise ValueError(
            f'vehicle must be an allocation dict, e.g. {{"ICE": 0.0, "EV": 1.0}} '
            f'or {{"ICE": 0.6, "EV": 0.4}} — got {vehicle!r}')
    unknown = set(vehicle) - set(cfg['vehicle_ramp']['from'])
    if unknown:
        raise ValueError(f'vehicle has unknown fuel(s) {sorted(unknown)} — '
                         f'known: {sorted(cfg["vehicle_ramp"]["from"])}')
    return normalize_mix(vehicle)


def _metrics(priced, drop):
    # Per-regime report card stored in the manifest.
    return {
        regime: {
            'lr': round(lr(b), 2),
            'retained_lr': round(retained_lr(b, drop), 2),
            'rho': round(rho(b), 4),
            'avg_prem': round(float(b['FINAL_PREMIUM_SST'].mean()), 0),
        }
        for regime, b in priced.items()
    }


def run_scenarios(grid='scenarios', template=None, scenario_names=None,
                  seeds=None, quick=False, csv=False, verbose=True):
    """Execute scenario groups and write combined results + manifest.

    grid            directory of scenario JSON files (or one file)
    template        base assumptions dict (default: base_template.json)
    scenario_names  optional subset filter by scenario name
    seeds           optional explicit seed list (default: seeds.json, else
                    the template seed; a scenario patching 'seed' runs once)
    quick           smoke mode: n=1000, n_years=2
    csv             also write a CSV copy of each combined result

    Returns a tidy DataFrame: scenario, seed, regime, lr, retained_lr, rho,
    avg_prem, vehicle, file.
    """
    ensure_core_methods()
    base = template if template is not None else load_template()
    if quick:
        base = deep_merge(base, {'n': 1000, 'n_years': 2})
    seed_list = seeds if seeds is not None else (load_seeds() or [base['seed']])

    rows = []
    for group, scenarios in load_scenario_groups(grid):
        selected = [s for s in scenarios
                    if s.get('enabled', True) is not False
                    and (not scenario_names or s['name'] in scenario_names)]
        skipped = [s['name'] for s in scenarios if s.get('enabled', True) is False]
        if verbose and skipped:
            print(f"\n=== {group} | skip (disabled): {', '.join(skipped)}")
        if not selected:
            continue
        for scenario in selected:
            name = scenario['name']
            cfg = build_cfg(base, scenario)
            vehicle = resolve_vehicle(scenario.get('vehicle'), cfg)
            regimes = list(cfg['regimes'])
            cards = resolve_cards(cfg, scenario, regimes)
            scenario_seeds = [scenario['seed']] if 'seed' in scenario else seed_list

            if verbose:
                print(f"\n=== {group} / {name} | vehicle={vehicle} "
                      f"| seeds={scenario_seeds} | regimes={regimes}")
                for line in describe_patch(base, scenario):
                    print(f"    patch {line}")

            for seed in scenario_seeds:
                started = time.time()
                book = simulate_book(cfg, vehicle, seed, n_years=cfg['n_years'],
                                     cache=False)
                # base_cfg = unpatched template: methods build training data
                # from the historical (base) world, not the scenario's DGP.
                priced = price_many(book, regimes, cards, cfg, base_cfg=base)
                combined = io.combine(book, priced)
                path = io.save_result(name, seed, combined, csv=csv)
                metrics = _metrics(priced, cfg['reporting']['retained_drop'])
                io.update_manifest(name, seed, path, cfg, cards, metrics)

                for regime in regimes:
                    m = metrics[regime]
                    rows.append({'scenario': name, 'seed': seed, 'regime': regime,
                                 'lr': m['lr'], 'retained_lr': m['retained_lr'],
                                 'rho': m['rho'], 'avg_prem': m['avg_prem'],
                                 'vehicle': vehicle, 'file': Path(path).name})
                    if verbose:
                        print(f"    seed {seed} | {reg_label(regime):<16} "
                              f"LR {m['lr']:>6.2f}%  rho {m['rho']:.3f}  "
                              f"avg prem RM{m['avg_prem']:,.0f}")
                if verbose:
                    print(f"    -> {path.name} ({time.time() - started:.0f}s)")

    return pd.DataFrame(rows)


def scenario_table(results):
    """Compact scenario × seed × regime view of run_scenarios output."""
    if results.empty:
        return results
    return results.pivot_table(index=['scenario', 'seed'], columns='regime',
                               values='lr', aggfunc='mean')
