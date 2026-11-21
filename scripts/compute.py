"""Derive lookup/tier/progression/cheatsheet data from db.json: python3 -I compute.py <db.json> <out_tools.json>
Every number comes from the wiki pages; rankings only reorder wiki values."""
import sys, json, re, math
from collections import defaultdict

DB, OUT = sys.argv[1:3]
d = json.load(open(DB))
B, I = d['buildings'], d['items']

CAT = {'Custom0': 'Crafted Items', 'Custom1': 'Forged Items', 'Custom2': 'Fabrics', 'Custom3': 'Industrial',
       'Custom4': 'Materials', 'Custom5': 'Construction', 'Custom6': 'Precious', 'Custom7': 'Miscellaneous',
       'CoalFuel': 'Minerals', 'Textile': 'Textiles (raw)', 'Health': 'Herbs & Health'}
START = ['wikipages:wood:log', 'wikipages:stone:stone', 'wikipages:iron:iron', 'wikipages:fuel:firewood', 'wikipages:tool:tool']
NOT_PRODUCTION = {'trading_post', 'market', 'storage', 'houses', 'roads', 'bridges', 'tunnels'}
by_name = {v['name'].lower(): k for k, v in I.items()}


def cat(it):
    c = (it.get('category') or '').strip('"')
    return CAT.get(c, c) or 'Other'


def cost_items(b):
    out = {}
    for k, q in b['cost'].items():
        if k.startswith('label:'):
            k = by_name.get(k[6:].lower())
        if k and k in I:
            out[k] = q
    return out


# ---- who makes / uses what (item pages + building pages combined) ----
made, used, build_needs = defaultdict(set), defaultdict(set), defaultdict(set)
for iid, it in I.items():
    made[iid].update(x for x in it['made_at'] if x in B)
    used[iid].update(x for x, _ in it['used_at'] if x in B)
for bid, b in B.items():
    for o in b['produces']:
        made[o].add(bid)
    for r in b['recipes']:
        for _, i in r['in']:
            used[i].add(bid)
    for i in cost_items(b):
        build_needs[i].add(bid)


def recipe_inputs(b, iid):
    """smallest total input count for one output of iid, None when no recipe, 0 when recipe needs nothing"""
    rs = [r for r in b['recipes'] if iid in r['out']]
    if not rs:
        return None, None
    best = min(rs, key=lambda r: sum(q for q, _ in r['in']))
    return sum(q for q, _ in best['in']), best['in']


def producer_facts(bid, iid):
    b = B[bid]
    n_in, ins = recipe_inputs(b, iid)
    w = (b.get('workers') or {}).get('max')
    if n_in:
        fam, key = 'recipe', (n_in, b['work_time'] or 1e9)
        rule = 'fewest input items per output, then shortest work time'
    elif b['work_time']:
        fam, key = 'cycle', (b['work_time'],)
        rule = 'shortest work time per cycle'
    elif b['radius'] and w:
        fam, key = 'area', (-w, -b['radius'])
        rule = 'most workers, then largest working radius'
    else:
        fam, key, rule = 'none', None, 'the wiki lists no output numbers'
    facts = []
    if ins:
        facts.append(' + '.join(f"{q:g} {I[i]['name'] if i in I else i.split(':')[-1]}" for q, i in ins) + ' → ' + (I[iid]['name'] if iid in I else iid.split(':')[-1]))
    if b['work_time']:
        facts.append(f"work time {b['work_time']:g}")
    if w:
        facts.append(f'{w} worker' + ('s' if w > 1 else ''))
    if b['radius']:
        facts.append(f"radius {b['radius']:g}")
    if b['max_prod']:
        facts.append(f"runs out after {b['max_prod']:g}")
    return fam, key, rule, ', '.join(facts)


def tiers(iid):
    fams = defaultdict(list)
    for bid in made[iid]:
        if B[bid]['group'] in NOT_PRODUCTION:
            continue
        fam, key, rule, facts = producer_facts(bid, iid)
        fams[fam].append((key, bid, rule, facts))
    out = []
    for fam, rows in fams.items():
        if fam == 'none':
            out += [[bid, 'No data', rule, facts] for _, bid, rule, facts in rows]
            continue
        rows.sort(key=lambda r: (r[0], B[r[1]]['name']))
        keys = sorted({r[0] for r in rows})
        for key, bid, rule, facts in rows:
            # tiers by distinct value so equal buildings always share a tier
            pos = keys.index(key) / max(1, len(keys) - 1) if len(keys) > 1 else 0
            t = 'High' if pos < 1 / 3 else 'Medium' if pos < 2 / 3 else 'Low'
            out.append([bid, t, rule, facts])
    order = {'High': 0, 'Medium': 1, 'Low': 2, 'No data': 3}
    return sorted(out, key=lambda r: (order[r[1]], B[r[0]]['name']))


