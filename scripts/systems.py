"""Generate system guides from wiki data: toolbar map, livestock, happiness, storage.
python3 -I systems.py <db.json> <raw_dir> <out_dir>"""
import sys, os, re, json, html, glob
from collections import defaultdict, Counter
DB, RAW, OUT = sys.argv[1:4]
d = json.load(open(DB))
B, I = d['buildings'], d['items']
esc = html.escape


def ic(name):
    return f'<img class="ic" data-i="{esc(name)}" alt="">' if name else ''


def blink(bid):
    b = B[bid]
    return f'<a href="#/{bid}">{ic(b["icon"])}{esc(b["name"])}</a>'


def num(s):
    m = re.findall(r'\d[\d,]*\.?\d*', s or '')
    return float(m[-1].replace(',', '')) if m else None


def mats(b):
    return sum(q or 0 for k, q in b['cost'].items() if 'work' not in k.lower() and not k.endswith('Cost'))


def cost_txt(b):
    parts = [f'{q:g} {k.split(":")[-1].replace("_", " ").title()}' for k, q in b['cost'].items() if q and 'work' not in k.lower() and not k.endswith('Cost')]
    return ' + '.join(parts) or 'free'


def write(name, title, body):
    open(os.path.join(OUT, name + '.html'), 'w').write(f'<!-- title: {title} -->\n<h1>{esc(title)}</h1>' + body)


# ---------------- toolbar map ----------------
tops, subs, examples = Counter(), defaultdict(Counter), defaultdict(lambda: defaultdict(list))
for bid, b in B.items():
    seen = set()
    for w in b['where']:
        p = [x.strip() for x in re.split(r'→|->', w) if x.strip()]
        if len(p) < 2 or p[0] in seen:
            continue
        seen.add(p[0])
        tops[p[0]] += 1
        s2 = p[1] if len(p) > 2 else '(directly here)'
        subs[p[0]][s2] += 1
        if len(examples[p[0]][s2]) < 4:
            examples[p[0]][s2].append(bid)
cards = []
for t, n in tops.most_common():
    if n < 3:
        continue
    rows = ''.join(f'<tr><td><b>{esc(s2)}</b></td><td>{c}</td><td>{" ".join(blink(x) for x in examples[t][s2])}</td></tr>'
                   for s2, c in subs[t].most_common())
    cards.append(f'<details class="prof" data-name="{esc(t.lower())} {esc(" ".join(subs[t]).lower())}"><summary><b>{esc(t)}</b><span class="pc">{n} buildings</span>'
                 f'<span class="facts">{len(subs[t])} menus</span></summary><div class="tw"><table><tr><th>Menu</th><th>Buildings</th><th>Examples</th></tr>{rows}</table></div></details>')
write('toolbars', 'Toolbar map',
      '<p class="lead">MegaMod puts the same building in several toolbars. This map lists every top-level toolbar from the wiki\'s “Where to Find” paths, '
      'the menus inside it and example buildings, so you know where to click.</p>'
      '<div class="tip"><b>Tip:</b> you don\'t need to learn the toolbars. Search a building here, open its page, and its <b>Where to Find</b> section gives the exact click path, often more than one.</div>'
      '<div class="toolbar"><input type="search" data-filter=".prof" placeholder="Filter toolbars or menus, e.g. storage" aria-label="Filter toolbars" style="min-width:300px"></div>'
      + ''.join(cards))

# ---------------- livestock ----------------
def clean(s):
    s = re.sub(r'\{\{[^}]*\}\}', '', s)
    s = re.sub(r'\[\[[^|\]]*\|([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'\[\[([^\]]*)\]\]', lambda m: m.group(1).split(':')[-1], s)
    return re.sub(r'<[^>]+>', '', s).strip()


animals = []
for f in sorted(glob.glob(os.path.join(RAW, 'livestock__livestock*.txt'))):
    t = open(f, encoding='utf-8').read()
    name = (re.search(r'^======\s*(.+?)\s*======', t, re.M) or [None, '?'])[1]
    box = dict((clean(a), clean(b2)) for a, b2 in re.findall(r'^\|\s*(.+?)\s*\|\s*(.+?)\s*\|', t, re.M))
    def sec(n):
        m = re.search(r'=====\s*' + n + r'\s*=====(.*?)(?=\n=====|\Z)', t, re.S)
        return [clean(x) for x in re.findall(r'^\s+\*\s*(.+)$', m.group(1), re.M)] if m else []
    icon = re.search(r'sprites\.worldofbanished\.com/([^?|}]+)', t)
    pid = os.path.basename(f)[:-4].replace('__', ':')
    where = (re.search(r'=====\s*Where to Find\s*=====(.*?)----', t, re.S) or [None, ''])[1]
    animals.append({'id': pid, 'name': name, 'icon': icon.group(1) if icon else None, 'value': box.get('Trade Value', ''),
                    'area': box.get('Pasture Area', ''), 'periodic': sec('Periodic Products'), 'slaughter': sec('Slaughter Products'),
                    'where': clean(where).replace('\n', ' ')})
