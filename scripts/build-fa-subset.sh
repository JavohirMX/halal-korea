#!/usr/bin/env bash
# Rebuild the Font Awesome subset (static/css/fontawesome-subset.css +
# static/fonts/fa-*-subset.woff2) from the icons actually used in
# templates, Python files and static JS. Requires: pip install fonttools brotli
# Usage: scripts/build-fa-subset.sh [version]
set -euo pipefail
VERSION="${1:-6.5.1}"
WORK="$(mktemp -d)"

grep -rhoE 'fa-[a-z0-9-]+' --include='*.html' --include='*.py' . static/js/ \
  | sort -u > "$WORK/used.txt"

curl -sSL -o "$WORK/fa.css" "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/$VERSION/css/all.min.css"
for f in fa-solid-900 fa-regular-400 fa-brands-400; do
  curl -sSL -o "$WORK/$f.woff2" "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/$VERSION/webfonts/$f.woff2"
done

python3 - "$WORK" <<'PY'
import re, subprocess, sys, os
work = sys.argv[1]
css = open(f"{work}/fa.css").read()
mapping = {}
for sel_group, code in re.findall(r'((?:\.fa-[a-z0-9-]+:before,?)+)\{content:"\\([0-9a-f]+)"\}', css):
    for name in re.findall(r'\.(fa-[a-z0-9-]+):before', sel_group):
        mapping[name] = code
skip = {'fa-solid','fa-regular','fa-brands','fa-light','fa-duotone'}
used = {l.strip() for l in open(f"{work}/used.txt") if l.strip()} - skip
have = {i: mapping[i] for i in used if i in mapping}
missing = sorted(i for i in used if i not in mapping)
if missing:
    print("warning: not in FA free:", missing)
unicodes = ','.join('U+' + u.upper().rjust(4, '0') for u in sorted(set(have.values())))
os.makedirs('static/fonts', exist_ok=True)
for fam in ['solid', 'regular', 'brands']:
    weight = {'solid': '900', 'regular': '400', 'brands': '400'}[fam]
    subprocess.run(['pyftsubset', f"{work}/fa-{fam}-{weight}.woff2",
                    f'--unicodes={unicodes}', '--flavor=woff2',
                    f'--output-file=static/fonts/fa-{fam}-subset.woff2',
                    '--layout-features=*'], check=True)
head = open('static/css/fontawesome-subset.css').read().split('/* icons */')[0]
rules = ''.join(f'.{n}:before {{ content: "\\{c}"; }}\n' for n, c in sorted(have.items()))
open('static/css/fontawesome-subset.css', 'w').write(head + '/* icons */\n' + rules)
print('subset rebuilt:', len(have), 'icons')
PY
echo "Done. Commit static/css/fontawesome-subset.css and static/fonts/."
