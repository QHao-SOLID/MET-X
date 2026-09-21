import nbformat
nb = nbformat.read('main.ipynb', as_version=4)
def src(c):
    return c.source if isinstance(c.source, str) else ''.join(c.source)

for target in [30, 36]:
    s = src(nb.cells[target])
    lines = s.split('\n')
    # find the nested def start
    start = None
    for j, ln in enumerate(lines):
        if ln.strip().startswith('def _encode_features'):
            start = j
            break
    if start is None:
        print(f'cell {target}: no nested _encode_features found')
        continue
    # find end: next line at same indentation that is NOT part of the function (blank or def at 4-space indent)
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start
    for j in range(start + 1, len(lines)):
        if lines[j].strip() == '':
            # allow blank lines inside? they're rare; stop at first blank at <= indent
            if len(lines[j]) - len(lines[j].lstrip()) <= indent:
                break
        if lines[j].strip() != '' and (len(lines[j]) - len(lines[j].lstrip())) <= indent:
            break
        end = j
    print(f'=== cell {target}: nested _encode_features lines {start}-{end} ===')
    for k in range(start, end + 1):
        print(repr(lines[k]))
    print()
