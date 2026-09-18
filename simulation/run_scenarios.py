"""Run every scenario group: simulate → price → combine → save (one file each).

Examples:
  python run_scenarios.py                     # all scenarios x seeds.json, full size
  python run_scenarios.py --quick             # smoke: n=1000, 2 years
  python run_scenarios.py --scenarios mix_60_40,tpo_heavy
  python run_scenarios.py --seeds 0,4         # override seeds.json
  python run_scenarios.py --csv               # also write CSV beside each pkl
  python run_scenarios.py --grid scenarios/02_severity.json
  python run_scenarios.py --excel mix_60_40_s0   # xlsx from an existing result

Results land in shared/results/<scenario>_s<seed>.pkl (+ manifest.json).
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from voltvision import run_scenarios  # noqa: E402
from voltvision import io  # noqa: E402


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description='VoltVision scenario runner')
    ap.add_argument('--grid', default='scenarios',
                    help='scenario directory or single .json file (default scenarios/)')
    ap.add_argument('--scenarios', default='',
                    help='subset of scenario names (comma-separated; default: all)')
    ap.add_argument('--seeds', default='',
                    help='override seeds.json, e.g. 0,1,2')
    ap.add_argument('--quick', action='store_true', help='smoke: n=1000, 2 years')
    ap.add_argument('--csv', action='store_true', help='also write CSV per result')
    ap.add_argument('--excel', default='',
                    help='export one result stem to xlsx, e.g. mix_60_40_s0 (skips the loop)')
    return ap.parse_args(argv)


def export_excel(stem):
    """Write an xlsx (sim sheet + one premium sheet per regime) from a result."""
    import pandas as pd
    parts = stem.rsplit('_s', 1)
    scenario, seed = parts[0], int(parts[1])
    combined = io.load_result(scenario, seed)
    path = os.path.join(ROOT, f'VoltVision_Motor_Simulation_{stem}.xlsx')
    regimes = io.premium_columns(combined)
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        io.sim_book(combined).to_excel(writer, sheet_name='Simulation Data', index=False)
        for regime in regimes:
            combined[['POLID', io.premium_column(regime)]].to_excel(
                writer, sheet_name=f'{regime} Premiums'[:31], index=False)
    print(f'exported {path}')


def main(argv=None):
    args = parse_args(argv)
    if args.excel:
        export_excel(args.excel)
        return 0

    names = {s.strip() for s in args.scenarios.split(',') if s.strip()} or None
    seeds = [int(s) for s in args.seeds.split(',') if s.strip()] if args.seeds else None
    results = run_scenarios(grid=args.grid, scenario_names=names, seeds=seeds,
                            quick=args.quick, csv=args.csv)
    if results.empty:
        print('no scenarios selected.')
        return 1
    print('\n=== LR by scenario x seed (rows) x regime (cols) ===')
    print(results.pivot_table(index=['scenario', 'seed'], columns='regime',
                              values='lr', aggfunc='mean').round(2).to_string())
    print('\ndone.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