# ---- progression levels ----
INF = 99
lvl_i = defaultdict(lambda: INF)
for s in START:
    lvl_i[s] = 0
lvl_b = {}
via = {}
for _ in range(30):
    changed = False
    for bid, b in B.items():
        ci = cost_items(b)
        lb = max([lvl_i[i] for i in ci] or [0])
        if lb != lvl_b.get(bid):
            lvl_b[bid] = lb
            changed = True
        if b['group'] in NOT_PRODUCTION or lb >= INF:
            continue
        for o in b['produces']:
            n_in, ins = recipe_inputs(b, o)
            li = max([lb] + [lvl_i[i] for _, i in (ins or [])])
            if li < INF and li + 1 < lvl_i[o] and o not in START:
                lvl_i[o] = li + 1
                via[o] = bid
                changed = True
    if not changed:
        break

def internal(iid, name):
    tail = iid.split(':')[-1]
    slug = re.sub(r'[^a-z0-9-]+', '_', name.lower()).strip('_')
    return tail[len(slug) + 1:] if tail.startswith(slug + '_') else ''


def hap_desc(b):
    m = re.search(r'happiness[^.]*?(?:radius of (\d+)|(\d+)-tile radius)', b.get('desc') or '', re.I)
    return float(m.group(1) or m.group(2)) if m else None


def stats(b):
    # numbers the tier lists rank on; only what the wiki page states
    st = b.get('storage') or ''
    capm = re.findall(r'\d[\d,]*', st)
    hap = re.match(r'\s*(Spirit|Goods|Entertainment|Safety|Health|Detraction)[^0-9]*?(?:radius\s*(\d+))?', b.get('happiness') or '')
    w = (b.get('workers') or {}).get('max')
    out = {'h': b.get('housing'), 'f': b.get('fuel_per'), 'st': float(capm[-1].replace(',', '')) if capm else None,
           'stt': 'per tile' in st, 'w': w, 'r': b.get('radius'), 'wt': b.get('work_time'), 'mp': b.get('max_prod'),
           'lab': b['cost'].get('label:Work Required'), 'sz': b.get('size'), 'mod': b.get('mod') or '',
           'rules': b.get('rules') or None,
           'wh': list(dict.fromkeys(w.replace('->', '→') for w in b.get('where') or []))[:3] or None,
           'hp': [hap.group(1), float(hap.group(2)) if hap.group(2) else hap_desc(b)] if hap else None}
    return {k: v for k, v in out.items() if v not in (None, '', False)}


# ---- compact payload for the page ----
items_out = {}
for iid, it in I.items():
    items_out[iid] = {
        'n': it['name'], 'i': it['icon'], 'c': cat(it), 'src': internal(iid, it['name']), 'y': it['yield'], 'v': it['value'], 'e': it['edible'],
        'lv': lvl_i[iid] if lvl_i[iid] < INF else None, 'via': via.get(iid),
        'tiers': tiers(iid),
        'used': sorted(used[iid], key=lambda x: B[x]['name']),
        'needs': sorted(build_needs[iid], key=lambda x: B[x]['name']),
        'buy': sorted(x for x in made[iid] if B[x]['group'] == 'trading_post'),
    }
bld_out = {}
for bid, b in B.items():
    bld_out[bid] = {'n': b['name'], 'i': b['icon'], 'g': b['group'], 'lv': lvl_b.get(bid) if lvl_b.get(bid, INF) < INF else None,
                    'cost': cost_items(b), 'out': b['produces'],
                    'rec': [[[[q, i] for q, i in r['in']], r['out']] for r in b['recipes']],
                    **stats(b)}

json.dump({'items': items_out, 'blds': bld_out, 'climates': d['climates'], 'seeds': d['seeds'], 'orchard': d['orchard_seeds'],
           'byname': by_name}, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
lv = defaultdict(int)
for v in items_out.values():
    lv[v['lv']] += 1
print('items per level:', dict(sorted(lv.items(), key=lambda x: (x[0] is None, x[0] or 0))))
