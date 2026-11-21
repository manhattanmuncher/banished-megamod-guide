// Interactive tools: resource lookup, hover cards, progression tree, season planner.
const T = D.tools, TI = T.items, TB = T.blds;
const iconImg = (n, cls = 'ic') => n && ICONS[n] ? `<img class="${cls}" src="${ICONS[n]}" alt="">` : `<span class="${cls} noic"></span>`;
const NAMECOUNT = {};
for (const v of Object.values(T.items)) NAMECOUNT[v.n] = (NAMECOUNT[v.n] || 0) + 1;
const iname = id => !TI[id] ? id.split(':').pop().replace(/_/g, ' ') : NAMECOUNT[TI[id].n] > 1 ? `${TI[id].n} (${TI[id].src || TI[id].c || id.split(':')[1]})` : TI[id].n;
const bname = id => TB[id] ? TB[id].n : id.split(':').pop();
const ichip = id => `<a class="chip" href="#/${id}" data-item="${id}">${iconImg(TI[id] && TI[id].i)}${esc(iname(id))}</a>`;
const bchip = id => `<a class="chip b" href="#/${id}">${iconImg(TB[id] && TB[id].i)}${esc(bname(id))}</a>`;
const lvName = l => l === null || l === undefined ? 'Trade only / unknown' : l === 0 ? 'Start' : 'Step ' + l;
const TIER_CLS = { High: 'hi', Medium: 'md', Low: 'lo', 'No data': 'nd' };

function madeFrom(id) {
  // items whose recipes take `id` as an input
  const out = new Set();
  for (const [bid, b] of Object.entries(TB)) for (const [ins, outs] of b.rec) if (ins.some(x => x[1] === id)) outs.forEach(o => out.add(o));
  out.delete(id);
  return [...out].filter(x => TI[x]).sort((a, b) => iname(a).localeCompare(iname(b)));
}

function twins(id) {
  // other wiki pages for an item with the same name (the wiki sometimes splits one item over several pages)
  const n = TI[id] && TI[id].n;
  return n ? Object.keys(TI).filter(k => k !== id && TI[k].n === n && TI[k].tiers.length) : [];
}
function twinNote(id) {
  const tw = twins(id);
  if (!tw.length || TI[id].tiers.length) return '';
  return `<div class="tip">The wiki lists no source on this ${esc(TI[id].n)} page, but it has ${tw.length > 1 ? tw.length + ' other pages' : 'another page'} called ${esc(TI[id].n)} that ${tw.length > 1 ? 'do' : 'does'}: ` +
    tw.map(k => `${ichip(k)} <span class="muted">${TI[k].tiers.length} building${TI[k].tiers.length > 1 ? 's' : ''} make it</span>`).join(' ') + '</div>';
}
function tierBlock(it, max = 99) {
  if (!it.tiers.length) return '<p class="muted">The wiki lists no building that makes this.' + (it.buy.length ? ' It can be bought.' : '') + '</p>';
  const byRule = {};
  for (const r of it.tiers) (byRule[r[2]] ||= []).push(r);
  return Object.entries(byRule).map(([rule, rows]) => `<div class="rule">Ranked by: ${esc(rule)}</div><ul class="tiers">` +
    rows.slice(0, max).map(([bid, tier, , facts]) => `<li><span class="tier ${TIER_CLS[tier]}">${tier}</span>${bchip(bid)}<span class="facts">${esc(facts)}</span></li>`).join('') +
    (rows.length > max ? `<li class="muted">+ ${rows.length - max} more in the Resource lookup</li>` : '') + '</ul>').join('');
}

function card(id, full) {
  const it = TI[id];
  if (!it) return '';
  const meta = [it.c, it.y && `yield ${it.y} (uneducated/educated)`, it.v != null && `trade value ${it.v}`, it.e === 'Yes' && 'edible']
    .filter(Boolean).map(esc).join(' · ');
  let h = `<div class="card-h">${iconImg(it.i, 'ic big')}<div><b>${esc(it.n)}</b><div class="muted">${meta}</div>` +
    `<div class="lv">Progression: <b>${lvName(it.lv)}</b>${it.via ? ` · first made at ${esc(bname(it.via))}` : ''}</div></div></div>`;
  if (full) h += `<h2 class="sec">Made at</h2>` + twinNote(id) + tierBlock(it, 999);
  else {
    const top = it.tiers.slice(0, 3);
    h += `<h2 class="sec">Made at</h2>` + twinNote(id) + (top.length ? `<ul class="tiers">${top.map(([bid, tier, , facts]) => `<li><span class="tier ${TIER_CLS[tier]}">${tier}</span>${bchip(bid)}<span class="facts">${esc(facts)}</span></li>`).join('')}</ul>` +
      (it.tiers.length > 3 ? `<div class="muted">+ ${it.tiers.length - 3} more — click for the full list</div>` : '') : '<p class="muted">The wiki lists no building that makes this.</p>');
  }
  if (it.buy.length) h += `<div class="muted">Also available from: ${it.buy.map(bchip).join(' ')}</div>`;
  const mf = madeFrom(id);
  h += `<h2 class="sec">Unlocks</h2><div class="muted">Needed to build <b>${it.needs.length}</b> building${it.needs.length === 1 ? '' : 's'} · ingredient for <b>${mf.length}</b> item${mf.length === 1 ? '' : 's'}</div>`;
  if (full) {
    if (mf.length) h += `<div class="chips">${mf.map(ichip).join('')}</div>`;
    if (it.needs.length) h += `<details><summary>Buildings that need ${esc(it.n)} to build (${it.needs.length})</summary><div class="chips">${it.needs.map(bchip).join('')}</div></details>`;
    if (it.used.length) h += `<details><summary>Buildings that use ${esc(it.n)} as input (${it.used.length})</summary><div class="chips">${it.used.map(bchip).join('')}</div></details>`;
    h += `<p><a href="#/${id}">Open the full ${esc(it.n)} wiki page →</a></p>`;
  }
  return h;
}

