"""Build the single-file offline guide: python3 -I build.py <raw_dir> <icon_dir> <guides_dir> <out.html>"""
import os, sys, glob, json, html, base64, subprocess, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dw2html import Conv

RAW, ICON_DIR, GUIDES, OUT = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__))

files = sorted(glob.glob(os.path.join(RAW, '*.txt')))
ids = {os.path.basename(f)[:-4].replace('__', ':'): f for f in files
       if not open(f, encoding='utf-8').read(15).lstrip().startswith('<!DOCTYPE')}  # wiki 'page not found' responses

# guides are hand-written HTML fragments: first line "<!-- title: X -->"
guides = {}
for f in sorted(g for d in GUIDES.split(',') for g in glob.glob(os.path.join(d, '*.html'))):
    src = open(f, encoding='utf-8').read()
    title = src.split('\n', 1)[0].removeprefix('<!-- title:').removesuffix('-->').strip()
    guides['guide:' + os.path.basename(f)[:-5]] = (title, src.split('\n', 1)[1])

known = set(ids) | set(guides)
pages, icons_needed, alts = {}, set(), {}
for pid, f in ids.items():
    text = open(f, encoding='utf-8').read()
    if not text.strip():
        continue
    c = Conv(pid, known)
    title, body = c.convert(text)
    title = title or pid.split(':')[-2 if pid.endswith(':start') and ':' in pid else -1].replace('_', ' ').title()
    pages[pid] = [html.unescape(title), body, c.tags, sorted(c.links & known)]
    icons_needed |= c.icons
    alts.update(c.alts)

import re
DBJ = json.load(open(os.path.join(os.path.dirname(RAW), 'db.json')))


def ref(m):
    kind, rid, label = m.group(1), m.group(2), m.group(3)
    src = DBJ['buildings'] if kind == 'b' else DBJ['items']
    e = src.get(rid)
    if not e:
        print('guide link to missing page:', rid)
        return html.escape(label or rid.split(':')[-1])
    icon = f'<img class="ic" data-i="{html.escape(e["icon"])}" alt="">' if e.get('icon') else ''
    return f'<a href="#/{rid}">{icon}{html.escape(label or e["name"])}</a>'


for gid in list(guides):
    title, body = guides[gid]
    guides[gid] = (title, re.sub(r'\[\[(b|i):([^\]|]+)(?:\|([^\]]*))?\]\]', ref, body))

for gid, (title, body) in guides.items():
    c = Conv(gid, known)
    for m in re.finditer(r'href="#/([^"]+)"', body):
        c.links.add(m.group(1))
    for m in re.finditer(r'data-i="([^"]+)"', body):
        icons_needed.add(m.group(1))
    pages[gid] = [title, body, ['Guide'], sorted(c.links & known)]

if 'professions:start' in pages:
    pages['professions:start'][1] = ('<div class="tip">See <a href="#/guide:professions">Professions: who works where</a> for every building each profession works in.</div>'
                                     + pages['professions:start'][1])

# interactive tool pages: rendered by tools.js, listed here so search and nav find them
TOOL_PAGES = {
    'tool:lookup': ('Resource lookup', 'Every resource: which buildings make it, ranked high medium low tiers, category, what it unlocks. production producers tooltip'),
    'tool:tree': ('Progression tree', 'What unlocks what. Resource steps from start: logs stone iron. Plan a building and see the chain of resources to work toward. tech tree'),
    'tool:planner': ('Season planner', 'Pick a climate: growing season, months above freezing, which seeds and crops fit, year-round food without seeds. weather winter summer'),
}
for tid, (title, text) in TOOL_PAGES.items():
    pages[tid] = [title, f'<p>{text}</p>', ['Tool'], []]
tools = json.load(open(os.path.join(os.path.dirname(RAW), 'tools.json')))
for it in tools['items'].values():
    if it['i']:
        icons_needed.add(it['i'])
for b in tools['blds'].values():
    if b['i']:
        icons_needed.add(b['i'])

# icons: wiki sprite -> replacement table -> similar working sprite -> lettered badge
from icon_fix import resolve_icons
icons, icon_report = resolve_icons(icons_needed, ICON_DIR, alts)

# nav: guides, then top-level categories, then building groups
def t(pid):
    return pages[pid][0] if pid in pages else pid

START = ['guide:home', 'guide:new-game', 'guide:first-steps', 'guide:cheatsheet']
nav = [['Start here', [[g, guides[g][0]] for g in START if g in guides]],
       ['Guides', sorted(([g, guides[g][0]] for g in guides if g not in START), key=lambda x: x[1])],
       ['Tools', [[k, v[0]] for k, v in TOOL_PAGES.items()]]]
top = [p for p in pages if p.count(':') == 1 and p.endswith(':start') and not p.startswith('guide:')]
nav.append(['Wiki sections', [[p, t(p)] for p in sorted(top, key=t)]])
bld = [p for p in pages if p.startswith('buildings:') and p.count(':') == 2 and p.endswith(':start')]
nav.append(['Buildings', [[p, t(p).replace(' Buildings', '')] for p in sorted(bld, key=t)]])
items = [p for p in pages if p.startswith('wikipages:') and p.count(':') == 2 and p.endswith(':start')]
nav.append(['Items & resources', [[p, t(p)] for p in sorted(items, key=t)]])

uniq, imap = {}, {}
for k, v in icons.items():
    imap[k] = uniq.setdefault(v, len(uniq))
data = {'pages': pages, 'icons': {'u': list(uniq), 'm': imap}, 'nav': nav, 'tools': tools, 'date': datetime.date.today().isoformat()}
blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
tpl = tpl.replace('__TOOLS_JS__', open(os.path.join(HERE, 'tools.js'), encoding='utf-8').read())
open(OUT, 'w', encoding='utf-8').write(tpl.replace('__DATA__', blob))
print(icon_report)
print(f'{len(pages)} pages, {len(icons)} icons, {os.path.getsize(OUT) / 1e6:.1f} MB -> {OUT}')