rows = ''.join(f'<tr><td><a href="#/{a["id"]}">{ic(a["icon"])}{esc(a["name"])}</a></td><td>{esc("; ".join(a["periodic"]) or "–")}</td>'
               f'<td>{esc(", ".join(a["slaughter"]) or "–")}</td><td>{esc(a["area"] or "–")}</td><td>{esc(a["value"] or "–")}</td><td class="muted">{esc(a["where"][:90])}</td></tr>'
               for a in sorted(animals, key=lambda a: a['name']))
pastures = sorted((bid for bid, b in B.items() if b['group'] in ('pastures', 'animal_pens')), key=lambda x: B[x]['name'])
write('livestock', 'Livestock and pastures',
      f'<p class="lead">All {len(animals)} animals on the wiki: what they give while alive, what they give when slaughtered, and how much space they need.</p>'
      '<ol class="steps"><li><b>Get animals</b> Livestock is bought from merchants at a Trading Post (<a href="#/trading:start">Trading</a>). Some starting conditions include one (<a href="#/startconditions:start">Starting Conditions</a>).</li>'
      '<li><b>Give them a pasture</b> A pasture is a player-drawn area, like the [[b:buildings:pastures:pasture]]. Each animal lists the pasture area it needs.</li>'
      '<li><b>Collect products</b> “Periodic” products come while the animal lives (for example Sheep: Wool every 2.75 months). Slaughter products come when herders cull animals.</li></ol>'
      '<div class="tw"><table><tr><th>Animal</th><th>While alive</th><th>When slaughtered</th><th>Pasture area</th><th>Trade value</th><th>Where</th></tr>' + rows + '</table></div>'
      f'<h2>Pastures and animal pens ({len(pastures)})</h2><div class="chips">' + ''.join(blink(x) for x in pastures[:80]) + '</div>'
      + (f'<p class="muted">+ {len(pastures) - 80} more: see <a href="#/buildings:pastures:start">Pastures</a> and <a href="#/buildings:animal_pens:start">Animal Pens</a>.</p>' if len(pastures) > 80 else ''))

# ---------------- happiness ----------------
TYPES = {
    'Spirit': 'From chapels, churches, town halls and cemeteries.',
    'Goods': 'From markets and trading posts that hand out goods.',
    'Entertainment': 'From taverns and similar places; some need alcohol in stock.',
    'Safety': 'From wells, guard towers, court houses and fire-fighting pieces.',
    'Health': 'From hospitals and a few dairies.',
    'Detraction': '<b>Lowers</b> happiness nearby: mostly mines and quarries, also tanneries, charburners and brickworks. Keep homes out of range.',
}
by_type = defaultdict(list)
for bid, b in B.items():
    h = b.get('happiness') or ''
    m = re.match(r'\s*(Spirit|Goods|Entertainment|Safety|Health|Detraction)', h)
    if m:
        by_type[m.group(1)].append((num(re.search(r'radius\s*(\d+)', h).group(1)) if re.search(r'radius\s*(\d+)', h) else None, bid, h))
secs = []
for t, expl in TYPES.items():
    rows = by_type.get(t, [])
    if not rows:
        continue
    with_r = sorted((r for r in rows if r[0]), key=lambda r: (-r[0] if t != 'Detraction' else r[0], mats(B[r[1]]), B[r[1]]['name']))
    seen, top = set(), []
    for r in with_r:
        if B[r[1]]['name'] not in seen:
            seen.add(B[r[1]]['name']); top.append(r)
        if len(top) == 6:
            break
    radii = Counter(int(r[0]) for r in rows if r[0])
    common = ', '.join(f'{k} tiles ({v})' for k, v in radii.most_common(3))
    trs = ''.join(f'<tr><td>{blink(bid)}</td><td>{r:g}</td><td>{esc(h)}</td><td>{esc(cost_txt(B[bid]))}</td></tr>' for r, bid, h in top)
    label = 'Smallest radius' if t == 'Detraction' else 'Widest reach'
    secs.append(f'<h2>{t} <span class="muted">({len(rows)} buildings)</span></h2><p>{expl}' + (f' Most common radius: {common}.' if common else '') + '</p>'
                + (f'<div class="tw"><table><tr><th>{label}</th><th>Radius</th><th>Wiki says</th><th>Cost</th></tr>{trs}</table></div>' if trs else ''))