// ---------- hover cards ----------
const tip = document.createElement('div');
tip.className = 'tip-card';
document.body.appendChild(tip);
let tipFor = null, tipTimer = null;
function placeTip(a) {
  // beside the link, never over it or the links just below it
  const r = a.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight, gap = 14;
  let x = r.right + gap;
  if (x + w > window.innerWidth - 8) x = r.left - w - gap;
  let y = Math.min(window.innerHeight - h - 8, Math.max(8, r.top - 12));
  if (x < 8) { x = Math.min(window.innerWidth - w - 8, Math.max(8, r.left)); y = r.bottom + h + gap < window.innerHeight ? r.bottom + gap : Math.max(8, r.top - h - gap); }
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}
function showTip(a, id) {
  tipFor = id; tip.innerHTML = card(id, false); tip.style.display = 'block';
  tip.querySelectorAll('img.ic[data-i]').forEach(img => { const d = ICONS[img.dataset.i]; if (d) img.src = d; });
  placeTip(a);
}
function hideTip() { clearTimeout(tipTimer); tip.style.display = 'none'; tipFor = null; }
document.addEventListener('mouseover', ev => {
  const a = ev.target.closest('a[href^="#/wikipages:"]');
  if (!a || !matchMedia('(hover:hover)').matches) return;
  const id = decodeURIComponent(a.getAttribute('href').slice(2));
  if (!TI[id] || id === tipFor) return;
  clearTimeout(tipTimer);
  tipTimer = setTimeout(() => showTip(a, id), 350);
});
document.addEventListener('mouseout', ev => {
  const a = ev.target.closest('a[href^="#/wikipages:"]');
  if (a && !a.contains(ev.relatedTarget)) hideTip();
});
document.addEventListener('scroll', hideTip, { passive: true });
window.addEventListener('hashchange', hideTip);
document.addEventListener('focusin', ev => {
  const a = ev.target.closest && ev.target.closest('a[href^="#/wikipages:"]');
  if (!a) { hideTip(); return; }
  const id = decodeURIComponent(a.getAttribute('href').slice(2));
  if (TI[id]) showTip(a, id);
});
document.addEventListener('keydown', ev => { if (ev.key === 'Escape') hideTip(); });

// ---------- tool pages ----------
const CATS = [...new Set(Object.values(TI).map(x => x.c))].sort();
const sortedItems = Object.keys(TI).sort((a, b) => iname(a).localeCompare(iname(b)));

function lookupPage(sel) {
  main.innerHTML = `<div class="crumb"><a href="#/guide:home">Home</a> › Tools</div><h1>Resource lookup</h1>
  <p class="lead">Pick a resource to see which buildings make it, ranked into <span class="tier hi">High</span> <span class="tier md">Medium</span> <span class="tier lo">Low</span> tiers by the wiki's own numbers, and what it unlocks.</p>
  <div class="toolbar"><input id="lf" type="search" placeholder="Filter resources…" aria-label="Filter resources"><select id="lc" aria-label="Category"><option value="">All categories</option>${CATS.map(c => `<option>${esc(c)}</option>`).join('')}</select></div>
  <div class="split"><div id="lg" class="grid"></div><aside id="lp" class="panel">${sel ? card(sel, true) : '<p class="muted">Select a resource on the left.</p>'}</aside></div>`;
  const draw = () => {
    const f = $('#lf').value.toLowerCase(), c = $('#lc').value;
    $('#lg').innerHTML = sortedItems.filter(id => (!c || TI[id].c === c) && (!f || iname(id).toLowerCase().includes(f)))
      .map(id => `<button class="cell${id === sel ? ' on' : ''}" data-id="${id}">${iconImg(TI[id].i)}<span>${esc(iname(id))}</span></button>`).join('') || '<p class="muted">No match.</p>';
  };
  $('#lf').oninput = draw; $('#lc').onchange = draw; draw();
  $('#lg').onclick = ev => { const b = ev.target.closest('.cell'); if (b) location.hash = '#/tool:lookup/' + b.dataset.id; };
}

