import json

nb = json.load(open('main.ipynb', encoding='utf-8'))


def rep(cid, old, new, expect=1):
    for c in nb['cells']:
        if c['id'] == cid:
            s = ''.join(c['source'])
            n = s.count(old)
            assert n == expect, f"{cid}: found {n} of {old[:60]!r}, expected {expect}"
            c['source'] = s.replace(old, new).splitlines(keepends=True)
            c['outputs'] = []
            c['execution_count'] = None
            print(f'ok {cid}: {n}x {old[:50]!r}')
            return
    raise KeyError(cid)


# 1. Config: rename category keys to Young Adults / Adults / Mature Adults / Seniors
rep('050b235c',
    "'Gen-Z': 0.40, 'Millennial': 0.40, 'Boomers': 0.15, 'Senior': 0.05})",
    "'Young Adults': 0.40, 'Adults': 0.40, 'Mature Adults': 0.15, 'Seniors': 0.05})")

rep('050b235c',
    "    age_bands: dict = field(default_factory=lambda: {\n"
    "        'Gen-Z': (18, 28), 'Millennial': (28, 46),\n"
    "        'Boomers': (46, 66), 'Senior': (66, 76)})",
    "    age_bands: dict = field(default_factory=lambda: {\n"
    "        'Young Adults': (18, 28), 'Adults': (28, 46),\n"
    "        'Mature Adults': (46, 66), 'Seniors': (66, 76)})")

rep('050b235c',
    "        'Gen-Z': {'Single': 0.85, 'Married': 0.15},\n"
    "        'Millennial': {'Single': 0.50, 'Married': 0.50},\n"
    "        'Boomers': {'Single': 0.20, 'Married': 0.80},\n"
    "        'Senior': {'Single': 0.20, 'Married': 0.80}})",
    "        'Young Adults': {'Single': 0.85, 'Married': 0.15},\n"
    "        'Adults': {'Single': 0.50, 'Married': 0.50},\n"
    "        'Mature Adults': {'Single': 0.20, 'Married': 0.80},\n"
    "        'Seniors': {'Single': 0.20, 'Married': 0.80}})")

rep('050b235c',
    "        'Gen-Z': 2.0, 'Millennial': 3.5, 'Boomers': 5.0, 'Senior': 5.5})",
    "        'Young Adults': 2.0, 'Adults': 3.5, 'Mature Adults': 5.0, 'Seniors': 5.5})")

# 2. age_band helper (single source of truth), module level before generate_dataset
rep('050b235c',
    "def _p(weights):",
    "def age_band(age):\n"
    "    \"\"\"Map an exact driver age to its rating band (band upgrades with age).\"\"\"\n"
    "    if age <= 27:\n"
    "        return 'Young Adults'\n"
    "    if age <= 45:\n"
    "        return 'Adults'\n"
    "    if age <= 65:\n"
    "        return 'Mature Adults'\n"
    "    return 'Seniors'\n\n\n"
    "def _p(weights):")

# 3. Loadings dict: new keys, same values
rep('2e942bfaa252',
    'DRIVER_AGE_LOADING = {\n'
    '    "Gen-Z": 1.20,\n'
    '    "Millennial": 1.05,\n'
    '    "Boomers": 1.00,\n'
    '    "Senior": 1.05,\n'
    '}',
    'DRIVER_AGE_LOADING = {\n'
    '    "Young Adults": 1.20,\n'
    '    "Adults": 1.05,\n'
    '    "Mature Adults": 1.00,\n'
    '    "Seniors": 1.05,\n'
    '}')

# 4. Claim frequency model: new labels
rep('claim-model-lambda',
    "    if cat == 'Gen-Z':",
    "    if cat == 'Young Adults':")
rep('claim-model-lambda',
    "    elif cat == 'Senior':",
    "    elif cat == 'Seniors':")
rep('claim-model-lambda',
    "    if cat == 'Gen-Z' and row['DRIVER_GENDER'] == 'Male':",
    "    if cat == 'Young Adults' and row['DRIVER_GENDER'] == 'Male':")

# 5. Aging loop: re-enable band upgrade at each threshold crossing
rep('cohort-simulation',
    "            # DRIVER_AGE_CAT frozen at inception (age_to_cat removed)",
    "            # Band upgrades with age: crossing 27/45/65 moves to the next rating band\n"
    "            df_active.loc[aging_mask, 'DRIVER_AGE_CAT'] = df_active.loc[\n"
    "                aging_mask, 'DRIVER_AGE'\n"
    "            ].apply(age_band)")

# 6. Validation-core test 9c: new label
rep('validation-core',
    "genz_car = results.loc[results['DRIVER_AGE_CAT'] == 'Gen-Z', 'CAR_AGE'].mean()\n"
    "other_car = results.loc[results['DRIVER_AGE_CAT'] != 'Gen-Z', 'CAR_AGE'].mean()\n"
    "check('9c. Gen-Z drive newer cars than other cohorts', genz_car < other_car,\n"
    "      f\"(Gen-Z {genz_car:.1f} vs others {other_car:.1f})\")",
    "genz_car = results.loc[results['DRIVER_AGE_CAT'] == 'Young Adults', 'CAR_AGE'].mean()\n"
    "other_car = results.loc[results['DRIVER_AGE_CAT'] != 'Young Adults', 'CAR_AGE'].mean()\n"
    "check('9c. Young Adults drive newer cars than other bands', genz_car < other_car,\n"
    "      f\"(Young Adults {genz_car:.1f} vs others {other_car:.1f})\")")

# 7. Overthinker display strings (test itself is age-based, <=27)
rep('d5f0a0cb6f51', '# 7. Gen Z vs Non-Gen Z', '# 7. Young Adults vs older drivers')
rep('d5f0a0cb6f51',
    "print(f\"   Gen Z share: {gen_z_pct:.1f}%\")",
    "print(f\"   Young Adults share: {gen_z_pct:.1f}%\")")
rep('d5f0a0cb6f51',
    "print(f\"   Claim rate: Gen Z={gz_claim*100:.1f}% vs Non={nz_claim*100:.1f}%\")",
    "print(f\"   Claim rate: Young Adults={gz_claim*100:.1f}% vs Older={nz_claim*100:.1f}%\")")
rep('d5f0a0cb6f51',
    "print(f\"   Avg premium: Gen Z=RM{gz_prem:,.0f} vs Non=RM{nz_prem:,.0f}\")",
    "print(f\"   Avg premium: Young Adults=RM{gz_prem:,.0f} vs Older=RM{nz_prem:,.0f}\")")
rep('d5f0a0cb6f51',
    "enhanced_results.append({'Test': 'Gen Z Share'",
    "enhanced_results.append({'Test': 'Young Adults Share'")
rep('d5f0a0cb6f51',
    "enhanced_results.append({'Test': 'Gen Z Higher Claim Rate'",
    "enhanced_results.append({'Test': 'Young Adults Higher Claim Rate'")

json.dump(nb, open('main.ipynb', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('Saved')