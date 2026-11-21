"""Generate the 'Best of' cheatsheet page from wiki data: python3 -I cheat.py <db.json> <tools.json> <out.html>"""
import sys, json, html, re
DB, TOOLS, OUT = sys.argv[1:4]
d, t = json.load(open(DB)), json.load(open(TOOLS))
B, I, TI = d['buildings'], d['items'], t['items']
esc = html.escape


def ic(name):
    return f'<img class="ic" data-i="{esc(name)}" alt="">' if name else ''


def blink(bid):
    b = B[bid]
    return f'<a href="#/{bid}">{ic(b["icon"])}{esc(b["name"])}</a>'


def ilink(iid):
    it = I.get(iid)
    return f'<a href="#/{iid}">{ic(it["icon"])}{esc(it["name"])}</a>' if it else esc(iid)


def items_matching(pat, cats=None):
    rx = re.compile(pat, re.I)
    return [k for k, v in I.items() if rx.search(v['name']) and (not cats or (v.get('category') or '') in cats)]


FAM_RULE = {'cycle': 'shortest work time per cycle (needs no inputs)',
            'recipe': 'fewest input items per output, then shortest work time',
            'area': 'most workers, then largest working radius'}


def fam_key(bid, iid):
    b = B[bid]
    rs = [r for r in b['recipes'] if iid in r['out']]
    n_in = min((sum(q for q, _ in r['in']) for r in rs), default=0)
    w = (b.get('workers') or {}).get('max') or 0
    if n_in:
        return 'recipe', (n_in, b['work_time'] or 1e9)
    if b['work_time']:
        # ties: a mine that never runs out beats one that does, then the longest-lasting
        return 'cycle', (b['work_time'], 1 if b['max_prod'] else 0, -(b['max_prod'] or 0))
    if b['radius'] and w:
        return 'area', (-w, -b['radius'])
    return None, None


def ranked(iids, group=None, need_input=None, fams=('cycle', 'recipe', 'area')):
    """producers of any of iids, best first, compared on raw wiki numbers within one ranking rule"""
    rows = []
    for iid in iids:
        for bid, tier, rule, facts in TI.get(iid, {}).get('tiers', []):
            if group and B[bid]['group'] not in group:
                continue
            if need_input and not any(any(i in need_input for _, i in r['in']) for r in B[bid]['recipes'] if iid in r['out']):
                continue
            fam, key = fam_key(bid, iid)
            if need_input:
                r = next(r for r in B[bid]['recipes'] if iid in r['out'] and any(i in need_input for _, i in r['in']))
                b = B[bid]
                facts = ' + '.join(f"{q:g} {I[i]['name'] if i in I else i.split(':')[-1]}" for q, i in r['in']) + f" → {I[iid]['name']}"
                facts += (f", work time {b['work_time']:g}" if b['work_time'] else '') + (f", {b['workers']['max']} worker" + ('s' if b['workers']['max'] > 1 else '') if b.get('workers') else '')
                fam, key = 'recipe', (sum(q for q, _ in r['in']), b['work_time'] or 1e9)
            if fam in fams:
                rows.append((fams.index(fam), key, FAM_RULE[fam], facts, bid, iid))
    rows.sort(key=lambda r: (r[0], r[1], B[r[4]]['name']))
    return [(None, r[2], r[3], r[4], r[5]) for r in rows]


def block(title, win='', facts='', alts=(), why='', body=''):
    """one cheatsheet entry: title, winner, its numbers, runner-ups, then why"""
    alt = ''.join(f'<li>{a}</li>' for a in alts)
    return (f'<section class="cs"><h3>{title}</h3>'
            + (f'<div class="cs-win">{win}</div>' if win else '')
            + (f'<div class="cs-facts">{facts}</div>' if facts else '') + body
            + (f'<div class="cs-alts"><span class="cs-lbl">Runner-ups</span><ul>{alt}</ul></div>' if alt else '')
            + (f'<p class="cs-why">{why}</p>' if why else '') + '</section>')