function treePage(sel) {
  const levels = {};
  for (const id of sortedItems) (levels[TI[id].lv ?? 'x'] ||= []).push(id);
  const keys = Object.keys(levels).filter(k => k !== 'x').map(Number).sort((a, b) => a - b);
  const blds = Object.keys(TB).sort((a, b) => bname(a).localeCompare(bname(b)));
  main.innerHTML = `<div class="crumb"><a href="#/guide:home">Home</a> › Tools</div><h1>Progression tree</h1>
  <p class="lead"><b>Start</b> is what every game begins with (Logs, Stone, Iron, Firewood, Tools). Each step needs a building you can afford with earlier steps. Click a resource to see what it needs and what it unlocks.</p>
  <div class="toolbar"><label for="fb">Plan a building:</label><input id="fb" list="fbl" placeholder="Type a building name, e.g. Tailor" style="min-width:280px"><datalist id="fbl">${blds.map(b => `<option value="${esc(bname(b))}">`).join('')}</datalist></div>
  <div id="fp"></div>
  <div class="split"><div class="levels">${keys.map(k => `<section><h2>${lvName(k)} <span class="muted">(${levels[k].length})</span></h2><div class="chips">${levels[k].map(id => `<button class="chip${id === sel ? ' on' : ''}" data-id="${id}">${iconImg(TI[id].i)}${esc(iname(id))}</button>`).join('')}</div></section>`).join('')}
  ${levels.x ? `<section><h2>${lvName(null)} <span class="muted">(${levels.x.length})</span></h2><p class="muted">No producer found on the wiki pages, so these come from merchants or the page is missing data.</p><div class="chips">${levels.x.map(id => `<button class="chip" data-id="${id}">${iconImg(TI[id].i)}${esc(iname(id))}</button>`).join('')}</div></section>` : ''}</div>
  <aside class="panel" id="tp">${sel ? card(sel, true) : '<p class="muted">Select a resource.</p>'}</aside></div>`;
  main.querySelector('.levels').onclick = ev => { const b = ev.target.closest('.chip'); if (b) location.hash = '#/tool:tree/' + b.dataset.id; };
  const byName = {}; blds.forEach(b => byName[bname(b).toLowerCase()] = b);
  $('#fb').onchange = () => {
    const bid = byName[$('#fb').value.toLowerCase()];
    if (!bid) return;
    const seen = new Set();
    const chain = (id, depth) => {
      if (seen.has(id) || depth > 6) return '';
      seen.add(id);
      const it = TI[id]; if (!it) return '';
      const via = it.via && TB[it.via];
      const ins = via ? (via.rec.find(r => r[1].includes(id)) || [[]])[0] : [];
      return `<li>${ichip(id)} <span class="muted">${lvName(it.lv)}${via ? ' · make at ' : ''}</span>${via ? bchip(it.via) : ''}` +
        ((via && (Object.keys(via.cost).some(c => TI[c] && TI[c].lv > 0) || ins.length)) ?
          `<ul>${[...new Set([...Object.keys(via.cost).filter(c => TI[c] && TI[c].lv > 0), ...ins.map(x => x[1])])].map(c => chain(c, depth + 1)).join('')}</ul>` : '') + '</li>';
    };
    const b = TB[bid];
    $('#fp').innerHTML = `<div class="focus"><h2 class="sec" style="font-size:16px;text-transform:none;letter-spacing:0;color:var(--ink)">To build ${bchip(bid)} you need</h2><ul class="chain">${Object.entries(b.cost).map(([c, q]) => `<li>${q ?? ''} × ${ichip(c)} <span class="muted">${lvName(TI[c] && TI[c].lv)}</span>${TI[c] && TI[c].lv > 0 ? `<ul>${chain(c, 0).replace(/^<li>.*?<\/span>/, '')}</ul>` : ''}</li>`).join('') || '<li class="muted">The wiki lists no materials for this building.</li>'}</ul></div>`;
  };
}

