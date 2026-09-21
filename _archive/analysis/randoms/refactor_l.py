import json

NB = 'main.ipynb'
nb = json.load(open(NB, encoding='utf-8'))


def fc(anchor):
    for c in nb['cells']:
        if anchor in ''.join(c.get('source', [])):
            return c
    raise SystemExit('not found: ' + anchor)


def patch(anchor, repls):
    c = fc(anchor)
    s = ''.join(c.get('source', []))
    for o, n in repls:
        k = s.count(o)
        if k != 1:
            raise SystemExit('match %d for %r' % (k, o[:70]))
        s = s.replace(o, n)
    c['source'] = s.splitlines(keepends=True)
    print('patched', anchor)


old = (
    "_spread_glm = tier_glm.max() - tier_glm.min()\n"
    "_spread_telem = tier_telem.max() - tier_telem.min()\n"
    "_check('13f. tier LR spread: GLM >> telem (blind pricing leaves risk gradient)',\n"
    "       _spread_glm > _spread_telem + 3,\n"
    "       f\"(GLM {_spread_glm:.1f}pp vs telem {_spread_telem:.1f}pp)\")\n"
    "print(f'Pricing-progression checks: {sum(_passed)}/{len(_passed)} passed')"
)

new = (
    "# 13f (reframed): GLM is blind to telematics, so its premium does NOT track\n"
    "# telematics_score; telem's premium is risk-based (negative score-premium corr).\n"
    "def _score_corr(res):\n"
    "    return spearmanr(res['FINAL_PREMIUM_SST'], res['telematics_score']).correlation\n"
    "_c_glm = _score_corr(cohort_results_glm)\n"
    "_c_telem = _score_corr(cohort_results_telem)\n"
    "_check('13f. telem premium tracks telematics_score (risk-based); GLM ~blind',\n"
    "       _c_telem < _c_glm - 0.1,\n"
    "       f\"(glm {_c_glm:+.3f} | telem {_c_telem:+.3f})\")\n"
    "print(f'Pricing-progression checks: {sum(_passed)}/{len(_passed)} passed')"
)

patch("tier_glm = _tier_lr(cohort_results_glm)", [(old, new)])

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved 13f reframe')