def row(title, rows, note='', n=3):
    if not rows:
        return block(title, body='<p class="muted">The wiki has no producer data for this.</p>')
    rule = rows[0][1]
    win = rows[0]
    seen, alts = {win[3]}, []
    names = {B[win[3]]['name']}
    for r in rows[1:]:
        if r[3] not in seen and B[r[3]]['name'] not in names and len(alts) < n - 1:
            seen.add(r[3]); names.add(B[r[3]]['name']); alts.append(r)
    return block(title, blink(win[3]), f'Makes {ilink(win[4])} · {esc(win[2])}',
                 [f'{blink(r[3])} <span class="facts">{esc(r[2])}</span>' for r in alts],
                 f'Ranked by {esc(rule)}.{(" " + note) if note else ""}')


groups = []


def group(name):
    groups.append([name, []])


def add(x):
    groups[-1][1].append(x)


# --- food ---
group('Food')
seed_rows = []
for s in d['seeds']:
    crop = t['byname'].get(s['crop'].lower()) or t['byname'].get(s['crop'].lower().rstrip('s'))
    y = I.get(crop, {}).get('yield') if crop else None
    m = re.match(r'\s*(\d+)\s*/\s*(\d+)', y or '')
    if m and s['months']:
        seed_rows.append((int(m.group(2)) / s['months'], s, crop, y))
seed_rows.sort(key=lambda r: (-r[0], r[1]['crop']))
if seed_rows:
    best = seed_rows[0][0]
    tied = [r for r in seed_rows if abs(r[0] - best) < 1e-9]
    nxt = [r for r in seed_rows if r[0] < best - 1e-9][:3]
    add(block('Best crop seed',
              facts=f'{len(tied)} crops tie: yield {esc(tied[0][3])} (uneducated/educated) in {tied[0][1]["months"]:g} months.',
              body=f'<div class="chips">{"".join(ilink(r[2]) for r in tied)}</div>',
              alts=[f'{ilink(r[2])} <span class="facts">{esc(r[3])} in {r[1]["months"]:g} months</span>' for r in nxt],
              why='Ranked by educated yield ÷ growth months. Plant whichever tied seed you have; merchants sell more. '
                  'In a short-season climate, check the <a href="#/tool:planner">Season planner</a> first.'))
else:
    add(row('Best crop seed', []))

edible = [k for k, v in I.items() if (v.get('edible') or '').lower() == 'yes']
staple = [k for k in edible if (I[k].get('category') or '').strip('"') in ('Grain', 'Vegetable', 'Fruit', 'Protein')]
add(row('Best seedless field patch', ranked(staple, group={'fields'}), 'Patches grow year-round with no seeds (wiki: Fields).'))
add(row('Best greenhouse', ranked(staple, group={'greenhouse'})))
add(row('Best gatherer', ranked(edible, group={'gathering'})))
add(row('Best fishing building', ranked(items_matching(r'^fish$'), group={'fishing'}, fams=('area', 'cycle', 'recipe'))))
add(row('Best hunting building', ranked(items_matching(r'^(venison|meat|leather)$'), group={'hunting'}, fams=('area', 'cycle', 'recipe'))))

# --- wood and fuel ---
group('Wood and fuel')
log = ['wikipages:wood:log']
add(row('Best forester (most output)', ranked(log, group={'forester'}, fams=('area',))))
fo = [(sum((q or 0) for k, q in B[bid]['cost'].items() if 'work' not in k.lower()), B[bid]['cost'].get('label:Work Required') or 0, bid) for bid in B
      if B[bid]['group'] == 'forester' and 'wikipages:wood:log' in B[bid]['produces'] and (B[bid].get('workers') or {}).get('max', 0) >= 4]
