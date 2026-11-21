"""BFS crawl of worldofbanished.com DokuWiki via do=export_raw. Resumable."""
import os, re, sys, time, json, subprocess, urllib.parse

OUT = sys.argv[1]  # directory for raw pages
DELAY = 2.0  # robots.txt Crawl-delay
BASE = 'https://worldofbanished.com/wiki/doku.php?id={}&do=export_raw'
UA = 'Mozilla/5.0 (personal offline wiki copy)'
LINK = re.compile(r'\[\[([^\]|#?]+)')

def norm(pid, cur):
    pid = pid.strip().lower().replace(' ', '_')
    if pid.startswith(('http:', 'https:', 'mailto:')) or '>' in pid:
        return None
    ns = cur.split(':')[:-1]
    if pid.startswith('..:'):
        pid = ':'.join(ns[:-1] + [pid[3:]])
    elif pid.startswith('.:'):
        pid = ':'.join(ns + [pid[2:]])
    elif pid.startswith(':'):
        pid = pid[1:]
    elif ':' not in pid:
        pid = ':'.join(ns + [pid])
    if pid.endswith(':'):
        pid += 'start'
    return pid

def path(pid):
    return os.path.join(OUT, pid.replace(':', '__') + '.txt')

os.makedirs(OUT, exist_ok=True)
HI = ('buildings:forester', 'buildings:fields', 'buildings:gathering', 'buildings:fuel', 'buildings:houses',
      'buildings:storage', 'buildings:fishing', 'buildings:hunting', 'buildings:pastures', 'buildings:greenhouse',
      'wikipages:grain', 'wikipages:vegetable', 'wikipages:fruit', 'wikipages:food', 'wikipages:wood', 'wikipages:fuel',
      'mechanics', 'climate', 'startconditions', 'livestock', 'terrain', 'disasters', 'trading')
seen, queue, hi = {'start'}, ['start'], []
failed = []
n = 0
while queue or hi:
    pid = hi.pop(0) if hi else queue.pop(0)
    p = path(pid)
    if os.path.exists(p):
        text = open(p, encoding='utf-8').read()
    else:
        t0 = time.time()
        try:
            r = subprocess.run(['curl', '-sf', '-m', '30', '-A', UA, BASE.format(urllib.parse.quote(pid, safe=':'))], capture_output=True, check=True)
            text = r.stdout.decode('utf-8', 'replace').lstrip('﻿')
        except Exception as e:
            failed.append([pid, str(e)])
            time.sleep(DELAY)
            continue
        if text.lstrip().startswith('<!DOCTYPE'):  # the wiki answers missing pages with an HTML page
            failed.append([pid, 'page does not exist'])
            continue
        open(p, 'w', encoding='utf-8').write(text)
        n += 1
        time.sleep(max(0, DELAY - (time.time() - t0)))
        if n % 50 == 0:
            print(f'{n} fetched, {len(hi)} priority + {len(queue)} queued, {len(seen)} seen', flush=True)
    for m in LINK.findall(text):
        t = norm(m, pid)
        if t and t not in seen:
            seen.add(t)
            (hi if t.startswith(HI) else queue).append(t)

json.dump(failed, open(os.path.join(OUT, '..', 'failed.json'), 'w'), indent=1)
print(f'done: {n} fetched, {len(seen)} seen, {len(failed)} failed', flush=True)
