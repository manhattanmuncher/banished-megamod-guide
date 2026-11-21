"""Pull structured data out of raw wiki pages: python3 -I extract.py <raw_dir> <out.json>
Output: {buildings: {id: {...}}, items: {id: {...}}, seeds: [...], orchard_seeds: [...], climates: [...]}"""
import os, re, sys, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dw2html import Conv, norm_id

RAW, OUT = sys.argv[1:3]
SPLIT = Conv('x', set()).split_row
LINK = re.compile(r'\[\[([^|\]#]+)(?:#[^|\]]*)?(?:\|([^\]]*))?\]\]')
SPRITE = re.compile(r'sprites\.worldofbanished\.com/([^?|}\s]+)')


def clean(s):
    s = re.sub(r'\{\{[^}]*\}\}', '', s)
    s = LINK.sub(lambda m: m.group(2) or m.group(1).split(':')[-1], s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s.replace('**', '').replace('\\\\', ' ')).strip()


def links(s, cur):
    return [norm_id(m.group(1), cur) for m in LINK.finditer(s)]


def section(text, name):
    m = re.search(r'\n=====\s*' + name + r'\s*=====(.*?)(?=\n=====[^=]|\Z)', text, re.S)
    return m.group(1) if m else ''


def sub(text, name):
    m = re.search(r'\n====\s*' + name + r'[^=]*====(.*?)(?=\n====|\Z)', text, re.S)
    return m.group(1) if m else ''


def bullets(block, cur):
    return [norm_id(m, cur) for m in re.findall(r'^\s+\*[^\[\n]*\[\[([^|\]]+)', block, re.M)]


def bullet_notes(block, cur):
    return [(norm_id(m, cur), n) for m, n in re.findall(r'^\s+\*[^\[\n]*\[\[([^|\]]+)[^\n(]*(?:\(for ([^)]*)\))?', block, re.M)]


def num(s):
    m = re.search(r'-?\d[\d,]*\.?\d*', s or '')
    return float(m.group(0).replace(',', '')) if m else None


def infobox(text, cur):
    box = re.search(r'<WRAP right>(.*?)</WRAP>', text, re.S)
    if not box:
        return None
    lines = box.group(1).strip().split('\n')
    head = [clean(c) for _, c in SPLIT(lines[0].strip())]
    out = {'_name': head[0] if head else '', '_flags': [h for h in head[1:] if h], 'cost': {}, '_icon': None}
    sect = 'main'
    for ln in lines[1:]:
        cells = SPLIT(ln.strip())
        if not cells:
            continue
        if ln.strip().startswith('^'):
            sect = 'cost' if 'cost' in clean(cells[0][1]).lower() else clean(cells[0][1]).lower()
            continue
        key = clean(cells[0][1])
        vals = [clean(c) for _, c in cells[1:]]
        if key.lower() == 'profession':
            m = SPRITE.search(ln)
            out['_prof_icon'] = m.group(1) if m else None
        if key.lower() == 'icon':
            m = SPRITE.search(ln)
            out['_icon'] = m.group(1) if m else None
            continue
        if sect == 'cost':
            ids = links(cells[0][1], cur)
            out['cost'][ids[0] if ids else 'label:' + key] = num(vals[0]) if vals else None
        else:
            # several columns = vanilla (xBAN) vs MegaMod (xMOD); keep both, MegaMod last
            out[key.lower()] = [v for v in vals if v] or ['']
    return out


RULE = re.compile(r"\b(must be (?:placed|built|next)|placed (?:on|in|over|at)(?: or adjacent to)? (?:the )?water|adjacent to water|water's edge|(?:built|placed) on (?:a|the) shoreline|as a district within|required to designate|placed inside (?:its|the)[^.]*radius|only one may be built|max(?:imum)? (?:1|one) (?:per|instance)|limit(?:ed)? to (?:1|one)|requires placement|for placement on|placement on a|needs a (?:trader|jetty)|built over a|on a quay wall)", re.I)


def rules(text, box):
    """placement rules and limits, quoted from the page's description and infobox"""
    body = re.split(r'<WRAP right></WRAP>|</WRAP>', text, maxsplit=2)[-1].split('=====')[0]
    out = [x.strip() for x in re.split(r'(?<=[.!])\s+', clean(body))
           if RULE.search(x) and not re.search(r'\bcan (?:also )?be placed\b(?![^.]*\bonly\b)', x, re.I)]
    pl = (box.get('placement') or [''])[-1]
    if pl and pl.lower() not in ('land', 'any', '') and not any('water' in o.lower() for o in out):
        out.append(f'Placement: {pl}.')
    mi = (box.get('max instances') or [''])[-1]
    if mi and not any('only one' in o.lower() for o in out):
        out.append(f'Max instances: {mi}.')
    return out


def workers(v):
    if not v:
        return None
    m = re.match(r'\s*(\d+)\s*(?:–|-)\s*(\d+)(?:\s*\(default:?\s*(\d+)\))?', v[-1])
    if m:
        return {'min': int(m.group(1)), 'max': int(m.group(2)), 'default': int(m.group(3) or m.group(2))}
    n = num(v[-1])
    return {'min': int(n), 'max': int(n), 'default': int(n)} if n is not None else None


def last(box, key):
    v = box.get(key)
    return v[-1] if v else None