fo.sort()
if fo:
    mat = lambda c, w: f'{w:g} labour, ' + (f'{c:g} materials' if c else 'no materials listed')
    add(block('Best forester (cheapest with 4+ workers)', blink(fo[0][2]), f'{mat(fo[0][0], fo[0][1])} · radius {B[fo[0][2]]["radius"] or 0:g}',
              [f'{blink(b)} <span class="facts">{mat(c, w)}, radius {B[b]["radius"] or 0:g}</span>' for c, w, b in fo[1:3]],
              'Ranked by lowest total build materials among foresters with at least 4 workers.'))
add(row('Best log source without planting', ranked(log, fams=('cycle',)), 'Collects logs (e.g. floating logs) instead of growing trees.'))
add(row('Best firewood maker', ranked(['wikipages:fuel:firewood'], group={'fuel'})))
add(row('Best lumber maker', ranked(['wikipages:custom5:lumber'])))

# --- clothing ---
group('Clothing')
wool = [k for k, v in I.items() if v['name'].lower() == 'wool']
add(row('Best wool clothes', ranked([k for k, v in I.items() if v['group'] == 'clothing'], need_input=set(wool))))
add(row('Best leather clothes', ranked([k for k, v in I.items() if v['group'] == 'clothing'], need_input={'wikipages:textile:leather'})))

# --- mining and tools ---
group('Mining and tools')
add(row('Best stone source', ranked(['wikipages:stone:stone'])))
add(row('Best iron source', ranked(['wikipages:iron:iron'])))
add(row('Best coal source', ranked(items_matching(r'^coal$'))))
add(row('Best copper ore source', ranked(items_matching(r'copper ore|^copper$'))))
add(row('Best tool maker', ranked(['wikipages:tool:tool'])))

# --- housing ---
group('Housing')
houses = [(B[b]['housing'] or 0, B[b]['fuel_per'] or 0, b) for b in B if B[b]['group'] == 'houses' and B[b]['housing']]
if houses:
    warm = sorted(houses, key=lambda h: (-h[1], -h[0]))[:3]
    big = sorted(houses, key=lambda h: (-h[0], -h[1]))[:3]
    add(block('Warmest house (least firewood)', blink(warm[0][2]), f'warmth {warm[0][1]:g} per fuel · houses {warm[0][0]:g}',
              [f'{blink(b)} <span class="facts">warmth {f:g} per fuel, houses {h:g}</span>' for h, f, b in warm[1:]],
              'Ranked by highest “Fuel Per Resource” (wiki: warmth units per fuel item; higher is more efficient).'))
    add(block('Biggest house', blink(big[0][2]), f'houses {big[0][0]:g} · warmth {big[0][1]:g} per fuel',
              [f'{blink(b)} <span class="facts">houses {h:g}, warmth {f:g} per fuel</span>' for h, f, b in big[1:]],
              'Ranked by most settlers housed.'))

# --- every resource: best way to get it ---
import glob, os
RAWDIR = os.path.join(os.path.dirname(DB), 'raw')
NS = {}
for f in glob.glob(os.path.join(RAWDIR, 'wikipages__*__start.txt')):
    m = re.search(r'^======\s*(.+?)\s*======', open(f, encoding='utf-8').read(), re.M)
    NS[os.path.basename(f).split('__')[1]] = m.group(1) if m else os.path.basename(f).split('__')[1]
SHORT = {FAM_RULE['cycle']: 'fastest, needs no inputs', FAM_RULE['recipe']: 'fewest inputs, then fastest',
         FAM_RULE['area']: 'most workers, then widest radius'}
