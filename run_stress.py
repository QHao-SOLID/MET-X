"""Run a stress grid headless: scenarios x seeds x regimes -> tidy results.

Loads a grid (default stress_grid.py, or a .py/.json path), simulates every
(scenario, seed) once, prices each regime with the scenario's card overrides,
prints pivots, and saves results to shared/ (CSV + parquet/pickle).

Examples:
  python run_stress.py --quick --seeds 0            # smoke: fast, 1 seed
  python run_stress.py                              # full grid, 3 seeds
  python run_stress.py --scenarios base,freq_x1.22,tpo_heavy
  python run_stress.py --grid my_grid.py --seeds 0,1,2,3,4
  python run_stress.py --regimes tariff,glm --vehicle EV
"""

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from voltvision import REGIMES, io  # noqa: E402
from voltvision.stress import run_stress, stress_summary, stress_pivot  # noqa: E402


def load_grid(path):
    # Import a .py grid module by path, or parse a .json list of scenarios.
    if path.endswith('.json'):
        return json.load(open(path, encoding='utf-8'))
    spec = importlib.util.spec_from_file_location('stress_grid', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SCENARIOS


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description='VoltVision stress runner')
    ap.add_argument('--grid', default='stress_grid.py', help='grid file (.py or .json)')
    ap.add_argument('--seeds', default='0,1,2', help='comma-separated sim seeds')
    ap.add_argument('--scenarios', default='', help='subset of scenario names (default: all)')
    ap.add_argument('--regimes', default=','.join(REGIMES), help='regimes to price')
    ap.add_argument('--vehicle', default='MIX', help='default vehicle book (ICE|EV|MIX)')
    ap.add_argument('--quick', action='store_true', help='n=1000, 2 years per run')
    ap.add_argument('--no-save', action='store_true', help='skip writing results')
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    grid = load_grid(args.grid)
    if args.scenarios:
        keep = {s.strip() for s in args.scenarios.split(',') if s.strip()}
        grid = [s for s in grid if s['name'] in keep]
    seeds = tuple(int(s) for s in args.seeds.split(',') if s.strip())
    regimes = [r.strip() for r in args.regimes.split(',') if r.strip()]
    print(f"grid={args.grid} scenarios={[s['name'] for s in grid]} "
          f"seeds={seeds} regimes={regimes} vehicle={args.vehicle} quick={args.quick}")

    df = run_stress(grid, seeds=seeds, regimes=regimes, vehicle=args.vehicle,
                    quick=args.quick)

    print('\n=== mean LR by scenario x regime ===')
    print(stress_pivot(df, 'lr', 'mean').round(2).to_string())
    if len(df) > len(grid) * len(regimes):          # more than one seed -> spread
        print('\n=== P(LR > 75%) by scenario x regime ===')
        print(stress_pivot(df, 'lr', lambda x: (x > 75).mean()).round(2).to_string())
    print('\n=== summary ===')
    print(stress_summary(df).round(3).to_string(index=False))

    if not args.no_save:
        stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
        stem = f"stress_{stamp}"
        try:
            p = df.to_parquet(io.SHARED / f'{stem}.parquet')
        except Exception:
            p = io.SHARED / f'{stem}.pkl'
            df.to_pickle(p)
        csv = io.SHARED / f'{stem}.csv'
        df.to_csv(csv, index=False)
        print(f"\nsaved: {p}\n       {csv}")
    print('done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
