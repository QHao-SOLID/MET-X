"""Premium-independent simulation engine (bread and butter).

What lives here:
  gen()          builds one book of policies (attributes + BASIC_PREMIUM, no claims).
                 Used for the starting book (prefix INIT) and yearly entrants (ENT).
  claim_lambda() Poisson rate per policy: log-linear rating model on driver,
                 vehicle, risk flags, behavior, car age, NCD, coverage.
  loading()      tariff loading per policy: driver band x vehicle-age factor.
  simulate()     evolves a book year by year: age -> frequency -> peril ->
                 severity -> retention -> NCD update -> record -> entrants.
                 Output has claims + labels, NEVER premium (pricing.py adds it).

Who calls it: 01_simulation.ipynb, 03_main.ipynb, run_all.py.
Output columns follow config.COLS (POLID first).

TODO (improvement backlog, behavior intentionally unchanged):
  - FLOOD/THEFT thresholds below are complemented vs full risk_pct
    (Peninsular flood-True 40% here vs 60% full; East flood ~100% vs 0%).
    Align to full when DGP change approved.
  - Optional EV-ramp entrant mix / entrant growth (full _entrant_vehicle_pct).
"""

import numpy as np
import pandas as pd

from .config import BANDS, BASIC_COMP, BASIC_TPO, COLS, PER_EXTRA, PERIL_DIST


def _p(w):
    # Turn any weights into probabilities that sum to exactly 1,
    # so np.random.choice never rejects them over float dust.
    a = np.array(list(w), float)
    return a / a.sum()


