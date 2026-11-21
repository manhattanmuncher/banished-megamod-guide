"""Download every icon the wiki references and repair the ones the sprite server lacks."""
import os, re, json, time, zlib, base64, difflib, subprocess, urllib.parse, html

SPRITES = 'https://sprites.worldofbanished.com/'
FANDOM_API = 'https://banished.fandom.com/api.php?action=query&prop=imageinfo&iiprop=url&format=json&titles='

# Vanilla icons missing from the sprite server -> same game art on banished.fandom.com
FANDOM = {
    'buildcutteryard.png': 'Woodcutter.png',
    'buildfield.png': 'Crops.png',
    'buildfishermansdock.png': 'Fishing.png',
    'buildforesterlodge.png': 'Forester.png',
    'buildgatherer.png': 'Gather.png',
    'buildhunterlodge.png': 'Hunt.png',
    'buildtoolmaker.png': 'Blacksmiths.png',
    'toolbarfood.png': 'Food.png',
    'toolbarresource.png': 'Resources.png',
    'buildwoodhouse.png': 'Woodhouse.png',
    'buildstonehouse.png': 'Stonehouse.png',
    'buildboardinghouse.png': 'Boardinghouse.png',
    'buildstoragebarn.png': 'Storagebarn.png',
    'buildstockpile.png': 'Stockpile.png',
    'buildmarket.png': 'Market.png',
    'buildtradingpost.png': 'Trade.png',
    'buildtownhall.png': 'Townhall.png',
    'buildschool.png': 'School.png',
    'buildschoolhouse.png': 'School.png',
    'buildchapel.png': 'Chapels.png',
    'buildhospital.png': 'Hospitals.png',
    'buildwell.png': 'Wells.png',
    'buildcemetery.png': 'Cemeteries.png',
    'buildquarry.png': 'Quarries.png',
    'buildmine.png': 'Mines.png',
    'buildironmine.png': 'Mines.png',
    'buildtailor.png': 'Tailors.png',
    'buildorchard.png': 'Orchards.png',
    'buildpasture.png': 'Pastures.png',
    'buildtunnel.png': 'Tunnel.png',
    'buildwoodbridge.png': 'Woodbridge.png',
    'buildroad.png': 'Dirtroad.png',
    'buildstoneroad.png': 'Stoneroad.png',
    'toolbarhousing.png': 'Housing.png',
    'toolbarstorage.png': 'Storage.png',
    'toolbartownservices.png': 'Services.png',
    'toolbarservices.png': 'Services.png',
    'toolbarroads.png': 'Roads.png',
    'buildbridge.png': 'Woodbridge.png',
    'buildquarry.png': 'Quarries.png',
    'buildtradingpost.png': 'Trade.png',
    'dstunnelsmenu.png': 'Tunnel.png',
    'CitizenCold.png': 'Cold.png',
    'CitizenDisease.png': 'Sickness.png',
    'CitizenFood.png': 'Hungry.png',
    'CitizenHome.png': 'Homeless.png',
    'CitizenJob.png': 'Jobless.png',
    'CitizenTool.png': 'Toolless.png',
    'buildhouse.png': 'Woodhouse.png',
    'buildstorageyard.png': 'Stockpile.png',
}

# Broken sprite names whose art exists on the sprite server under another name
WIKI_ALIAS = {
    'buildamoryhouseback.png': 'buildamoryhouse.png',
    'stonebridgemenu.png': 'buildstonebridge.png',
    'dsstonebridgemenu.png': 'buildstonebridge.png',
    'buildnmt30stonebridge.png': 'buildstonebridge.png',
    'decorative.png': 'toolbardecorative.png',
    'toolbarservice.png': 'ccservices.png',
    'toolbartransport.png': 'cctransport.png',
    'professionbeekeeper.png': 'beekeeper.png',
    'dsmarketstraverns.png': 'dsmarkets.png',
    'tiereditems.png': 'toolbarmodular.png',
    'seedalmondtree.png': 'seedalmond.png',
    'builddecojapanesecemeterygate.png': 'buildjapanesecemeterygate.png',
}

BADGE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect x="1" y="1" width="30" height="30" rx="6" '
         'fill="#8a6a3f" stroke="#5b4426" stroke-width="2"/><text x="16" y="22" font-family="Georgia,serif" '
         'font-size="17" font-weight="bold" fill="#fff6e3" text-anchor="middle">{}</text></svg>')


def curl(url, out):
    r = subprocess.run(['curl', '-sfL', '-m', '20', '-A', 'Mozilla/5.0', '-o', out, url])
    time.sleep(0.2)
    return r.returncode == 0 and os.path.exists(out) and open(out, 'rb').read(4) == b'\x89PNG'


def fandom(name, out):
    r = subprocess.run(['curl', '-sf', '-m', '20', '-A', 'Mozilla/5.0', FANDOM_API + urllib.parse.quote('File:' + name)],
                       capture_output=True)
    try:
        page = next(iter(json.loads(r.stdout)['query']['pages'].values()))
        return curl(page['imageinfo'][0]['url'] + '&format=original', out)
    except Exception:
        return False