buildings, items = {}, {}
for f in sorted(glob.glob(os.path.join(RAW, '*.txt'))):
    pid = os.path.basename(f)[:-4].replace('__', ':')
    if pid.endswith(':start'):
        continue
    text = open(f, encoding='utf-8').read()
    if text.lstrip().startswith('<!DOCTYPE'):
        continue
    box = infobox(text, pid)
    if not box:
        continue
    tags = (re.search(r'\{\{tag>([^}]*)\}\}', text) or [None, ''])[1].split()
    mod = re.search(r'originally came from \*\*(.+?)\*\*', text)
    desc = clean(re.split(r'<WRAP right></WRAP>|</WRAP>', text, maxsplit=2)[-1].split('----')[0])
    desc = re.sub(r'^=+ ?Overview ?=+ ?', '', desc)[:300]
    if pid.startswith('buildings:'):
        recipes = []
        for ln in section(text, 'Recipes').split('\n'):
            if not ln.startswith('|'):
                continue
            cells = SPLIT(ln.strip())
            if len(cells) < 2:
                continue
            ins = [(num(q) or 1, norm_id(i, pid)) for q, i in re.findall(r'(\d+(?:\.\d+)?)?\s*\[\[([^|\]]+)', cells[0][1])]
            outs = links(cells[1][1], pid)
            if outs:
                recipes.append({'in': ins, 'out': outs})
        w = box.get('workers')
        b = {
            'name': box['_name'] or pid, 'icon': box['_icon'], 'flags': box['_flags'], 'group': pid.split(':')[1],
            'profession': last(box, 'profession'), 'prof_icon': box.get('_prof_icon'), 'size': last(box, 'size'), 'workers': workers(w),
            'workers_vanilla': workers(w[:1]) if w and len(w) > 1 else None,
            'radius': num(last(box, 'radius')), 'work_time': num(last(box, 'work time')),
            'work_cycle': num(last(box, 'work required')), 'storage': last(box, 'storage'),
            'housing': num(last(box, 'housing')), 'fuel_per': num(last(box, 'fuel per resource')),
            'temp': num(last(box, 'temp')), 'tool': last(box, 'tool'), 'max_prod': num(last(box, 'max production')),
            'happiness': last(box, 'happiness'), 'storecat': last(box, 'storage categories'), 'placement': last(box, 'placement'),
            'cost': box['cost'], 'produces': links(section(text, 'Produces'), pid), 'recipes': recipes,
            'where': [clean(x) for x in section(text, 'Where to Find').split('----')[0].strip().split('\n\n') if clean(x)],
            'mod': mod.group(1) if mod else ('Vanilla' if 'xBAN' in box['_flags'] else ''), 'tags': tags, 'desc': desc,
        }
        b['rules'] = rules(text, box)
        if not b['icon']:
            m = SPRITE.findall(section(text, 'Where to Find').split('\n\n')[0])
            b['icon'] = m[-1] if m else None
        for r in recipes:
            for o in r['out']:
                if o not in b['produces']:
                    b['produces'].append(o)
        buildings[pid] = b
    elif pid.startswith('wikipages:'):
        items[pid] = {
            'name': box['_name'] or pid, 'icon': box['_icon'], 'category': last(box, 'category'),
            'yield': last(box, 'yield'), 'edible': last(box, 'edible'),
            'value': num(last(box, 'trade value') or last(box, 'base value')),
            'weight': num(last(box, 'weight')), 'group': pid.split(':')[1], 'desc': desc, 'tags': tags,
            'made_at': bullets(sub(text, 'Procuring'), pid),
            'used_at': [[b, n] for b, n in bullet_notes(sub(text, 'Processing'), pid)],
        }

seeds, orchard = [], []
st = os.path.join(RAW, 'wikipages__seeds__start.txt')
if os.path.exists(st):
    t = open(st, encoding='utf-8').read()
    for ln in section(t, 'Crop Seeds').split('\n'):
        c = [clean(x) for _, x in SPLIT(ln.strip())] if ln.startswith('|') else []
        if len(c) >= 4:
            seeds.append({'id': links(ln, 'wikipages:seeds:start')[0], 'seed': c[0], 'crop': c[1], 'months': num(c[2]), 'value': num(c[3])})
    for ln in section(t, 'Orchard Seeds').split('\n'):
        c = [clean(x) for _, x in SPLIT(ln.strip())] if ln.startswith('|') else []
        if len(c) >= 5:
            orchard.append({'id': links(ln, 'wikipages:seeds:start')[0], 'seed': c[0], 'tree': c[1], 'cycle': num(c[2]), 'maturity': num(c[3]), 'value': num(c[4])})

climates = []
ct = os.path.join(RAW, 'climate__start.txt')
if os.path.exists(ct):
    t = open(ct, encoding='utf-8').read()
    tech = {}
    for ln in section(t, 'Technical Parameters').split('\n'):
        c = [clean(x) for _, x in SPLIT(ln.strip())] if ln.startswith('|') else []
        if len(c) >= 6:
            tech[c[0]] = {'base': num(c[1]), 'range': num(c[2]), 'swing': num(c[3]), 'yrtemp': num(c[4]), 'yrweather': num(c[5])}
    for ln in section(t, 'Available Climates').split('\n'):
        c = [clean(x) for _, x in SPLIT(ln.strip())] if ln.startswith('|') else []
        if len(c) >= 7:
            climates.append({'key': c[0], 'name': c[1], 'low': num(c[2]), 'high': num(c[3]), 'season': c[4], 'tornado': c[5], 'notes': c[6], **tech.get(c[0], {})})

json.dump({'buildings': buildings, 'items': items, 'seeds': seeds, 'orchard_seeds': orchard, 'climates': climates},
          open(OUT, 'w'), indent=1, ensure_ascii=False)
print(len(buildings), 'buildings,', len(items), 'items,', len(seeds), 'seeds,', len(orchard), 'orchard seeds,', len(climates), 'climates')