def gen(cfg, vehicle_pct, seed, year=None, prefix='INIT', n=None):
    # Build one book of n policies from the CFG assumptions.
    # Pure attributes + BASIC_PREMIUM: no claims, no SIM_YEAR yet.
    # Same seed + same inputs = same book (reproducible).
    n = int(n or cfg['n'])
    rng = np.random.default_rng(seed)
    yr = year or cfg['cohort_year']
    df = pd.DataFrame(index=range(n))

    # Product mix: coverage, fuel type, region — independent draws.
    df['COVERAGE_TYPE'] = rng.choice(list(cfg['coverage_pct']), p=_p(cfg['coverage_pct'].values()), size=n)
    df['VEHICLE_TYPE'] = rng.choice(list(vehicle_pct), p=_p(vehicle_pct.values()), size=n)
    df['REGION'] = rng.choice(list(cfg['region_pct']), p=_p(cfg['region_pct'].values()), size=n)

    # Sum assured: log-normal per fuel type (EVs cost more to replace),
    # rounded to RM1,000 because tariff tables step per thousand.
    sa = np.zeros(n)
    for vt, (lam, sp) in cfg['sa_stats'].items():
        m = df['VEHICLE_TYPE'].values == vt
        sa[m] = rng.lognormal(np.log(lam), sp, int(m.sum()))
    df['SUM_ASSURED'] = np.round(sa / 1000) * 1000

    # Engine band: fixed hand-set mix, small cars dominant.
    df['ENGINE_CAPACITY'] = rng.choice(BANDS, p=_p(cfg['engine_weights']), size=n)

    # Driver: draw the generation band first, then an exact age inside it.
    df['DRIVER_AGE_CAT'] = rng.choice(list(cfg['generation_pct']), p=_p(cfg['generation_pct'].values()), size=n)
    lo = np.array([cfg['age_bands'][c][0] for c in df['DRIVER_AGE_CAT']])
    hi = np.array([cfg['age_bands'][c][1] for c in df['DRIVER_AGE_CAT']])
    df['DRIVER_AGE'] = rng.integers(lo, hi)
    df['DRIVER_GENDER'] = rng.choice(list(cfg['gender_pct']), p=_p(cfg['gender_pct'].values()), size=n)

    # Car age at inception: band median plus noise, clipped to 0-10 years.
    ca = np.zeros(n)
    for c, med in cfg['car_age_median'].items():
        m = df['DRIVER_AGE_CAT'].values == c
        ca[m] = np.clip(np.round(med + rng.normal(0, cfg['car_age_sigma'], int(m.sum()))), 0, 10)
    df['CAR_AGE'] = ca.astype(int)

    # Region risk flags. NOTE the thresholds read as P(False): random() above
    # the cut means True, so Peninsular flood-True is 40%, theft-True 60%.
    # (Full notebook uses the complement — flagged, kept until approved.)
    fl = np.zeros(n, bool)
    th = np.zeros(n, bool)
    for r in df['REGION'].unique():
        m = df['REGION'].values == r
        pen = 'Peninsular' in r
        fl[m] = rng.random(m.sum()) > (0.60 if pen else 0.0)
        th[m] = rng.random(m.sum()) > (0.40 if pen else 0.15)
    df['FLOOD_RISK'] = fl
    df['THEFT_RISK'] = th

    # NCD entry mix: most drivers start at 0 years, few at max discount.
    df['NCD_YEARS'] = rng.choice([0, 1, 2, 3, 4, 5], p=_p([0.30, 0.22, 0.16, 0.13, 0.10, 0.09]), size=n)
    # Years beyond 5 keep the top tier (min caps the lookup).
    df['NCD_LEVEL'] = df['NCD_YEARS'].map(lambda y: cfg['ncd_table'][min(int(y), 5)])
    df['COHORT_YEAR'] = yr

    # Telematics: harsh braking / speeding / night share -> one composite ->
    # score 20-100 (higher = safer). Min-max blend keeps each input 0-1 first.
    hb = np.clip(rng.gamma(2.0, 1.8, size=n), 0, 15)
    sp = np.clip(rng.gamma(2.0, 6.0, size=n), 0, 50)
    nd = np.clip(rng.beta(2, 5, size=n) * 40, 0, 50)
    comp = (0.45 * (hb - hb.min()) / (hb.max() - hb.min())
            + 0.40 * (sp - sp.min()) / (sp.max() - sp.min())
            + 0.15 * (nd - nd.min()) / (nd.max() - nd.min()))
    df['telematics_score'] = np.clip(100 - comp * 80, 20, 100)
    # Behavior risk: rank-map score to 0.90-1.30 so the WORST driver always
    # gets 1.30 and the shape stays uniform whatever the raw gammas do.
    u = np.argsort(np.argsort(df['telematics_score'].values)) / (max(n - 1, 1))
    df['BEHAVIOR_RISK'] = 1.30 - 0.40 * u

    # Deterministic policy IDs: prefix + cohort year + sequence.
    df['POLID'] = [f"{prefix}{yr}-{i + 1:06d}" for i in range(n)]

    # BASIC premium from the tariff tables (before loadings/discounts/SST):
    # Comp = first-RM1,000 rate + PER_EXTRA per extra thousand of sum assured;
    # TPFT = 75% of Comp; TPO = flat table rate (SA leg added at pricing time).
    bi = {b: i for i, b in enumerate(BANDS)}
    cb = np.array([BASIC_COMP[r][bi[e]] for r, e in zip(df['REGION'], df['ENGINE_CAPACITY'])])
    ex = np.array([PER_EXTRA[r] for r in df['REGION']])
    comp_basic = cb + ex * np.ceil(np.maximum(0, df['SUM_ASSURED'].values - 1000) / 1000)
    tb = np.array([BASIC_TPO[r][bi[e]] for r, e in zip(df['REGION'], df['ENGINE_CAPACITY'])])
    cov = df['COVERAGE_TYPE'].values
    df['BASIC_PREMIUM'] = np.where(
        cov == 'Comprehensive', comp_basic,
        np.where(cov == 'TPFT', np.round(0.75 * comp_basic, 2), tb)).round(2)
    return df