TB = t['blds']
every = {}
for iid, it in sorted(I.items(), key=lambda x: x[1]['name'].lower()):
    ns = NS.get(iid.split(':')[1], iid.split(':')[1].title())
    rows = ranked([iid])
    nm = esc(it['name']) + (f' <span class="muted">({esc(t["items"][iid]["src"])})</span>' if t['items'][iid].get('src') and sum(1 for v in I.values() if v['name'] == it['name']) > 1 else '')
    head = f'<a class="rs-name" href="#/{iid}">{ic(it["icon"])}{nm}</a>'
    if rows:
        win = rows[0]
        alts, seen = [], {B[win[3]]['name']}
        for r in rows[1:]:
            if B[r[3]]['name'] not in seen and len(alts) < 2:
                seen.add(B[r[3]]['name']); alts.append(r)
        html_ = (f'<div class="rs" data-name="{esc(it["name"].lower())}">{head}'
                 f'<div class="rs-best"><span class="rs-lbl">Best</span>{blink(win[3])}<span class="facts">{esc(win[2])} · {SHORT.get(win[1], win[1])}</span></div>'
                 + (f'<div class="rs-alt"><span class="rs-lbl">Also</span>' + ''.join(f'{blink(r[3])}' for r in alts) + '</div>' if alts else '')
                 + (f'<div class="muted">{len(rows)} buildings make it — <a href="#/tool:lookup/{iid}">see all</a></div>' if len(rows) > 3 else '') + '</div>')
        every.setdefault(ns, [[], []])[0].append(html_)
    else:
        buy = t['items'][iid].get('buy') or []
        note = 'buy from merchants' if buy or iid.startswith('wikipages:seeds') else 'no source listed on the wiki'
        tw = [k for k, v in I.items() if k != iid and v['name'] == it['name'] and t['items'].get(k, {}).get('tiers')]
        if tw:
            note = 'no source on this page; see the other ' + esc(it['name']) + ' page: ' + ', '.join(f'<a href="#/{k}">{esc(I[k]["name"])} ({esc(t["items"][k]["c"])})</a>' for k in tw)
        every.setdefault(ns, [[], []])[1].append(f'<span class="rs-none" data-name="{esc(it["name"].lower())}">{head} <span class="muted">— {note}</span></span>')  # note may hold links
n_made = sum(len(v[0]) for v in every.values())
groups.append(['Every resource', []])
ev_jump = ''.join(f'<a class="chip" data-jump="ev-{i}">{esc(ns)}</a>' for i, ns in enumerate(sorted(every)))
ev_body = (f'<p class="lead">All {n_made} resources a building can make, and the best way to get each one. Resources no building makes are listed at the end of each group.</p>'
           '<div class="toolbar"><input type="search" data-filter=".rs, .rs-none" placeholder="Filter resources, e.g. gemstone" aria-label="Filter resources" style="min-width:300px"></div>'
           f'<div class="chips">{ev_jump}</div>'
           + ''.join(f'<h3 id="ev-{i}" class="ev-h">{esc(ns)}</h3><div class="rs-grid">{"".join(every[ns][0])}</div>'
                     + (f'<div class="rs-nones">{"".join(every[ns][1])}</div>' if every[ns][1] else '')
                     for i, ns in enumerate(sorted(every))))

jump = ''.join(f'<a class="chip" data-jump="cs-{i}">{esc(g)}</a>' for i, (g, _) in enumerate(groups))
body = ''.join(f'<h2 id="cs-{i}">{esc(g)}</h2>' + (ev_body if g == 'Every resource' else f'<div class="cs-grid">{"".join(items)}</div>') for i, (g, items) in enumerate(groups))
html_out = ('<!-- title: Best-of cheatsheet -->\n<h1>Best-of cheatsheet</h1>'
            '<p class="lead">The top pick in each area, then the best way to get every resource. Chosen only from numbers on the wiki; each entry says how it was ranked.</p>'
            '<div class="warn">The wiki does not say how many items one work cycle makes, so “shortest work time” compares speed per cycle, not total output.</div>'
            f'<div class="chips">{jump}</div>' + body)
open(OUT, 'w').write(html_out)
print('cheatsheet highlights:', sum(len(x) for _, x in groups), '| every resource:', n_made, 'made,', sum(len(v[1]) for v in every.values()), 'not made')
