"""Generate 'Professions: who works where' from building infoboxes: python3 -I professions.py <db.json> <raw_dir> <out.html>"""
import sys, json, re, html, os
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dw2html import Conv

DB, RAW, OUT = sys.argv[1:4]
B = json.load(open(DB))['buildings']
esc = html.escape
SPLIT = Conv('x', set()).split_row


def key(name):
    return re.sub(r'[^a-z]', '', name.lower())


# death rates and notes from the wiki's Professions page
rates, rates_icon = {}, {}
src = open(os.path.join(RAW, 'professions__start.txt'), encoding='utf-8').read()
for ln in src.split('\n'):
    if not ln.startswith('|'):
        continue
    cells = [re.sub(r'<[^>]+>|\{\{[^}]*\}\}|\[\[[^|\]]*\||\]\]|\[\[', '', c).strip() for _, c in SPLIT(ln.strip())]
    if len(cells) >= 4 and cells[1]:
        rates[key(cells[1])] = (cells[3], cells[4] if len(cells) > 4 else '')
        icon = re.search(r'sprites\.worldofbanished\.com/([^?|}]+)', ln)
        if icon:
            rates_icon[icon.group(1)] = (cells[3], (cells[4] if len(cells) > 4 else '') or f'Listed on the wiki as {cells[1]}.')

profs = defaultdict(lambda: {'names': set(), 'icon': None, 'blds': []})
for bid, b in B.items():
    p = (b.get('profession') or '').strip()
    if not p:
        continue
    e = profs[key(p)]
    e['names'].add(p)
    e['icon'] = e['icon'] or b.get('prof_icon')
    e['blds'].append(bid)


def ic(name):
    return f'<img class="ic" data-i="{esc(name)}" alt="">' if name else ''


cards = []
for k, e in sorted(profs.items(), key=lambda x: -len(x[1]['blds'])):
    name = sorted(e['names'], key=len)[-1]
    rate, note = rates.get(k) or rates_icon.get(e['icon']) or ('', '')
    by_group = defaultdict(list)
    for bid in e['blds']:
        by_group[bid.split(':')[1].replace('_', ' ')].append(bid)
    chips = ''
    for g, ids in sorted(by_group.items(), key=lambda x: -len(x[1])):
        ids.sort(key=lambda x: B[x]['name'])
        chips += (f'<div class="pg"><span class="rs-lbl">{esc(g)} ({len(ids)})</span>'
                  + ''.join(f'<a href="#/{b}">{ic(B[b]["icon"])}{esc(B[b]["name"])}</a>' for b in ids) + '</div>')
    risk = f'<span class="facts">{esc(rate)} deaths per 100 workers per year</span>' if rate else '<span class="facts">death rate not listed on the wiki</span>'
    cards.append(f'<details class="prof" data-name="{esc(" ".join(e["names"]).lower())}"><summary>{ic(e["icon"])}<b>{esc(name)}</b>'
                 f'<span class="pc">{len(e["blds"])} building{"s" if len(e["blds"]) > 1 else ""}</span>{risk}</summary>'
                 + (f'<p class="muted">{esc(note)}</p>' if note else '') + chips + '</details>')

page = ('<!-- title: Professions: who works where -->\n<h1>Professions: who works where</h1>'
        f'<p class="lead">Every profession the wiki names on a building page ({len(profs)} professions, {sum(len(e["blds"]) for e in profs.values())} buildings), '
        'with the buildings that employ it. Death rates come from the <a href="#/professions:start">Professions</a> page. Click a profession to see its buildings.</p>'
        '<div class="toolbar"><input type="search" data-filter=".prof" placeholder="Filter professions, e.g. miner" aria-label="Filter professions" style="min-width:300px"></div>'
        + ''.join(cards))
open(OUT, 'w').write(page)
print(len(profs), 'professions,', sum(1 for k, e in profs.items() if k in rates or e['icon'] in rates_icon), 'with a death rate')
