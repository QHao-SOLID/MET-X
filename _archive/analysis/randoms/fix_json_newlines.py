p = r'C:\Users\Admin\Documents\Visual Studio Code\Typst\IFoA_VoltVison\analysis\main.ipynb'
s = open(p, encoding='utf-8').read()

bad = (
    '"from scipy.stats import kstest, gamma as gamma_dist, normaltest, norm'
    '\n\n# ensure output directories exist for figures / exports / report'
    '\nos.makedirs(\'images\', exist_ok=True)'
    '\nos.makedirs(\'data\', exist_ok=True)'
    '\nos.makedirs(\'report/figures\', exist_ok=True)'
    '\\n"'
)
good = (
    '"from scipy.stats import kstest, gamma as gamma_dist, normaltest, norm'
    '\\n\\n# ensure output directories exist for figures / exports / report'
    '\\nos.makedirs(\'images\', exist_ok=True)'
    '\\nos.makedirs(\'data\', exist_ok=True)'
    '\\nos.makedirs(\'report/figures\', exist_ok=True)'
    '\\n"'
)

if bad in s:
    s = s.replace(bad, good, 1)
    open(p, 'w', encoding='utf-8').write(s)
    print('REPAIRED')
else:
    print('NO MATCH')
