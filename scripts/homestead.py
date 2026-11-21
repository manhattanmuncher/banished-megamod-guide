"""Generate the Homestead toolbar guide from wiki data: python3 -I homestead.py <db.json> <out.html>"""
import sys, json, html
DB, OUT = sys.argv[1:3]
B, I = (lambda d: (d['buildings'], d['items']))(json.load(open(DB)))
esc = html.escape

blds = [bid for bid, b in B.items() if any('Homestead' in [x.strip() for x in w.split('→')] for w in b['where'])]

FAMILIES = [  # (title, explanation, test)
    ('Crop patches', 'Butcher &amp; Baker. Same idea as Patchwork: one worker, year-round, no inputs. Toolbar: Homestead → Crop Patches.',
     lambda bid, b: 'Crop Patches' in str(b['where'])),
    ('Patchwork patches', 'Kid - Patchwork. One worker grows one crop <b>year-round with no inputs</b>. All free to build, 3 × 5 tiles. Toolbar: Homestead → Patchwork.',
     lambda bid, b: bid.startswith('buildings:fields:patch') and 'Patchwork' in str(b['where'])),
    ('Farmyards', 'KID Farmyard / Kid Workshop. A small farm plot that makes <b>several products at once</b> (fruit, grain, vegetables, eggs, milk and more). 2 workers, about 7 Logs.',
     lambda bid, b: bid.startswith(('buildings:fields:kf', 'buildings:fields:kwfarmyard'))),
    ('Botanical Garden greenhouses', 'Grow potato, wheat, oats and corn on a small plot for 4 Logs; the bigger sheds take more workers and work faster per cycle. The Herb Garden grows herbs and spices.',
     lambda bid, b: bid.startswith(('buildings:greenhouse:bg', 'buildings:fields:bgherb'))),
    ('Home Grown patches', 'Free garden patches that <b>need an input</b>: compost (onion, pepper, pumpkin, squash, tomato) or fertilizer (rice).',
     lambda bid, b: bid.startswith('buildings:greenhouse:hgpatch')),
    ('Hedgerows', 'Free strips that workers harvest for a mix of products (nuts, berries, honey, flax, eggs, branches, firewood). Named Spring, Summer, Fall and Winter by their look; the wiki does not say they only work in that season.',
     lambda bid, b: b['group'] == 'hedgerow'),
    ('Fairy Garden', 'Fairy Dust plots make Fairy Dust; the Fairy Garden patches use <b>1 Fairy Dust</b> per cycle to grow mixed food.',
     lambda bid, b: 'fairygarden' in bid),
    ('Groves, nuts and other plots', 'Fruit and nut plots (free; you choose the product), nut groves, maple and lemon groves, mushroom farm, seed collector, thatch patch and more.',
     lambda bid, b: True),
]


def ic(name):
    return f'<img class="ic" data-i="{esc(name)}" alt="">' if name else ''


def item(i):
    it = I.get(i)
    return f'<a href="#/{i}">{ic(it["icon"])}{esc(it["name"])}</a>' if it else esc(i.split(':')[-1].replace('_', ' '))


def cost(b):
    parts = [f'{q:g} {k.split(":")[-1].replace("_", " ").title()}' for k, q in b['cost'].items() if q and 'work' not in k.lower() and not k.endswith('Cost')]
    return ' + '.join(parts) or 'free'


placed, sections = set(), []
for title, expl, test in FAMILIES:
    rows = sorted((bid for bid in blds if bid not in placed and test(bid, B[bid])), key=lambda x: (B[x]['name'], x))
    if not rows:
        continue
    placed.update(rows)
    trs = []
    for bid in rows:
        b = B[bid]
        if b['group'] == 'decorations':
            continue
        ins = sorted({i for r in b['recipes'] for _, i in r['in']})
        w = (b.get('workers') or {}).get('max')
        trs.append(f'<tr><td><a href="#/{bid}">{ic(b["icon"])}{esc(b["name"])}</a>'
                   + (f' <span class="muted">({esc(bid.split(":")[-1])})</span>' if sum(1 for x in rows if B[x]['name'] == b['name']) > 1 else '')
                   + f'</td><td>{"".join(item(o) + " " for o in b["produces"]) or "–"}</td><td>{" ".join(item(i) for i in ins) or "nothing"}</td>'
                   f'<td>{w or "–"}</td><td>{b["work_time"]:g}</td><td>{esc(b["size"] or "–")}</td><td>{esc(cost(b))}</td></tr>'
                   if b['work_time'] else
                   f'<tr><td><a href="#/{bid}">{ic(b["icon"])}{esc(b["name"])}</a></td><td>{"".join(item(o) + " " for o in b["produces"]) or "–"}</td><td>{" ".join(item(i) for i in ins) or "nothing"}</td>'
                   f'<td>{w or "–"}</td><td>–</td><td>{esc(b["size"] or "–")}</td><td>{esc(cost(b))}</td></tr>')
    sections.append(f'<h2>{esc(title)} <span class="muted">({len(trs)})</span></h2><p>{expl}</p>'
                    '<div class="tw"><table><tr><th>Building</th><th>Makes</th><th>Needs</th><th>Workers</th><th>Work time</th><th>Size</th><th>Build cost</th></tr>'
                    + ''.join(trs) + '</table></div>')

page = ('<!-- title: Homestead toolbar -->\n<h1>Homestead toolbar</h1>'
        f'<p class="lead">Everything in Food Production → <b>Homestead</b>: {len(blds)} small farm buildings that make food and materials without big fields. '
        'Most need no seeds, and many need no inputs at all. Numbers come from each building\'s wiki page.</p>'
        '<div class="tip"><b>Quick picks</b><ul>'
        '<li><b>Food in any season, no seeds:</b> a Patchwork or Crop patch. See the <a href="#/tool:planner">Season planner</a> for your climate.</li>'
        '<li><b>Many foods from one building:</b> a Farmyard. Food variety keeps people healthy (<a href="#/mechanics:citizens:start">Citizens</a>).</li>'
        '<li><b>Free and no inputs:</b> hedgerows and Fruit and Nut plots.</li>'
        '<li><b>Needs a supply chain:</b> Home Grown patches (compost or fertilizer) and Fairy Garden patches (Fairy Dust).</li></ul></div>'
        '<p class="muted">Work time is per cycle (lower is faster). The wiki does not say how many items one cycle makes.</p>'
        + ''.join(sections))
open(OUT, 'w').write(page)
print('homestead:', len(blds), 'buildings in', len(sections), 'sections')
