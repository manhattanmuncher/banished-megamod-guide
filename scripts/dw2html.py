"""Minimal DokuWiki -> HTML converter covering the markup worldofbanished.com uses."""
import re, html

SPRITE = re.compile(r'https?://sprites\.worldofbanished\.com/([^?|}\s]+)')


def norm_id(target, cur):
    t = target.strip().lower().replace(' ', '_')
    ns = cur.split(':')[:-1]
    if t.startswith('..:'):
        t = ':'.join(ns[:-1] + [t[3:]])
    elif t.startswith('.:'):
        t = ':'.join(ns + [t[2:]])
    elif t.startswith(':'):
        t = t[1:]
    elif ':' not in t:
        t = ':'.join(ns + [t])
    if t.endswith(':'):
        t += 'start'
    return t


class Conv:
    def __init__(self, pid, known_ids):
        self.pid = pid
        self.known = known_ids
        self.links = set()
        self.icons = set()
        self.alts = {}
        self.tags = []

    # ---------- inline ----------
    def link(self, m):
        inner = m.group(1)
        target, _, text = inner.partition('|')
        target = target.strip()
        if re.match(r'(https?:|mailto:)', target):
            label = self.inline(text) if text else html.escape(target)
            return f'<a href="{html.escape(target)}" target="_blank" rel="noopener" class="ext">{label}</a>'
        page, _, anchor = target.partition('#')
        tid = norm_id(page, self.pid) if page else self.pid
        self.links.add(tid)
        label = self.inline(text) if text.strip() else html.escape(text or tid.split(':')[-1].replace('_', ' '))
        cls = '' if tid in self.known else ' class="missing"'
        return f'<a href="#/{html.escape(tid)}"{cls}>{label}</a>'

    def image(self, m):
        inner = m.group(1).strip()
        src, _, alt = inner.partition('|')
        src = src.split('?')[0].strip()
        s = SPRITE.match(src)
        alt = html.escape(alt.strip())
        if s:
            name = s.group(1)
            self.icons.add(name)
            self.alts.setdefault(name, alt)
            return f'<img class="ic" data-i="{html.escape(name)}" alt="{alt}" title="{alt}">'
        if src.startswith('http'):
            return f'<img src="{html.escape(src)}" alt="{alt}" loading="lazy">'
        return ''

    def inline(self, s):
        out, i = [], 0
        # protect links and images first
        tokens = []

        def stash(h):
            tokens.append(h)
            return f'\x00{len(tokens) - 1}\x00'

        s = re.sub(r'\{\{tag>([^}]*)\}\}', lambda m: (self.tags.extend(m.group(1).split()), '')[1], s)
        s = re.sub(r'\{\{([^}]*)\}\}', lambda m: stash(self.image(m)), s)
        s = re.sub(r'\[\[(.+?)\]\]', lambda m: stash(self.link(m)), s)
        s = re.sub(r"''(.+?)''", lambda m: stash('<code>' + html.escape(m.group(1)) + '</code>'), s)
        s = re.sub(r'<abbr "([^"]*)">(.*?)</abbr>', lambda m: stash(f'<abbr title="{html.escape(m.group(1))}">{html.escape(m.group(2))}</abbr>'), s)
        s = re.sub(r'<wrap ([^>]*)>', lambda m: stash(f'<span class="w {html.escape(m.group(1))}">'), s)
        s = s.replace('</wrap>', stash('</span>'))
        s = html.escape(s, quote=False)
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        s = re.sub(r'(?<!:)//(.+?)(?<!:)//', r'<i>\1</i>', s)
        s = re.sub(r'__(.+?)__', r'<u>\1</u>', s)
        s = re.sub(r'\\\\(\s|$)', '<br>', s)
        s = re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m.group(1))], s)
        # nested stashes (labels containing images)
        s = re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m.group(1))], s)
        return s

    # ---------- table ----------
    def split_row(self, line):
        # split on | and ^ outside [[ ]] and {{ }}
        cells, cur, depth, seps = [], '', 0, []
        i = 0
        while i < len(line):
            two = line[i:i + 2]
            if two in ('[[', '{{'):
                depth += 1; cur += two; i += 2; continue
            if two in (']]', '}}') and depth:
                depth -= 1; cur += two; i += 2; continue
            c = line[i]
            if c in '|^' and depth == 0:
                cells.append(cur); seps.append(c); cur = ''
            else:
                cur += c
            i += 1
        cells.append(cur)
        # cells[0] is before first sep (empty), last is after final sep
        row = []
        for k in range(1, len(cells) - 1):
            row.append((seps[k - 1], cells[k]))
        return row

    def table(self, lines):
        out = ['<div class="tw"><table>']
        for ln in lines:
            row = self.split_row(ln.rstrip())
            out.append('<tr>')
            k = 0
            while k < len(row):
                sep, txt = row[k]
                span = 1
                while k + span < len(row) and row[k + span][1] == '':
                    span += 1
                tag = 'th' if sep == '^' else 'td'
                cs = f' colspan="{span}"' if span > 1 else ''
                al = ''
                if txt.startswith('  ') and txt.endswith('  '):
                    al = ' class="c"'
                elif txt.startswith('  '):
                    al = ' class="r"'
                out.append(f'<{tag}{cs}{al}>{self.inline(txt.strip())}</{tag}>')
                k += span
            out.append('</tr>')
        out.append('</table></div>')
        return ''.join(out)

    # ---------- blocks ----------
    def convert(self, text):
        text = text.lstrip('﻿')
        text = re.sub(r'~~[A-Z]+[^~]*~~', '', text)
        lines = text.split('\n')
        out, para, i = [], [], 0
        title = None

        def flush():
            if para:
                out.append('<p>' + self.inline(' '.join(para)) + '</p>')
                para.clear()

        while i < len(lines):
            ln = lines[i]
            st = ln.strip()
            h = re.match(r'^(={2,6})\s*(.+?)\s*={2,6}\s*$', st)
            if h:
                flush()
                lvl = 7 - len(h.group(1))
                txt = self.inline(h.group(2))
                if lvl == 1 and title is None:
                    title = re.sub('<[^>]+>', '', txt)
                out.append(f'<h{lvl}>{txt}</h{lvl}>')
                i += 1; continue
            if re.match(r'^-{4,}$', st):
                flush(); out.append('<hr>'); i += 1; continue
            m = re.match(r'^<WRAP\s*([^>]*)>(.*)$', st)
            if m:
                flush()
                rest = m.group(2)
                out.append(f'<div class="W {html.escape(m.group(1))}">')
                if rest.endswith('</WRAP>'):
                    out.append(self.inline(rest[:-7]) + '</div>')
                elif rest:
                    para.append(rest)
                i += 1; continue
            if st.startswith('</WRAP>'):
                flush(); out.append('</div>'); i += 1; continue
            if st.startswith(('^', '|')) and not ln.startswith('  '):
                flush()
                block = []
                while i < len(lines) and lines[i].strip().startswith(('^', '|')):
                    block.append(lines[i].strip()); i += 1
                out.append(self.table(block)); continue
            lm = re.match(r'^( {2,}|\t+)([*-])\s(.*)$', ln)
            if lm:
                flush()
                stack = []
                while i < len(lines):
                    lm = re.match(r'^( {2,}|\t+)([*-])\s(.*)$', lines[i])
                    if not lm:
                        break
                    depth = len(lm.group(1).replace('\t', '  ')) // 2
                    tag = 'ul' if lm.group(2) == '*' else 'ol'
                    while len(stack) < depth:
                        out.append(f'<{tag}>'); stack.append(tag)
                    while len(stack) > depth:
                        out.append(f'</{stack.pop()}>')
                    out.append('<li>' + self.inline(lm.group(3)) + '</li>')
                    i += 1
                while stack:
                    out.append(f'</{stack.pop()}>')
                continue
            if st.startswith('<code') or st.startswith('<file'):
                flush()
                end = '</code>' if st.startswith('<code') else '</file>'
                buf = []
                i += 1
                while i < len(lines) and end not in lines[i]:
                    buf.append(lines[i]); i += 1
                out.append('<pre>' + html.escape('\n'.join(buf)) + '</pre>')
                i += 1; continue
            if not st:
                flush(); i += 1; continue
            para.append(st)
            i += 1
        flush()
        return title, '\n'.join(out)
