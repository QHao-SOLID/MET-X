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


patch("print('=== PRICING PROGRESSION (same book, same seed; only pricing differs) ===')\nprint(lr_df.to_string(index=False))", [
    (
        "print('=== PRICING PROGRESSION (same book, same seed; only pricing differs) ===')\n"
        "print(lr_df.to_string(index=False))",
        "print('=== PRICING PROGRESSION (same book, same seed; only pricing differs) ===')\n"
        "print(lr_df.to_string(index=False))\n"
        "print()\n"
        "print('=== compare_pricing() [engine API] ===')\n"
        "print(compare_pricing(cohort_results).to_string(index=False))"),
])

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved compare_pricing display')
