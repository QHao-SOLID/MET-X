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


patch('def compute_retention_probability(row, premium_change_pct):', [
    (
        "def compute_retention_probability(row, premium_change_pct):\n"
        "    \"\"\"Compute probability of renewal.\n"
        "\n"
        "    Key drivers (priority):\n"
        "    1. Premium increase (highest sensitivity)\n"
        "    2. Claim occurrence\n"
        "    3. NCD level (incentive to stay)\n"
        "    \"\"\"\n"
        "    p = 0.80  # Base renewal rate\n"
        "\n"
        "    # Premium increase sensitivity (highest priority)\n"
        "    if premium_change_pct > 0.15:\n"
        "        p -= 0.15\n"
        "    elif premium_change_pct > 0.05:\n"
        "        p -= 0.10\n"
        "    elif premium_change_pct < -0.05:\n"
        "        p += 0.05  # Discounts improve retention\n"
        "\n"
        "    # Claim occurrence effect\n"
        "    p -= 0.25 if row.get('CLAIM_OCCURRED', False) else 0\n"
        "\n"
        "    # NCD incentive to stay\n"
        "    if row['NCD_YEARS'] >= 3:\n"
        "        p += 0.15\n"
        "    elif row['NCD_YEARS'] >= 2:\n"
        "        p += 0.08\n"
        "\n"
        "    return np.clip(p, 0.1, 0.95)\n",
        "def compute_retention_probability(row):\n"
        "    \"\"\"Premium-independent retention (driver A: experience + telematics only).\"\"\"\n"
        "    p = 0.82\n"
        "    if row.get('CLAIM_OCCURRED', False):\n"
        "        p -= 0.25\n"
        "    else:\n"
        "        p += 0.05\n"
        "    if row['NCD_YEARS'] >= 3:\n"
        "        p += 0.15\n"
        "    elif row['NCD_YEARS'] >= 2:\n"
        "        p += 0.08\n"
        "    if row['TELEMATICS_SCORE'] >= 80:\n"
        "        p += 0.10 * (row['TELEMATICS_SCORE'] - 80) / 20.0\n"
        "    elif row['TELEMATICS_SCORE'] >= 60:\n"
        "        p += 0.03\n"
        "    p -= 0.05 * (row['BEHAVIOR_RISK'] - 1.0)\n"
        "    return np.clip(p, 0.10, 0.95)\n"),
])

patch('def retention_prob_array(df, premium_change_pct):', [
    (
        "def retention_prob_array(df, premium_change_pct):\n"
        "    \"\"\"Vectorized binomial-logit retention proxy, same model as compute_retention_probability.\"\"\"\n"
        "    p = np.full(len(df), 0.80)\n"
        "    pc = np.full(len(df), premium_change_pct)\n"
        "    p -= np.where(pc > 0.15, 0.15, np.where(pc > 0.05, 0.10, 0.0))\n"
        "    p += np.where(pc < -0.05, 0.05, 0.0)\n"
        "    p -= 0.25 * df['CLAIM_OCCURRED'].values.astype(float)\n"
        "    ncd = df['NCD_YEARS'].values\n"
        "    p += np.select([ncd >= 3, ncd >= 2], [0.15, 0.08], default=0.0)\n"
        "    return np.clip(p, 0.1, 0.95)\n",
        "def retention_prob_array(df):\n"
        "    \"\"\"Vectorized premium-independent retention (driver A).\"\"\"\n"
        "    p = np.full(len(df), 0.82)\n"
        "    p -= np.where(df['CLAIM_OCCURRED'].values, 0.25, -0.05)\n"
        "    ncd = df['NCD_YEARS'].values\n"
        "    p += np.select([ncd >= 3, ncd >= 2], [0.15, 0.08], default=0.0)\n"
        "    ts = df['TELEMATICS_SCORE'].values\n"
        "    p += np.where(ts >= 80, 0.10 * (ts - 80) / 20.0,\n"
        "                  np.where(ts >= 60, 0.03, 0.0))\n"
        "    p -= 0.05 * (df['BEHAVIOR_RISK'].values - 1.0)\n"
        "    return np.clip(p, 0.10, 0.95)\n"),
])

json.dump(nb, open(NB, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved retention patch')
