"""Assumptions loader: base_template.json + scenario patches + seeds.

The template is the single source of truth for SIMULATION assumptions.
Scenarios are flat patches: keys present replace the base, everything else is
inherited; nested dicts merge key-by-key. Unknown keys are rejected with a
pointer to TEMPLATE.md.

Pricing is a black box to this module: the `pricing` key is passed through
untouched (opaque per-regime override blobs) — see voltvision/pricing.py.
"""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / 'base_template.json'
SEEDS_PATH = ROOT / 'seeds.json'

# Every key a template (or scenario patch) may contain. Anything else errors.
# Keep in sync with TEMPLATE.md.
TEMPLATE_KEYS = [
    # run controls
    'n', 'cohort_year', 'n_years', 'seed', 'regimes', 'vehicle_mix',
    'pricing', 'reporting',
    # book composition
    'coverage_pct', 'region_pct', 'generation_pct', 'age_bands', 'gender_pct',
    'car_age_median', 'car_age_sigma', 'sa_stats', 'engine_bands',
    'engine_weights', 'entrant_frac',
    # ncd
    'ncd_table', 'ncd_entry',
    # frequency
    'claim_frequency_base', 'frequency', 'risk_flags',
    # loadings / aging
    'loading', 'aging',
    # severity
    'severity', 'peril_dist', 'ev_severity_factor', 'severity_multiplier',
    # telematics & retention
    'telematics', 'behavior_risk', 'retention',
]

# Keys the runner consumes directly; never merged into the simulation cfg.
SCENARIO_RESERVED = ('name', 'vehicle')


def deep_merge(base, patch):
    """Recursive merge: dicts merge key-by-key, everything else replaces.

    Returns a new dict; inputs are never mutated (patches stay reusable).
    """
    out = {k: (copy.deepcopy(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _check_keys(d, where):
    unknown = [k for k in d if k not in TEMPLATE_KEYS]
    if unknown:
        raise KeyError(f"unknown key(s) in {where}: {unknown} — see TEMPLATE.md for the key list")


def _normalize(cfg):
    # JSON keys are strings; the NCD table is looked up by integer year.
    cfg['ncd_table'] = {int(k): v for k, v in cfg['ncd_table'].items()}
    return cfg


def load_template(path=None):
    """Read base_template.json (validated, normalized). Returns the base cfg."""
    p = Path(path) if path else TEMPLATE_PATH
    cfg = json.loads(p.read_text(encoding='utf-8'))
    _check_keys(cfg, p.name)
    cfg = _normalize(cfg)
    validate(cfg)
    return cfg


def load_seeds(path=None):
    """Read seeds.json. Returns a list of ints, or None when the file is absent.

    Accepted shapes: [0, 1, 2] or {"seeds": [0, 1, 2]}.
    """
    p = Path(path) if path else SEEDS_PATH
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding='utf-8'))
    seeds = data['seeds'] if isinstance(data, dict) else data
    if not isinstance(seeds, list) or not seeds:
        raise ValueError(f'{p.name}: expected a non-empty list of seeds')
    return [int(s) for s in seeds]


def build_cfg(template, scenario):
    """Merge one scenario patch onto the template → run cfg.

    Reserved runner keys (name, vehicle) are ignored here; `pricing` and `seed`
    stay in the cfg — `seed` because it is also a template key, `pricing` as an
    opaque blob the pricing connector reads.
    """
    patch = {k: v for k, v in scenario.items() if k not in SCENARIO_RESERVED}
    _check_keys(patch, f"scenario {scenario.get('name')!r}")
    return _normalize(deep_merge(template, patch))


def validate(cfg):
    """Fail loud on inconsistent assumptions. Returns cfg for chaining."""
    # Bands: one weight per band.
    if len(cfg['engine_bands']) != len(cfg['engine_weights']):
        raise ValueError('engine_bands and engine_weights length mismatch')
    # Severity: perils == spec keys == union of peril_dist keys.
    perils = cfg['severity']['perils']
    specs = set(cfg['severity']['specs'])
    if set(perils) != specs:
        raise ValueError(f'severity.perils {sorted(perils)} != specs {sorted(specs)}')
    used = {p for dist in cfg['peril_dist'].values() for p in dist}
    if used - specs:
        raise ValueError(f'peril_dist references unknown perils: {sorted(used - specs)}')
    # Every coverage in peril_dist must exist in coverage_pct (and vice versa).
    if set(cfg['peril_dist']) != set(cfg['coverage_pct']):
        raise ValueError('peril_dist and coverage_pct cover different coverages')
    # Risk flags must know every region.
    for flag, by_region in cfg['risk_flags'].items():
        missing = set(cfg['region_pct']) - set(by_region)
        if missing:
            raise ValueError(f'risk_flags.{flag} missing regions: {sorted(missing)}')
    # Fuel stats must exist for every fuel mentioned anywhere.
    fuels = set(cfg['vehicle_mix']) | set(cfg['sa_stats'])
    if set(cfg['sa_stats']) != fuels:
        raise ValueError(f'sa_stats must cover fuels {sorted(fuels)}')
    # Regime names are identifier-safe (used in PREM_ columns).
    from .schema import check_regime_name
    for name in cfg['regimes']:
        check_regime_name(name)
    return cfg


def describe_patch(template, scenario):
    """Plain-English diff of a scenario against the template (runner log).

    Returns lines like: 'coverage_pct.TPO: 0.15 -> 0.35'. Reserved keys are
    listed as-is (vehicle/seed/pricing are shown by the runner separately).
    """
    lines = []

    def walk(prefix, base, patch):
        for k, v in patch.items():
            path = f'{prefix}{k}'
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                walk(path + '.', base[k], v)
            else:
                lines.append(f'{path}: {base.get(k)!r} -> {v!r}')

    walk('', template, {k: v for k, v in scenario.items() if k not in SCENARIO_RESERVED})
    return lines