write('happiness', 'Happiness',
      '<p class="lead">Happy citizens work; unhappy ones idle (<a href="#/mechanics:citizens:start">Citizens</a>). Building pages list which kind of happiness a building gives and how far it reaches. '
      'Five kinds raise it; one, Detraction, lowers it.</p>'
      '<div class="tip"><b>How to use this:</b> place homes inside the radius of one building of each kind (Spirit, Goods, Entertainment, Safety, Health), and outside the radius of Detraction buildings. '
      'Births and marriages also raise happiness; deaths, sickness, starvation and freezing lower it.</div>' + ''.join(secs))

# ---------------- storage ----------------
def stclass(cat):
    c = (cat or '').lower()
    if not c:
        return None
    if 'food' in c and ('tools' in c or 'clothing' in c):
        return 'General (food and goods)'
    if any(w in c for w in ('grain', 'vegetable', 'fruit', 'protein')) and not any(w in c for w in ('fuel', 'wood', 'stone')):
        return 'Food'
    for k, v in [('alcohol', 'Alcohol'), ('coal', 'Coal'), ('fuel', 'Fuel'), ('wood', 'Wood'), ('stone', 'Stone'), ('iron', 'Iron'),
                 ('consumables', 'Consumables'), ('food', 'Food'), ('clothing', 'Clothing and textiles'), ('textile', 'Clothing and textiles')]:
        if k in c:
            return v
    return 'Other'


groups = defaultdict(list)
for bid, b in B.items():
    cl = stclass(b.get('storecat'))
    cap = num(b.get('storage'))
    if cl and cap and b['group'] in ('storage', 'stockpiles', 'market', 'trading_post') and b['group'] in ('storage', 'stockpiles'):
        groups[cl].append((cap, bid))
secs = []
for cl in sorted(groups, key=lambda c: -len(groups[c])):
    rows = groups[cl]
    big = sorted(rows, key=lambda r: (-r[0], mats(B[r[1]])))
    seen, top = set(), []
    for cap, bid in big:
        if B[bid]['name'] not in seen:
            seen.add(B[bid]['name']); top.append((cap, bid))
        if len(top) == 5:
            break
    eff = sorted(((cap / mats(B[bid]), cap, bid) for cap, bid in rows if mats(B[bid]) > 0 and 'per tile' not in (B[bid]['storage'] or '')), key=lambda r: -r[0])[:3]
    trs = ''.join(f'<tr><td>{blink(bid)}</td><td>{cap:,.0f}{" per tile" if "per tile" in (B[bid]["storage"] or "") else ""}</td><td>{esc(cost_txt(B[bid]))}</td><td>{esc(B[bid]["size"] or "–")}</td></tr>' for cap, bid in top)
    effs = ' · '.join(f'{blink(bid)} <span class="facts">{cap:,.0f} for {mats(B[bid]):g} materials</span>' for _, cap, bid in eff)
    secs.append(f'<h2>{cl} <span class="muted">({len(rows)} buildings)</span></h2>'
                f'<div class="tw"><table><tr><th>Biggest</th><th>Capacity</th><th>Cost</th><th>Size</th></tr>{trs}</table></div>'
                + (f'<p><b>Most storage per material:</b> {effs}</p>' if effs else ''))
write('storage', 'Storage',
      '<p class="lead">Every barn, cart and stockpile on the wiki lists what it stores (“Storage Categories”) and how much. Grouped by what they hold, biggest first.</p>'
      '<div class="tip">Stockpiles hold raw materials per tile; barns hold food and goods. Build storage close to where things are made and used: '
      'shorter walks mean more work (<a href="#/mechanics:pathing:start">Pathfinding</a>). Set resource limits so one resource can\'t fill everything (<a href="#/mechanics:limits:start">Resource Limits</a>).</div>'
      + ''.join(secs))
print('systems:', len(cards), 'toolbars,', len(animals), 'animals,', sum(len(v) for v in by_type.values()), 'happiness buildings,', sum(len(v) for v in groups.values()), 'storage buildings')
