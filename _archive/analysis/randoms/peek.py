p = r'C:\Users\Admin\Documents\Visual Studio Code\Typst\IFoA_VoltVison\analysis\main.ipynb'
s = open(p, encoding='utf-8').read()
print('len', len(s))
# show context around error position
i = 1484
print(repr(s[i-200:i+200]))
