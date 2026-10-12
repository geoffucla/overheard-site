"""Rebuild the edition markdown from the sent email HTML (the inverse of md_to_email_html.py).
Usage: html_to_md.py email_html_path out_md_path   (env EDITION selects the edition name, default bay)
Used by scripts/publish_from_resend.py when the plain-text part of the broadcast is not in our own format."""
import sys, re, os, json, html as H
_ED = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'editions.json')))[os.environ.get('EDITION', 'bay')]
src, out = sys.argv[1:3]
S = re.S
doc = open(src).read()

def inl(t, strong=True):
    t = re.sub(r'<a\s[^>]*?href="([^"]*)"[^>]*>(.*?)</a\s*>', lambda m: '[' + re.sub(r'<[^>]+>', '', m.group(2)).strip() + '](' + H.unescape(m.group(1)) + ')', t, flags=S)
    if strong: t = re.sub(r'<strong[^>]*>(.*?)</strong\s*>', r'**\1**', t, flags=S)
    t = re.sub(r'<[^>]+>', '', t)
    return re.sub(r'\s+', ' ', H.unescape(t).replace('\xa0', ' ')).strip()

BAN = re.compile(r'<img\s[^>]*?/banners/(?!foot_|00_)\d\d_\w+\.png[^"]*"[^>]*?alt="([^"]*)"', S)
ms = list(BAN.finditer(doc))
if not ms: sys.exit('no column banners found in html')
end_all = doc.find('edition complete')
if end_all < 0: end_all = len(doc)
O = ["# " + _ED["name"], "", "Designed by hand, assembled by machine.", ""]
TOK = re.compile(
    r'<p\s+style="font:12px/1\.5[^>]*>(?P<link>.*?)</p\s*>'
    r'|<p\s+style="font:(?:17|15\.5|15)px/[^>]*>(?P<p>.*?)</p\s*>'
    r'|<div\s+style="font:(?:italic )?(?:15\.5|16)px/1\.\d+ [^"]*">(?P<d>.*?)</div\s*>'
    r'|<td\s+style="padding-left:14px;font:15\.5px/1\.55[^>]*>(?P<yc>.*?)</td\s*>', S)

def linkline(frag):
    m = re.match(r'\s*<em>(.*?)</em\s*>(.*)', frag, S)
    if not m: return '> ' + inl(frag)
    lab = inl(m.group(1)).rstrip(':').strip()
    return '> ' + lab + ': ' + inl(m.group(2))

for i, m in enumerate(ms):
    title = H.unescape(m.group(1)).strip()
    body = doc[m.end(): (ms[i + 1].start() if i + 1 < len(ms) else end_all)]
    k = body.find('padding:20px 20px 8px')
    if k >= 0: body = body[k:]
    body = re.split(r'<img\s[^>]*?/banners/foot_', body)[0]
    lines = []
    if title == 'THE LEDGER':
        for seg in re.split(r'<td\s+valign="top"\s+style="padding:16px 16px 14px', body)[1:]:
            seg = seg.split('>', 1)[1]
            cut = re.search(r'<div\s+style="font:bold 26px|</td\s*>', seg)
            lines.append(inl(seg[:cut.start()] if cut else seg, strong=False)); lines.append('')
        for lm in TOK.finditer(body):
            if lm.group('link') is not None: lines.append(linkline(lm.group('link'))); lines.append('')
    elif title == 'OPEN WEIGHTS':
        for seg in re.split(r'border-top:4px solid', body)[1:]:
            up = '&#9650;' in seg or '▲' in seg
            t = re.search(r'<strong[^>]*>(.*?)</strong\s*>', seg, S)
            b = re.search(r'<div\s+style="font:15px/1\.5[^>]*>(.*?)</div\s*>', seg, S)
            lines.append('**' + ('UP' if up else 'DOWN') + ': ' + inl(t.group(1)) + '** ' + (inl(b.group(1)) if b else '')); lines.append('')
            lm = re.search(r'<p\s+style="font:12px/1\.5[^>]*>(.*?)</p\s*>', seg, S)
            if lm: lines.append(linkline(lm.group(1))); lines.append('')
    else:
        n = 0
        for t in TOK.finditer(body):
            if t.group('link') is not None: lines.append(linkline(t.group('link'))); lines.append(''); continue
            if t.group('yc') is not None and title.startswith('THREE THINGS'):
                n += 1; lines.append(f"{n}. " + inl(t.group('yc'))); lines.append(''); continue
            frag = t.group('p') if t.group('p') is not None else (t.group('d') if t.group('d') is not None else t.group('yc'))
            lines.append(inl(frag)); lines.append('')
    O += ['## ' + title, ''] + lines
txt = '\n'.join(O)
while re.search(r'\n\d\. [^\n]*\n\n\d\. ', txt): txt = re.sub(r'(\n\d\. [^\n]*)\n\n(\d\. )', r'\1\n\2', txt)
O = txt.split('\n')
while O and O[-1] == '': O.pop()
open(out, 'w').write('\n'.join(O) + '\n')
