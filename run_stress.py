"""Run stress scenarios headless: JSON scenario groups x seeds x regimes.

Scenario files live in scenarios/*.json (default), each a JSON list of:
  {"name": "...", "cfg": {DGP overrides}, "card": {pricing overrides},
   "vehicle": "ICE" | "EV" | "MIX" (optional, default --vehicle)}

Every (scenario, seed) is simulated once and priced per regime; tidy results
are saved per group to shared/stress_results/<group>_<stamp>.csv and .json,
with mean-LR and P(LR>75%) pivots printed.

Useful levers (docs in AGENT.md): cfg = claim_frequency_base,
severity_multiplier, ev_severity_factor, coverage_pct, entrant_frac;
card = expense_loading, tpo_loading, tpo_sa_pct, risk_step, train_book_seed.

Examples:
  python run_stress.py --quick --seeds 0            # smoke: fast, 1 seed
  python run_stress.py                              # all groups, seeds 0,1,2
  python run_stress.py --grid scenarios/02_severity.json --seeds 0,1
  python run_stress.py --scenarios base,freq_x1.22 --no-save
"""

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from voltvision import REGIMES, io  # noqa: E402
from voltvision.stress import run_stress, stress_summary, stress_pivot  # noqa: E402


def load_groups(grid):
    # grid = a directory of *.json scenario files (default: scenarios/) or a
    # single .json file. Returns [(group_name, [scenario dicts]), ...] in
    # file-name order; the file stem becomes the result group name.
    p = Path(grid)
    if p.is_dir():
        files = sorted(p.glob('*.json'))
        if not files:
            raise SystemExit(f'no *.json scenario files found in {p}')
    else:
        files = [p]
    groups = []
    for f in files:
        scens = json.loads(f.read_text(encoding='utf-8'))
        if not isinstance(scens, list) or not scens:
            raise SystemExit(f'{f}: expected a non-empty JSON list of scenarios')
        groups.append((f.stem, scens))
    return groups


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description='VoltVision stress runner')
    ap.add_argument('--grid', default='scenarios', help='scenario directory or .json file')
    ap.add_argument('--seeds', default='0,1,2', help='comma-separated sim seeds')
    ap.add_argument('--scenarios', default='', help='subset of scenario names (default: all)')
    ap.add_argument('--regimes', default=','.join(REGIMES), help='regimes to price')
    ap.add_argument('--vehicle', default='MIX', help='default vehicle book (ICE|EV|MIX)')
    ap.add_argument('--quick', action='store_true', help='n=1000, 2 years per run')
    ap.add_argument('--no-save', action='store_true', help='skip writing results')
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    groups = load_groups(args.grid)
    if args.scenarios:
        keep = {s.strip() for s in args.scenarios.split(',') if s.strip()}
        groups = [(g, [s for s in scens if s['name'] in keep]) for g, scens in groups]
        groups = [(g, scens) for g, scens in groups if scens]
    seeds = tuple(int(s) for s in args.seeds.split(',') if s.strip())
    regimes = [r.strip() for r in args.regimes.split(',') if r.strip()]
    print(f"grid={args.grid} groups={[g for g, _ in groups]} seeds={seeds} "
          f"regimes={regimes} vehicle={args.vehicle} quick={args.quick}")

    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = io.SHARED / 'stress_results'
    frames = []
    for name, scens in groups:
        print(f"\n########## {name}: {[s['name'] for s in scens]}")
        df = run_stress(scens, seeds=seeds, regimes=regimes,
                        vehicle=args.vehicle, quick=args.quick)
        frames.append(df)
        print('\n=== mean LR by scenario x regime ===')
        print(stress_pivot(df, 'lr', 'mean').round(2).to_string())
        if len(seeds) > 1:
            print('\n=== P(LR > 75%) by scenario x regime ===')
            print(stress_pivot(df, 'lr', lambda x: (x > 75).mean()).round(2).to_string())
        print('\n=== summary ===')
        print(stress_summary(df).round(3).to_string(index=False))
        if not args.no_save:
            out_dir.mkdir(parents=True, exist_ok=True)
            csv, js = out_dir / f'{name}_{stamp}.csv', out_dir / f'{name}_{stamp}.json'
            df.to_csv(csv, index=False)
            df.to_json(js, orient='records', indent=1)
            print(f"saved: {csv}\n       {js}")

    if not args.no_save and len(frames) > 1:
        import pandas as pd
        allf = pd.concat(frames, ignore_index=True)
        csv, js = out_dir / f'all_{stamp}.csv', out_dir / f'all_{stamp}.json'
        allf.to_csv(csv, index=False)
        allf.to_json(js, orient='records', indent=1)
        print(f"\ncombined: {csv}\n          {js}")
    print('done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