def claim_lambda(df, cfg):
    # Poisson rate per policy: start from the base log-rate, add rating
    # factors in log space (so they multiply), exponentiate, then scale by
    # coverage (TPO has no own-damage, TPFT fire/theft only).
    c = df['DRIVER_AGE_CAT'].values
    ll = np.full(len(df), cfg['claim_frequency_base']) + 0.40 * (c == 'Young Adults') + 0.26 * (c == 'Seniors')
    ll += 0.05 * ((c == 'Young Adults') & (df['DRIVER_GENDER'].values == 'Male')) + 0.05 * (df['VEHICLE_TYPE'].values == 'EV')
    ll += 0.20 * df['FLOOD_RISK'].values + 0.10 * df['THEFT_RISK'].values + np.log(df['BEHAVIOR_RISK'].values)
    ll += 0.03 * df['CAR_AGE'].values - 0.05 * df['NCD_YEARS'].values
    mult = np.where(df['COVERAGE_TYPE'].values == 'TPO', 0.45,
                    np.where(df['COVERAGE_TYPE'].values == 'TPFT', 0.60, 1.0))
    return np.exp(ll) * mult


def loading(df):
    # Tariff loading: risky driver bands pay more, older cars pay 3%/year.
    # Car age capped at 10 so the factor tops out at 1.30.
    dl = df['DRIVER_AGE_CAT'].map(
        {"Young Adults": 1.2, "Adults": 1.05, "Mature Adults": 1.0, "Seniors": 1.05}).fillna(1).values
    return dl * (1 + 0.03 * np.minimum(df['CAR_AGE'].values, 10))


# Peril draw order. Each coverage maps to a subset with its own mix
# (see PERIL_DIST); policies can hold several claims joined by '/'.
PN = ['AD', 'Windscreen', 'Theft', 'Fire', 'TPPD', 'TPBI']