KEEP = {b'IHDR', b'PLTE', b'tRNS', b'IDAT', b'IEND'}


def png_slim(data):
    """drop metadata chunks (colour profiles, text) and recompress pixels; image stays identical"""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return data
    i, chunks, idat = 8, [], b''
    while i + 8 <= len(data):
        n = int.from_bytes(data[i:i + 4], 'big')
        t, body = data[i + 4:i + 8], data[i + 8:i + 8 + n]
        if t == b'IDAT':
            idat += body
        elif t in KEEP:
            chunks.append((t, body))
        i += 12 + n
    try:
        idat = zlib.compress(zlib.decompress(idat), 9)
    except zlib.error:
        return data
    out = [data[:8]]
    for t, body in chunks:
        if t == b'IEND':
            out.append(chunk(b'IDAT', idat))
        out.append(chunk(t, body))
    return b''.join(out)


def chunk(t, body):
    return len(body).to_bytes(4, 'big') + t + body + (zlib.crc32(t + body) & 0xffffffff).to_bytes(4, 'big')


def uri(path):
    return 'data:image/png;base64,' + base64.b64encode(png_slim(open(path, 'rb').read())).decode()


def resolve_icons(needed, icon_dir, alts):
    os.makedirs(icon_dir, exist_ok=True)
    miss_marker = os.path.join(icon_dir, '_missing.json')
    missing = set(json.load(open(miss_marker))) if os.path.exists(miss_marker) else set()
    icons, broken = {}, []
    for name in sorted(needed):
        p = os.path.join(icon_dir, name.replace('/', '_'))
        if os.path.exists(p) or (name not in missing and curl(SPRITES + name, p)):
            icons[name] = uri(p)
        else:
            missing.add(name)
            if os.path.exists(p):
                os.remove(p)
            broken.append(name)
    json.dump(sorted(missing), open(miss_marker, 'w'))

    fixed = {'fandom': [], 'similar': [], 'badge': []}
    good = sorted(icons)
    for name in broken:
        fp = os.path.join(icon_dir, '_fandom_' + name)
        if name in FANDOM and (os.path.exists(fp) or fandom(FANDOM[name], fp)):
            icons[name] = uri(fp)
            fixed['fandom'].append(name)
            continue
        lp = os.path.join(icon_dir, name.lower())
        if name != name.lower() and (os.path.exists(lp) or curl(SPRITES + name.lower(), lp)):
            icons[name] = uri(lp)
            fixed['similar'].append(f'{name} -> {name.lower()}')
            continue
        label = (alts.get(name) or '').strip().lower()
        same = [k for k in good if label and (alts.get(k) or '').strip().lower() == label]
        if same:
            icons[name] = icons[same[0]]
            fixed['similar'].append(f'{name} -> {same[0]} (same label "{alts.get(name)}")')
            continue
        ap = os.path.join(icon_dir, WIKI_ALIAS.get(name, '_none'))
        if name in WIKI_ALIAS and (os.path.exists(ap) or curl(SPRITES + WIKI_ALIAS[name], ap)):
            icons[name] = uri(ap)
            fixed['similar'].append(f'{name} -> {WIKI_ALIAS[name]}')
            continue
        # e.g. buildfoo.png -> foo.png, professionfoo.png -> foo.png
        base = re.sub(r'^(build|profession|toolbar)', '', name)
        cand = [base] if base in icons else difflib.get_close_matches(base, good, n=1, cutoff=0.85)
        if cand:
            icons[name] = icons[cand[0]]
            fixed['similar'].append(f'{name} -> {cand[0]}')
            continue
        letter = html.escape((alts.get(name) or name).strip()[:1].upper() or '?')
        icons[name] = 'data:image/svg+xml;base64,' + base64.b64encode(BADGE.format(letter).encode()).decode()
        fixed['badge'].append(f'{name} ({alts.get(name, "")})')

    report = [f'icons: {len(needed)} used, {len(broken)} broken on the wiki',
              f'  replaced with original game art (Fandom): {len(fixed["fandom"])}',
              f'  replaced with matching wiki sprite: {len(fixed["similar"])}'] + \
             [f'    {x}' for x in fixed['similar']] + \
             [f'  no art found anywhere, lettered badge: {len(fixed["badge"])}'] + [f'    {x}' for x in fixed['badge']]
    return icons, '\n'.join(report)


if __name__ == '__main__':
    # self-check: slimmed PNG decodes to the same pixel stream
    import sys, glob
    total = slim = 0
    for f in glob.glob(os.path.join(sys.argv[1], '*.png')):
        a = open(f, 'rb').read()
        b = png_slim(a)
        total += len(a); slim += len(b)
        def pix(d):
            i, out = 8, b''
            while i + 8 <= len(d):
                n = int.from_bytes(d[i:i + 4], 'big')
                if d[i + 4:i + 8] == b'IDAT':
                    out += d[i + 8:i + 8 + n]
                i += 12 + n
            return zlib.decompress(out) if out else b''
        if a[:4] == b'\x89PNG':
            assert pix(a) == pix(b), f
    print(f'{total / 1e6:.1f} MB -> {slim / 1e6:.1f} MB, pixels identical')
