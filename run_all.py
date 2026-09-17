"""Run the full VoltVision set without opening a notebook.

Does everything 01 + 02x + 03 do, headless:
  1. discover pricing methods from the 02x notebooks (notebooks own the math)
  2. simulate each scenario (premium-independent books -> shared/)
  3. price every book N ways (same claims, N premiums -> shared/)
  4. print the N-regime scorecard per scenario (+ optional Excel export)

Examples:
  python run_all.py                    # full run (n=10000, 5 years, core 3 regimes)
  python run_all.py --quick            # smoke run (n=1000, 2 years)
  python run_all.py --scenarios MIX    # one scenario only
  python run_all.py --regimes tariff,glm,telem,floor_demo
  python run_all.py --ev-share 0.30 --tpo-share 0.35   # richer EV mix + TPO-heavy book
  python run_all.py --no-excel         # skip the xlsx export

Exit code is nonzero when any validation fails (fail loud, not silent).
"""

import argparse
import copy
import os
import sys

# Run from anywhere: repo root (this file's folder) joins the import path.
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from voltvision import (  # noqa: E402  (imports after path fix, on purpose)
    CFG, SCEN, N_YEARS, REGIMES, COLS,
    gen, simulate, price_many, compare_all, lr_by,
    discover_methods, io,
)
from voltvision.config import export_config  # noqa: E402


def parse_args(argv=None):
    # CLI surface stays tiny: what to run, how big, what to price, what to save.
    ap = argparse.ArgumentParser(description="VoltVision full-set runner")
    ap.add_argument('--quick', action='store_true',
                    help='smoke run: n=1000, 2 years')
    ap.add_argument('--scenarios', default='ALL',
                    help='ICE | EV | MIX | ALL (default ALL)')
    ap.add_argument('--regimes', default=','.join(REGIMES),
                    help='comma-separated registered regimes (default core 3)')
    ap.add_argument('--seed', type=int, default=None,
                    help='override sim seed (default CFG seed)')
    ap.add_argument('--ev-share', type=float, default=None,
                    help='EV share for the MIX scenario, e.g. 0.30 (ICE gets 1-share); '
                         'ICE/EV-only scenarios unaffected')
    ap.add_argument('--tpo-share', type=float, default=None,
                    help='TPO share of the book mix, e.g. 0.35 (moved from Comprehensive; '
                         'TPFT share stays as configured)')
    ap.add_argument('--no-excel', action='store_true',
                    help='skip the xlsx export')
    ap.add_argument('--excel-scen', default='MIX',
                    help='scenario exported to xlsx (default MIX)')
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    # 1. Pricing methods come from the 02x notebooks — the runner owns no math.
    found = discover_methods(root=ROOT)
    print('methods:', {m: found[m] for m in sorted(found)})

    # 2. Scenarios + size. QUICK keeps the smoke run under a minute.
    scen_mix = copy.deepcopy(SCEN)
    if args.ev_share is not None:
        if not 0.0 <= args.ev_share <= 1.0:
            raise SystemExit('--ev-share must be within [0, 1]')
        scen_mix['MIX'] = {'ICE': round(1 - args.ev_share, 4), 'EV': args.ev_share}
    scens = [args.scenarios] if args.scenarios in SCEN else ['ICE', 'EV', 'MIX']
    regimes = [r.strip() for r in args.regimes.split(',') if r.strip()]
    cfg = copy.deepcopy(CFG)
    if args.quick:
        cfg['n'] = 1000
    if args.tpo_share is not None:
        tpft = cfg['coverage_pct'].get('TPFT', 0.20)
        if not 0.0 <= args.tpo_share <= 1 - tpft - 0.05:
            raise SystemExit(f'--tpo-share must leave >=5% Comprehensive (TPFT fixed at {tpft})')
        cfg['coverage_pct'] = {'Comprehensive': round(1 - args.tpo_share - tpft, 4),
                               'TPFT': tpft, 'TPO': args.tpo_share}
    nyears = 2 if args.quick else N_YEARS
    seed = cfg['seed'] if args.seed is None else args.seed
    print(f"scenarios={scens} regimes={regimes} n={cfg['n']} years={nyears} seed={seed}")
    print(f"mix: coverage={cfg['coverage_pct']} | MIX vehicle={scen_mix['MIX']}")

    # 3. Per scenario: simulate once (shared claims), price N ways.
    # Books are written to shared/ immediately and NOT accumulated in memory —
    # the export step reloads from disk, keeping peak RAM to one scenario.
    for s in scens:
        vp = scen_mix[s]
        d0 = gen(cfg, vp, seed)
        book = simulate(d0, cfg, vp, seed=seed, n_years=nyears, verbose=True)
        # Guard the connector contract: canonical columns, premium-free.
        assert list(book.columns) == COLS, f'{s}: column order drift'
        assert 'FINAL_PREMIUM_SST' not in book.columns, f'{s}: sim leaked premium'
        io.save_sim(s, book)
        books = price_many(book, cfg, regimes)
        for m, b in books.items():
            io.save_priced(s, m, b)
        print(f"--- {s} scorecard ---")
        print(compare_all(books).to_string(index=False))

    # 4. Optional export: 4-sheet Excel when RAM allows, CSV fallback otherwise.
    # Reload the chosen scenario from shared/ (already on disk) so the export
    # never holds every scenario's books at once.
    if not args.no_excel:
        export_scen = args.excel_scen if args.excel_scen in scens else scens[0]
        export_results(export_scen, regimes)

    # Run provenance: record the actual cfg/scen (overrides included).
    export_config(cfg=cfg, scen=scen_mix)
    print('done.')
    return 0


def export_results(export_scen, regimes):
    """Write one scenario's books: Excel (4 sheets), CSV fallback on MemoryError.

    Raw claims first (the one dataset every regime shares), then one slim
    POLID + FINAL_PREMIUM_SST sheet per regime. Big books (n=10000 x 5yr
    ~= 86k rows x 28 cols) can exhaust openpyxl's in-memory model; the CSV
    path writes the same content to shared/export_<SCEN>/ instead.
    Reads from shared/ — call after the books are saved.
    """
    import pandas as pd
    raw_book = io.load_sim(export_scen)
    books = {m: io.load_priced(export_scen, m) for m in regimes}
    file_name = os.path.join(ROOT, f"VoltVision_Motor_Simulation_{export_scen}.xlsx")
    try:
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            raw_book.to_excel(writer, sheet_name='Simulation Data', index=False)
            for m, b in books.items():
                sheet = ('Tariff Premiums' if m == 'tariff'
                         else 'GLM Premiums' if m == 'glm'
                         else 'Telematics Premiums' if m == 'telem'
                         else f'{m} Premiums'[:31])
                b[['POLID', 'FINAL_PREMIUM_SST']].to_excel(writer, sheet_name=sheet, index=False)
        print(f"exported {file_name}")
    except MemoryError:
        # Partial xlsx may be left behind — remove it, then write CSV instead.
        if os.path.exists(file_name):
            os.remove(file_name)
        csv_dir = os.path.join(io.SHARED, f'export_{export_scen}')
        os.makedirs(csv_dir, exist_ok=True)
        raw_book.to_csv(os.path.join(csv_dir, 'simulation_data.csv'), index=False)
        for m, b in books.items():
            b[['POLID', 'FINAL_PREMIUM_SST']].to_csv(
                os.path.join(csv_dir, f'{m}_premiums.csv'), index=False)
        print(f"Excel export ran out of memory — wrote CSVs to {csv_dir}")


if __name__ == '__main__':
    sys.exit(main())
