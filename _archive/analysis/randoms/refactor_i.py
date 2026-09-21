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


# Cell PR: keep the global cohort_results priced (telem = primary regime)
patch("cohort_results_telem = price_book(cohort_results, 'telem', COHORT_CONFIG)", [
    (
        "cohort_results_telem = price_book(cohort_results, 'telem', COHORT_CONFIG)\n"
        "\n"
        "avg_sev = (cohort_results['CLAIM_AMOUNT'].sum()",
        "cohort_results_telem = price_book(cohort_results, 'telem', COHORT_CONFIG)\n"
        "# keep the global cohort_results priced (telem = primary regime) for downstream cells\n"
        "cohort_results = cohort_results_telem\n"
        "\n"
        "avg_sev = (cohort_results['CLAIM_AMOUNT'].sum()"),
])

# Report: price the book explicitly before building the report (robust to any upstream state)
patch("    generate_actuarial_report(cohort_results, COHORT_CONFIG)", [
    (
        "    generate_actuarial_report(cohort_results, COHORT_CONFIG)",
        "    generate_actuarial_report(price_book(cohort_results, 'telem', COHORT_CONFIG), COHORT_CONFIG)"),
])

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved report/global pricing fix')