def simulate(df0, cfg, vehicle_pct, seed, n_years=5, verbose=True):
    # Evolve the book. Same seed = same claims (local RNG, no globals).
    # Retention is premium-independent: experience + telematics only.
    rng = np.random.default_rng(seed)
    act = df0.copy()
    hist = []
    for k in range(n_years):
        yr = cfg['cohort_year'] + k
        act['SIM_YEAR'] = yr

        # Age in-force policies by one year; fresh entrants keep young ages.
        # Crossing 27/45/65 moves the driver rating band up.
        age = act['COHORT_YEAR'] < yr
        if age.any():
            act.loc[age, 'DRIVER_AGE'] += 1
            act.loc[age, 'CAR_AGE'] = np.minimum(act.loc[age, 'CAR_AGE'] + 1, 10)
            act.loc[age, 'DRIVER_AGE_CAT'] = np.select(
                [act.loc[age, 'DRIVER_AGE'] <= 27, act.loc[age, 'DRIVER_AGE'] <= 45,
                 act.loc[age, 'DRIVER_AGE'] <= 65],
                ['Young Adults', 'Adults', 'Mature Adults'], default='Seniors')

        # Frequency + priced-NCD snapshot BEFORE this year's claims
        # (NCD_LEVEL_PRICED lags one year behind the updated NCD_LEVEL).
        act['CLAIM_LAMBDA'] = claim_lambda(act, cfg)
        act['TOTAL_LOADING'] = loading(act)
        act['NCD_LEVEL_PRICED'] = act['NCD_LEVEL']

        # Claim counts: one Poisson draw per policy around its lambda.
        act['CLAIM_COUNT'] = rng.poisson(act['CLAIM_LAMBDA'].values)
        act['CLAIM_OCCURRED'] = act['CLAIM_COUNT'] > 0

        # Severity, vectorized: explode claimants into one row PER CLAIM,
        # draw each claim's peril from its coverage mix, draw Gamma amounts,
        # cap them, then add back up to policy level.
        amt = np.zeros(len(act))
        per = np.full(len(act), '', dtype=object)
        cnt = act['CLAIM_COUNT'].values
        m = cnt > 0
        if m.any():
            # Repeat each claimant's row index by its claim count.
            idx = np.repeat(np.flatnonzero(m), cnt[m])
            cov = act['COVERAGE_TYPE'].values[idx]
            sa = act['SUM_ASSURED'].values[idx]
            # Peril draw: uniform vs cumulative mix, argmax-style via sum.
            P = np.array([[PERIL_DIST[c].get(p, 0) for p in PN] for c in cov])
            pi = np.minimum((rng.random(len(idx))[:, None] > np.cumsum(P, axis=1)).sum(axis=1), 5)
            pl = np.array(PN)[pi]
            # EV repair loading applies to own-damage perils only (not TPBI/TPPD).
            evm = np.where(act['VEHICLE_TYPE'].values[idx] == 'EV', cfg['ev_severity_factor'], 1.0)
            # Global severity shock (stress lever): 1.0 = baseline, 1.2 = +20%
            # on EVERY peril; kept separate from the EV loading so scenarios
            # can move repair costs without touching the EV mix effect.
            sev_mult = cfg.get('severity_multiplier', 1.0)
            sh = np.zeros(len(idx))    # Gamma shape per claim
            sc = np.zeros(len(idx))    # Gamma scale per claim
            cap = np.full(len(idx), np.inf)  # payout cap per claim
            # Third-party + windscreen: fixed severity curves.
            tb = {'TPBI': (0.35, 70000.0, np.inf), 'TPPD': (0.55, 9000.0, 3e6),
                  'Windscreen': (2.0, 700.0, 15000.0)}
            for nm, (a, s, cp) in tb.items():
                q = pl == nm
                sh[q] = a
                sc[q] = s * sev_mult
                cap[q] = cp
            # Own-damage: scale tracks sum assured (fraction f, clipped to
            # a RM band so tiny/large cars stay sane), capped AT sum assured.
            for nm, lo, hi, f, a in (('Theft', 8000, 20000, 0.20, 1.10),
                                     ('Fire', 7000, 18000, 0.15, 0.90),
                                     ('AD', 4500, 12000, 0.10, 0.60)):
                q = pl == nm
                sh[q] = a
                sc[q] = np.clip(sa[q] * f, lo, hi) * evm[q] * sev_mult
                cap[q] = sa[q]
            am = np.minimum(rng.gamma(sh, sc), cap)
            # Scatter the per-claim amounts back onto their policies.
            np.add.at(amt, idx, am)
            # One peril string per policy: multiple claims joined by '/'.
            per[np.flatnonzero(m)] = pd.Series(pl).groupby(pd.Series(idx)).agg('/'.join).values
        act['CLAIM_AMOUNT'] = amt
        act['CLAIM_PERIL'] = per

        # Retention: base 82%, claimants -25pp, clean years +5pp, loyal NCD
        # +8/+15pp, safe telematics bonus, risky behavior penalty. Clipped.
        p = np.full(len(act), 0.82) - np.where(act['CLAIM_OCCURRED'].values, 0.25, -0.05)
        p += np.select([act['NCD_YEARS'].values >= 3, act['NCD_YEARS'].values >= 2],
                       [0.15, 0.08], default=0.0)
        ts = act['telematics_score'].values
        p += np.where(ts >= 80, 0.10 * (ts - 80) / 20, np.where(ts >= 60, 0.03, 0.0))
        p -= 0.05 * (act['BEHAVIOR_RISK'].values - 1.0)
        act['RENEWAL_PROB'] = np.clip(p, 0.10, 0.95)
        act['RENEWED'] = rng.random(len(act)) < act['RENEWAL_PROB'].values

        # NCD update AFTER the year: clean year earns a year, any claim resets.
        act.loc[~act['CLAIM_OCCURRED'], 'NCD_YEARS'] += 1
        act.loc[act['CLAIM_OCCURRED'], 'NCD_YEARS'] = 0
        act['NCD_LEVEL'] = act['NCD_YEARS'].map(lambda y: cfg['ncd_table'][min(int(y), 5)])

        # Record the FULL year state in canonical column order (incl. lapsers,
        # so retention stays measurable), then roll forward: survivors + entrants.
        hist.append(act[COLS].copy())
        if verbose:
            print(f"Year {yr}: {len(act)} pols, claims {act['CLAIM_COUNT'].sum()}, "
                  f"freq {act['CLAIM_OCCURRED'].mean():.1%}")
        if k < n_years - 1:
            ent = gen(cfg, vehicle_pct, seed + k + 1, year=yr + 1,
                      prefix='ENT', n=int(cfg['n'] * cfg['entrant_frac']))
            act = pd.concat([act[act['RENEWED']], ent], ignore_index=True)
    return pd.concat(hist, ignore_index=True)