function plannerPage(key) {
  const C = T.climates, c = C.find(x => x.key === key) || C.find(x => x.key === 'Fair') || C[0];
  // shortcut: assumes temperature moves smoothly (cosine) between the wiki's winter low and summer high
  const frac = c.range ? (c.base - c.range >= 32 ? 1 : c.base + c.range <= 32 ? 0 : 1 - Math.acos((c.base - 32) / c.range) / Math.PI) : (c.base > 32 ? 1 : 0);
  const months = Math.round(frac * 12 * 10) / 10;
  const crops = T.seeds.map(s => {
    const crop = T.byname[s.crop.toLowerCase()] || T.byname[s.crop.toLowerCase().replace(/s$/, '')];
    const y = crop && TI[crop] && TI[crop].y, m = /(\d+)\s*\/\s*(\d+)/.exec(y || '');
    return { ...s, crop_id: crop, y, rate: m ? +m[2] / s.months : 0, spare: months - s.months };
  }).sort((a, b) => b.rate - a.rate || a.months - b.months);
  const fit = crops.filter(x => x.spare >= 0), nofit = crops.filter(x => x.spare < 0);
  const yearRound = Object.entries(TB).filter(([, b]) => (b.g === 'fields' || b.g === 'greenhouse') && b.out.some(o => TI[o] && TI[o].e === 'Yes') && !b.rec.some(r => r[0].length))
    .map(([id]) => id).sort((a, b) => bname(a).localeCompare(bname(b)));
  const unpredictable = (c.swing >= 10 || c.yrtemp >= 40);
  main.innerHTML = `<div class="crumb"><a href="#/guide:home">Home</a> › Tools</div><h1>Season planner</h1>
  <p class="lead">Pick the climate you chose at game start. Crops only grow while it is above freezing (32 °F) — <a href="#/climate:start">Climate</a>.</p>
  <div class="toolbar"><label>Climate: <select id="pc">${C.map(x => `<option value="${esc(x.key)}"${x === c ? ' selected' : ''}>${esc(x.name)}</option>`).join('')}</select></label></div>
  <div class="stats"><div><b>${c.low} °F</b><span>winter low</span></div><div><b>${c.high} °F</b><span>summer high</span></div><div><b>${esc(c.season)}</b><span>growing season (wiki)</span></div><div><b>≈ ${months} months</b><span>above freezing (estimate)</span></div><div><b>${esc(c.tornado)}</b><span>tornado risk</span></div></div>
  <p class="muted">${esc(c.notes)}. The month count is an estimate: it assumes temperature moves smoothly between the wiki's winter low and summer high.</p>
  ${unpredictable ? `<div class="warn">This climate is unpredictable (daily swing ${c.swing} °F, year-to-year change ${c.yrtemp}). Some years are colder than the numbers above, so prefer crops with months to spare.</div>` : ''}
  ${months >= 12 ? '<div class="tip">This climate never freezes: every crop grows year-round.</div>' : ''}
  ${months === 0 ? '<div class="warn">It never gets above freezing: no field crops grow. Use the year-round buildings below.</div>' : ''}
  <h2>Crops that fit (${fit.length})</h2><p class="muted">Sorted by educated yield per month of growth. Growth times and yields come from the wiki's Seeds table and crop pages.</p>
  <div class="tw"><table><tr><th>Crop</th><th>Seed</th><th>Grows in</th><th>Yield</th><th>Months to spare</th></tr>${fit.map(x => `<tr><td>${x.crop_id ? ichip(x.crop_id) : esc(x.crop)}</td><td>${TI[x.id] ? ichip(x.id) : `<a href="#/${x.id}">${esc(x.seed)}</a>`}</td><td>${x.months} mo</td><td>${esc(x.y || '–')}</td><td>${Math.round(x.spare * 10) / 10}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">None.</td></tr>'}</table></div>
  ${nofit.length ? `<details><summary>Crops that need a longer season (${nofit.length})</summary><div class="chips">${nofit.map(x => x.crop_id ? ichip(x.crop_id) : esc(x.crop)).join(' ')}</div></details>` : ''}
  <h2>Orchards</h2><p>Orchard trees take <b>${T.orchard[0] ? T.orchard[0].maturity : '?'} months</b> to mature, then fruit every ${T.orchard[0] ? T.orchard[0].cycle : '?'} months (wiki: <a href="#/wikipages:seeds:start">Seeds</a>). Plant them early.</p>
  <h2>Year-round food, no seeds (${yearRound.length})</h2><p class="muted">Field patches and greenhouses whose wiki pages list food output and no inputs.</p><div class="chips">${yearRound.map(bchip).join('')}</div>`;
  $('#pc').onchange = () => location.hash = '#/tool:planner/' + encodeURIComponent($('#pc').value);
}

const TOOLS = { 'tool:lookup': lookupPage, 'tool:tree': treePage, 'tool:planner': plannerPage };

// ---------- tier lists per building category ----------
const mats = b => Object.entries(b.cost || {}).reduce((s, [k, q]) => s + (k.startsWith('label:') ? 0 : (q || 0)), 0);
const costTxt = b => Object.entries(b.cost || {}).filter(([k, q]) => q && !k.startsWith('label:')).map(([k, q]) => `${q} ${iname(k)}`).join(' + ') || 'free';
const minInputs = b => b.rec && b.rec.length ? Math.min(...b.rec.map(r => r[0].reduce((s, x) => s + x[0], 0))) : null;
const METRICS = [  // [key, label, rule shown to the reader, value fn, higher is better, unit]
  ['h', 'Most people housed', 'settlers housed', b => b.h, true, ''],
  ['f', 'Warmest (least firewood)', 'warmth per fuel item (wiki: higher is more efficient)', b => b.f, true, ''],
  ['pp', 'Cheapest per person', 'build materials ÷ settlers housed', b => b.h ? mats(b) / b.h : null, false, ''],
  ['st', 'Biggest storage', 'storage capacity', b => b.st && !b.stt ? b.st : null, true, ''],
  ['spm', 'Most storage per material', 'storage ÷ build materials', b => b.st && !b.stt && mats(b) ? b.st / mats(b) : null, true, ''],
  ['wt', 'Fastest work cycle', 'work time per cycle (lower is faster)', b => b.wt, false, ''],
  ['inp', 'Fewest inputs', 'input items per recipe', b => { const m = minInputs(b); return m ? m : null; }, false, ''],
  ['w', 'Most workers', 'maximum workers', b => b.w, true, ''],
  ['r', 'Widest working radius', 'working radius in tiles', b => b.r, true, ''],
  ['hr', 'Widest happiness reach', 'happiness radius in tiles', b => b.hp && b.hp[0] !== 'Detraction' ? b.hp[1] : null, true, ''],
  ['mp', 'Lasts longest', 'total output before it runs out', b => b.mp, true, ''],
  ['m', 'Cheapest materials', 'total build materials', b => mats(b), false, ''],
  ['lab', 'Least labour', 'labour to build', b => b.lab, false, ''],
];
const TIER_ORDER = ['S', 'A', 'B', 'C'];
const SHORT = {"h": "houses", "f": "warmth", "pp": "materials/person", "st": "storage", "spm": "storage/material", "wt": "work time", "inp": "inputs", "w": "workers", "r": "radius", "hr": "happiness radius", "mp": "runs out after", "m": "materials", "lab": "labour"};
const tierOf = p => p < 0.1 ? 'S' : p < 0.3 ? 'A' : p < 0.6 ? 'B' : 'C';

function groupRows(g) {
  // collapse look-alike variants: same name and same numbers
  const seen = new Map();
  for (const [id, b] of Object.entries(TB)) {
    if (b.g !== g) continue;
    const key = b.n + '|' + METRICS.map(m => m[3](b)).join('|');
    if (seen.has(key)) seen.get(key).n++; else seen.set(key, { id, b, n: 1 });
  }
  return [...seen.values()];
}

function tierViews(rows) {
  const views = [];
  for (const [key, label, rule, fn, hi] of METRICS) {
    const vals = rows.map(r => fn(r.b)).filter(v => v !== null && v !== undefined && !Number.isNaN(v));
    if (vals.length < 3 || new Set(vals).size < 2) continue;
    if (key === 'm' || key === 'lab') { views.push({ key, label, rule, fn, hi }); continue; }
    views.push({ key, label, rule, fn, hi, core: true });
  }
  const core = views.filter(v => v.core && !(v.key === 'st' && views.some(x => x.key === 'spm')));
  if (core.length >= 2) views.unshift({ key: 'overall', label: 'Overall', rule: 'average of its position on: ' + core.map(v => v.label.toLowerCase()).join(', '), core });
  return views;
}

function rankView(rows, view) {
  const pos = new Map();
  const ranks = (v) => {
    const have = rows.filter(r => { const x = v.fn(r.b); return x !== null && x !== undefined && !Number.isNaN(x); });
    const vals = [...new Set(have.map(r => v.fn(r.b)))].sort((a, b) => v.hi ? b - a : a - b);
    const m = new Map();
    for (const r of have) m.set(r, vals.length > 1 ? vals.indexOf(v.fn(r.b)) / (vals.length - 1) : 0);
    return m;
  };
  if (view.key === 'overall') {
    const per = view.core.map(ranks);
    for (const r of rows) {
      const ps = per.map(m => m.get(r)).filter(x => x !== undefined);
      if (ps.length >= Math.max(2, view.core.length - (view.slack ?? view.core.length))) pos.set(r, ps.reduce((a, b) => a + b, 0) / ps.length);
    }
    // turn averages into an even spread so tiers mean the same in every view
    const sorted = [...pos.entries()].sort((a, b) => a[1] - b[1]);
    sorted.forEach(([r], i) => pos.set(r, sorted.length > 1 ? i / (sorted.length - 1) : 0));
  } else ranks(view).forEach((p, r) => pos.set(r, p));
  return [...pos.entries()].sort((a, b) => a[1] - b[1] || a[0].b.n.localeCompare(b[0].b.n));
}

function tierWidget(g, title) {
  const rows = groupRows(g);
  const views = tierViews(rows);
  if (!views.length || rows.length < 3) return;
  const box = document.createElement('section');
  box.className = 'tierbox';
  box.innerHTML = `<h2>Tier list <span class="muted">(${rows.length} buildings${rows.length !== Object.values(TB).filter(b => b.g === g).length ? ', look-alike variants grouped' : ''})</span></h2>
    <p class="muted">Pick what matters to you. Tiers show where a building ranks on that measure within ${esc(title || 'this category')}: <span class="tier t-s">S</span> top 10%, <span class="tier t-a">A</span> next 20%, <span class="tier t-b">B</span> next 30%, <span class="tier t-c">C</span> the rest. Only wiki numbers are used.</p>
    <div class="tabs" role="tablist">${views.map((v, i) => `<button role="tab" aria-selected="${i === 0}" data-v="${i}">${esc(v.label)}</button>`).join('')}</div>
    <div class="toolbar"><label class="chk"><input type="checkbox" id="tEarly"> Early game only <span class="muted">(buildable from starting Logs, Stone and Iron)</span></label><input type="search" id="tFind" placeholder="Filter by name" aria-label="Filter tier list by name"></div>
    <p class="rule" id="tRule"></p><div id="tList"></div>`;
  const h1 = main.querySelector('h1');
  (h1 ? h1.nextElementSibling ? h1.parentNode.insertBefore(box, h1.nextElementSibling) : h1.after(box) : main.prepend(box));
  let cur = 0, all = false;
  const draw = () => {
    const v = views[cur];
    box.querySelectorAll('[role=tab]').forEach((t, i) => t.setAttribute('aria-selected', i === cur));
    box.querySelector('#tRule').textContent = 'Ranked by ' + v.rule + '.';
    const early = box.querySelector('#tEarly').checked, find = box.querySelector('#tFind').value.toLowerCase();
    let ranked = rankView(rows, v).filter(([r]) => (!early || r.b.lv === 0) && (!find || r.b.n.toLowerCase().includes(find)));
    const total = ranked.length;
    if (!all) ranked = ranked.slice(0, 40);
    const val = r => {
      if (v.key === 'overall') return v.core.map(c => { const x = c.fn(r.b); return x === null || x === undefined ? '' : `${SHORT[c.key] || c.label} ${+x.toFixed(1)}`; }).filter(Boolean).join(' · ');
      const x = v.fn(r.b); return x === null || x === undefined ? '' : String(+x.toFixed(1));
    };
    box.querySelector('#tList').innerHTML = total ? `<div class="tw"><table class="tiertable"><tr><th>Tier</th><th>Building</th><th>${v.key === 'overall' ? 'Numbers' : esc(v.label)}</th><th>Build cost</th><th>Size</th></tr>` +
      ranked.map(([r, p]) => { const t = tierOf(p); return `<tr><td><span class="tier t-${t.toLowerCase()}">${t}</span></td><td>${bchip(r.id)}${r.n > 1 ? ` <span class="muted">×${r.n} variants</span>` : ''}${r.b.lv === 0 ? ' <span class="badge early">Early game</span>' : ''}${ruleBadge(r.b)}<div class="muted">${esc(r.b.mod || '')}</div></td><td>${esc(val(r))}</td><td>${esc(costTxt(r.b))}${r.b.lab ? ` <span class="muted">· ${r.b.lab} labour</span>` : ''}</td><td>${esc(r.b.sz || '–')}</td></tr>`; }).join('') + '</table></div>' +
      (total > 40 && !all ? `<button class="more" id="tMore">Show all ${total}</button>` : '') : '<p class="muted">No building matches.</p>';
    const more = box.querySelector('#tMore'); if (more) more.onclick = () => { all = true; draw(); };
    box.querySelectorAll('img.ic[data-i]').forEach(img => { const d = ICONS[img.dataset.i]; if (d) img.src = d; });
  };
  box.querySelector('.tabs').onclick = ev => { const b = ev.target.closest('[data-v]'); if (b) { cur = +b.dataset.v; all = false; draw(); } };
  box.querySelector('.tabs').onkeydown = ev => { if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') { cur = (cur + (ev.key === 'ArrowRight' ? 1 : views.length - 1)) % views.length; draw(); box.querySelector(`[data-v="${cur}"]`).focus(); } };
  box.querySelector('#tEarly').onchange = () => { all = false; draw(); };
  box.querySelector('#tFind').oninput = () => { all = false; draw(); };
  draw();
}

function tiersIndex() {
  const groups = [...new Set(Object.values(TB).map(b => b.g))].filter(g => P['buildings:' + g + ':start'] && groupRows(g).length >= 3 && tierViews(groupRows(g)).length)
    .sort((a, b) => P['buildings:' + a + ':start'][0].localeCompare(P['buildings:' + b + ':start'][0]));
  main.innerHTML = `<div class="crumb"><a href="#/guide:home">Home</a> › Tools</div><h1>Tier lists</h1>
  <p class="lead">Every building category has a tier list at the top of its page. Pick a category; each shows the current Overall S-tier picks.</p>
  <h2>Buildings</h2><div class="cards">${groups.map(g => { const rows = groupRows(g), v = tierViews(rows)[0], top = rankView(rows, v).filter(([, p]) => p < 0.1).slice(0, 8);
    return `<a href="#/buildings:${g}:start"><b>${esc(P['buildings:' + g + ':start'][0].replace(/ Buildings$/, ''))}</b><span class="muted">${rows.length} buildings · ${esc(v.label)}</span><br>${[...new Set(top.map(([r]) => r.b.n))].map(esc).join(', ')}</a>`; }).join('')}</div>
  <h2>Items and resources</h2><p class="muted">Item categories rank by yield, trade value, how early you can make them and how many buildings make them.</p>
  <div class="cards">${Object.keys(P).filter(k => /^wikipages:[^:]+:start$/.test(k) && Object.keys(TI).filter(i => i.startsWith(k.replace(':start', ':'))).length >= 3).sort((a, b) => P[a][0].localeCompare(P[b][0]))
    .map(k => `<a href="#/${k}"><b>${esc(P[k][0])}</b><span class="muted">${Object.keys(TI).filter(i => i.startsWith(k.replace(':start', ':'))).length} items</span></a>`).join('')}</div>`;
}
TOOLS['tool:tiers'] = tiersIndex;


// ---------- tier lists per item category ----------
const IMETRICS = [
  ['y', 'Highest yield', 'educated yield (wiki: uneducated/educated)', it => { const m = /(\d+)\s*\/\s*(\d+)/.exec(it.y || ''); return m ? +m[2] : null; }, true, 'yield'],
  ['v', 'Highest trade value', 'trade value', it => it.v, true, 'value'],
  ['lv', 'Easiest to get', 'progression step (Start = 0)', it => it.lv, false, 'step'],
  ['np', 'Most ways to make', 'number of buildings that make it', it => it.tiers.length || null, true, 'makers'],
  ['nu', 'Most useful for building', 'buildings that need it to be built', it => it.needs.length || null, true, 'needed by'],
];
function itemTierWidget(ns, title) {
  // the wiki files most fruit, grain and vegetables under Food, so also match on the item's category
  const label = (title || '').toLowerCase().replace(/s$/, '');
  const ids = Object.keys(TI).filter(k => k.startsWith('wikipages:' + ns + ':') || (label.length > 3 && (TI[k].c || '').toLowerCase().replace(/s$/, '') === label));
  if (ids.length < 3) return;
  const rows = ids.map(id => ({ id, b: TI[id], n: 1 }));
  const views = [];
  for (const [key, label, rule, fn, hi, short] of IMETRICS) {
    const vals = rows.map(r => fn(r.b)).filter(v => v !== null && v !== undefined);
    if (vals.length >= 3 && new Set(vals).size >= 2) views.push({ key, label, rule, fn, hi, short, core: key !== 'nu' });
  }
  const core = views.filter(v => v.core);
  if (core.length >= 2) views.unshift({ key: 'overall', label: 'Overall', slack: 1, rule: 'average of its position on: ' + core.map(v => v.label.toLowerCase()).join(', ') + ' (items missing more than one of these are left out)', core });
  if (!views.length) return;
  const box = document.createElement('section');
  box.className = 'tierbox';
  box.innerHTML = `<h2>Tier list <span class="muted">(${rows.length} items)</span></h2>
    <p class="muted">Tiers show where an item ranks on that measure within ${esc(title || 'this category')}: <span class="tier t-s">S</span> top 10%, <span class="tier t-a">A</span> next 20%, <span class="tier t-b">B</span> next 30%, <span class="tier t-c">C</span> the rest.</p>
    <div class="tabs" role="tablist">${views.map((v, i) => `<button role="tab" aria-selected="${i === 0}" data-v="${i}">${esc(v.label)}</button>`).join('')}</div>
    <div class="toolbar"><label class="chk"><input type="checkbox" id="tEarly"> Early game only <span class="muted">(makeable by progression step 1)</span></label><input type="search" id="tFind" placeholder="Filter by name" aria-label="Filter tier list by name"></div>
    <p class="rule" id="tRule"></p><div id="tList"></div>`;
  const h1 = main.querySelector('h1');
  h1 && h1.nextElementSibling ? h1.parentNode.insertBefore(box, h1.nextElementSibling) : main.prepend(box);
  let cur = 0, all = false;
  const draw = () => {
    const v = views[cur];
    box.querySelectorAll('[role=tab]').forEach((t2, i) => t2.setAttribute('aria-selected', i === cur));
    box.querySelector('#tRule').textContent = 'Ranked by ' + v.rule + '.';
    const early = box.querySelector('#tEarly').checked, find = box.querySelector('#tFind').value.toLowerCase();
    let ranked = rankView(rows, v).filter(([r]) => (!early || (r.b.lv !== null && r.b.lv <= 1)) && (!find || r.b.n.toLowerCase().includes(find)));
    const total = ranked.length;
    if (!all) ranked = ranked.slice(0, 40);
    const val = r => v.key === 'overall' ? v.core.map(c => { const x = c.fn(r.b); return x === null || x === undefined ? '' : `${c.short} ${x}`; }).filter(Boolean).join(' · ') : String(v.fn(r.b) ?? '');
    box.querySelector('#tList').innerHTML = total ? `<div class="tw"><table class="tiertable"><tr><th>Tier</th><th>Item</th><th>${v.key === 'overall' ? 'Numbers' : esc(v.label)}</th><th>Best way to get it</th></tr>` +
      ranked.map(([r, p]) => { const t2 = tierOf(p), best = r.b.tiers[0]; return `<tr><td><span class="tier t-${t2.toLowerCase()}">${t2}</span></td><td>${ichip(r.id)}</td><td>${esc(val(r))}</td><td>${best ? bchip(best[0]) + ` <span class="facts">${esc(best[3])}</span>` : (twins(r.id).length ? 'see ' + ichip(twins(r.id)[0]) : '<span class="muted">no source on the wiki</span>')}</td></tr>`; }).join('') + '</table></div>' +
      (total > 40 && !all ? `<button class="more" id="tMore">Show all ${total}</button>` : '') : '<p class="muted">No item matches.</p>';
    const more = box.querySelector('#tMore'); if (more) more.onclick = () => { all = true; draw(); };
  };
  box.querySelector('.tabs').onclick = ev => { const b = ev.target.closest('[data-v]'); if (b) { cur = +b.dataset.v; all = false; draw(); } };
  box.querySelector('.tabs').onkeydown = ev => { if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') { cur = (cur + (ev.key === 'ArrowRight' ? 1 : views.length - 1)) % views.length; draw(); box.querySelector(`[data-v="${cur}"]`).focus(); } };
  box.querySelector('#tEarly').onchange = () => { all = false; draw(); };
  box.querySelector('#tFind').oninput = () => { all = false; draw(); };
  draw();
}

// ---------- placement rules ----------
const SA = { nmt30fchunter: 'buildings:hunting:nmt30sahunter', nmt30fcforester: 'buildings:forester:nmt30saforester', nmt30fcgatherer: 'buildings:gathering:nmt30sagatherer',
  nmt30fcherbalist: 'buildings:herbalist:nmt30saherbalist', nmt30fcbarn: 'buildings:storage:nmt30sabarn', nmt30fcwoodcutter: 'buildings:fuel:nmt30sawoodcutter', nmt30fclumbermill: 'buildings:construction:nmt30salumbermill' };
const findB = re => Object.keys(TB).filter(k => re.test(TB[k].n)).slice(0, 4);
function rulesBox(id) {
  const b = TB[id], tail = id.split(':').pop();
  const rules = (b && b.rules) || [];
  const isDistrict = tail.startsWith('nmt30fc') && tail !== 'nmt30fcroad';
  if (!rules.length && !isDistrict) return '';
  const all = rules.join(' ');
  let need = '';
  if (isDistrict || /Forest Center/.test(all)) {
    need += `<p><b>You need first</b> (same toolbar: Themed Sets → NMT Forest Center Toolbar):</p><ol class="steps">
      <li>${bchip('buildings:gathering:nmtforestcenter')} <span class="muted">11 × 11, 24 Logs, working radius 40</span></li>
      <li>${bchip('buildings:roads:nmt30fcroad')} <span class="muted">“a special path required to designate districts”</span></li>
      <li>Then place this building inside the Forest Center's radius.</li></ol>
      <p class="muted">Steps read from the wiki pages; the wiki doesn't describe the in-game clicks.</p>`;
    if (SA[tail]) need += `<p><b>No Forest Center?</b> Use the stand-alone version instead, which can go anywhere: ${bchip(SA[tail])}</p>`;
  }
  if (/Forest Haven Platform/i.test(all)) need += `<p><b>Build the platform first:</b> ${findB(/Platform/).filter(k => /fh|haven/i.test(k)).map(bchip).join(' ') || 'see the Forest Haven set'}</p>`;
  if (/stone bridge/i.test(all)) need += `<p><b>Build the bridge first:</b> ${bchip('buildings:bridges:dsnormalstonebridgel')} ${bchip('buildings:bridges:dsstonebridgewalkways')}</p>`;
  if (/Dock platforms|as part of a dock/i.test(all)) need += `<p><b>Dock pieces:</b> ${bchip('buildings:wells:wooddock')}</p>`;
  if (/water|shoreline|jetty|platform/i.test(all)) need += `<p class="muted">More on building over water: <a href="#/guide:water">Life on the Water</a>.</p>`;
  return `<div class="rulebox" role="note"><b class="rb-h">Before you can build this</b><ul>${rules.map(r => `<li>“${esc(r)}”</li>`).join('') || '<li>“Works as a district within an NMT Forest Center compound.”</li>'}</ul>${need}</div>`;
}
const ruleBadge = b => b && b.rules ? ` <span class="badge rule" title="${esc(b.rules.join(' '))}">Placement rule</span>` : '';
