#!/usr/bin/env python3
"""Build the static Overheard in the Bay site from output/SCUTTLEBUTT_*.md.
Usage: python3 build_site.py [AI_folder]   (default: parent of this file's folder)
Writes AI_folder/site/ (index.html, archive/, editions/, about/, unsubscribe/, banner.png, style.css)."""
import os, re, sys, html, shutil, datetime
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'site'); SRC = os.path.join(ROOT, 'output')
# ---- settings: change these in one place ----
SITE = 'Overheard in the Bay'
TAGLINE = 'Tech news and gossip, best served hot'
META_DESC = 'A dry-wit Bay Area tech briefing, written by AI every weekday morning.'
BYLINE = 'As Heard by Always-On Listening'   # public byline; email keeps 'Designed for human consumption by Geoff Allen'
BASE = 'https://bay.overheardnews.com'
MIN_DATE = '2026-10-02'   # earlier editions predate the current voice and are not published
SUBSCRIBE_ACTION = 'https://api.overheardnews.com/subscribe'
# ---------------------------------------------
E = html.escape
NUM = re.compile(r'^\d+\.\s*')
def inline(s):
    s = E(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2" rel="noopener">\1</a>', s)
    return s
def parse(path):
    secs, cur = [], None
    for ln in open(path, encoding='utf-8').read().splitlines():
        s = ln.strip()
        if not s or s.startswith('# ') or s.startswith(('Curated by','Designed for human consumption')): continue
        if s.startswith('## '):
            cur = [s[3:].strip(), []]; secs.append(cur); continue
        if cur is not None: cur[1].append(s)
    return secs
COLS = {
 'THE LEAD': ('01_lead', 'news'), 'THE LEDGER': ('02_ledger', 'money'), 'OPEN WEIGHTS': ('03_weights', 'money'),
 'HUMAN, YOUR LOOP IS CALLING': ('04_human', 'machine'), 'THE SCUTTLEBUTT': ('05_scuttle', 'wit'), 'LOCAL DESK': ('06_local', 'news'),
 'CORRECTIONS AND UPDATES': ('07_corr', 'news'), 'AUTOMATIC REPLIES': ('08_auto', 'machine'), 'SYNTHETIC REFLECTIONS': ('09_synth', 'machine'),
 'EMPATHY AS A SERVICE': ('10_empathy', 'machine'), 'YOUR CALL IS IMPORTANT TO US': ('11_call', 'wit'),
 'UNSUITABLE FOR GENERAL RELEASE': ('12_unsuit', 'wit'), 'THREE THINGS TO BRING UP TODAY': ('13_three', 'wit')}
SCALES = [1e8, 2.5e8, 5e8, 1e9, 2.5e9, 5e9, 1e10, 2.5e10, 5e10, 1e11]
def amount(line):
    best = None
    for m in re.finditer(r'\$\s?([\d][\d,]*(?:\.\d+)?)\s?(billion|million|thousand|bn|B|M|K)\b', line):
        tail = line[m.end():m.end() + 24].lower()
        mult = {'billion': 1e9, 'bn': 1e9, 'b': 1e9, 'million': 1e6, 'm': 1e6, 'thousand': 1e3, 'k': 1e3}[m.group(2).lower()]
        val = float(m.group(1).replace(',', '')) * mult
        isval = bool(re.match(r'\s*(pre-money|post-money|valuation|valued|market cap)', tail))
        if best is None or (best[1] and not isval): best = (val, isval)
        if not isval: break
    return best[0] if best else None
def money(v):
    if v >= 1e9: return '$' + f'{v/1e9:.2f}'.rstrip('0').rstrip('.') + 'B'
    if v >= 1e6: return '$' + f'{v/1e6:.1f}'.rstrip('0').rstrip('.') + 'M'
    return f'${v/1e3:.0f}K'
def render(secs, rel=''):
    o = []
    for title, lines in secs:
        info = COLS.get(title); fam = info[1] if info else 'news'
        slug = re.sub(r'[^a-z]+', '-', title.lower()).strip('-')
        o.append(f'<section class="col {fam} {slug}">')
        if info: o.append(f'<img class="cb" src="{rel}banners/{info[0]}.png" alt="{E(title)}" width="1200" height="220">')
        else: o.append(f'<h2>{E(title)}</h2>')
        o.append('<div class="cbody">')
        if lines and lines[0].startswith('~ '):
            lines = lines[1:]  # tagline lives in the banner
        def more(l):
            lab, _, rest = l[2:].partition(':')
            return f'<p class="more"><em>{E(lab.strip())}:</em> {inline(rest.strip())}</p>'
        body = [l for l in lines if l.strip()]
        txt = [l for l in body if not l.startswith('> ')]
        links = [more(l) for l in body if l.startswith('> ')]
        if title in ('THE ONE THING', 'THE LEAD'):
            for l in body:
                if l.startswith('> '): o.append(more(l))
                else: o.append(f'<p class="lead"><span class="dc">{E(l[0])}</span>{inline(l[1:])}</p>')
        elif title == 'THE LEDGER':
            amts = [amount(l) for l in txt]; top = max([x for x in amts if x] + [5e8]); scale = next(x for x in SCALES if x >= top)
            o.append('<div class="ledger">')
            for l, a in zip(txt, amts):
                right = ''
                if a:
                    pct = max(4, min(100, round(a / scale * 100)))
                    right = f'<div class="amt">{money(a)}</div><div class="bar"><i style="width:{pct}%"></i></div><div class="sc">of {money(scale)} scale</div>'
                o.append(f'<div class="row"><div class="who">{inline(l)}</div><div class="side">{right}</div></div>')
            o.append('</div>'); o.extend(links)
        elif title.startswith('WHO') or title == 'OPEN WEIGHTS':
            card = None
            for l in body:
                if l.startswith('> '):
                    if card is not None: card += more(l)
                    else: o.append(more(l))
                    continue
                m = re.match(r'\*\*(UP|DOWN):\s*(.+?)\*\*\s*(.*)', l)
                if m:
                    if card is not None: o.append(card + '</div>')
                    cls, lab = ('up', '&#9650; UP') if m.group(1) == 'UP' else ('down', '&#9660; DOWN')
                    card = f'<div class="owcard {cls}"><div class="hd"><span class="tag {cls}">{lab}</span> <strong>{inline(m.group(2))}</strong></div><p>{inline(m.group(3))}</p>'
                else:
                    o.append(f'<p>{inline(l)}</p>')
            if card is not None: o.append(card + '</div>')
        elif title.startswith('THREE'):
            o.append('<ol class="three">' + ''.join('<li>' + inline(NUM.sub('', l)) + '</li>' for l in txt) + '</ol>'); o.extend(links)
        elif title == 'HUMAN, YOUR LOOP IS CALLING':
            o.append('<div class="darkpanel">' + ''.join(f'<p>{inline(l)}</p>' for l in txt) + ''.join(links) + '</div>')
        elif title == 'THE SCUTTLEBUTT':
            o.append('<div class="scut"><span class="stamp">UNCONFIRMED</span>' + ''.join(f'<p>{inline(l)}</p>' for l in txt) + '</div>'); o.extend(links)
        elif title == 'CORRECTIONS AND UPDATES':
            o.append('<div class="erratum"><span class="lab">FOR THE RECORD</span>' + ''.join(f'<p>{inline(l)}</p>' for l in txt) + '</div>'); o.extend(links)
        elif title == 'AUTOMATIC REPLIES':
            o.append('<div class="autoreply"><div class="status"><strong>STATUS</strong> Responding automatically</div><div class="ar">' + ''.join(f'<p>{inline(l)}</p>' for l in txt) + '</div></div>'); o.extend(links)
        elif title == 'EMPATHY AS A SERVICE':
            o.append('<div class="note"><div class="orn">&mdash; &#9825; &mdash;</div>' + ''.join(f'<p>{inline(l)}</p>' for l in txt) + '</div>'); o.extend(links)
        elif title == 'YOUR CALL IS IMPORTANT TO US':
            for l in body: o.append(more(l) if l.startswith('> ') else f'<p class="callrule">{inline(l)}</p>')
        elif title == 'UNSUITABLE FOR GENERAL RELEASE':
            o.append('<div class="boxed">' + ''.join(f'<p>{inline(l)}</p>' for l in txt) + '</div>'); o.extend(links)
        elif title == 'SOURCES':
            ul = False
            for l in lines:
                if l.startswith('- '):
                    if not ul: o.append('<ul class="src">'); ul = True
                    o.append(f'<li>{inline(l[2:])}</li>')
                else:
                    if ul: o.append('</ul>'); ul = False
                    o.append(f'<h3>{inline(l.strip("*"))}</h3>')
            if ul: o.append('</ul>')
        else:
            for l in body: o.append(more(l) if l.startswith('> ') else f'<p>{inline(l)}</p>')
        o.append('</div></section>')
    return '\n'.join(o)
def long_date(iso):
    d = datetime.date.fromisoformat(iso); return d.strftime('%A, %B ') + str(d.day) + d.strftime(', %Y')
def first_para(secs):
    for t, ls in secs:
        if t in ('THE ONE THING', 'THE LEAD') and ls:
            p = re.sub(r'\*\*|\[([^\]]+)\]\([^)]+\)', lambda m: m.group(1) or '', ls[0]); return p[:200]
    return META_DESC
CSS = '''
:root{--ink:#1F2933;--mute:#6B7280;--red:#B3261E;--paper:#E9E3D6;--sheet:#F6F1E7;--card:#fff;--rule:#E5E0D8;--wash:#F7F3EE}
@media(prefers-color-scheme:dark){:root{--ink:#E8E6E3;--mute:#9AA3AD;--red:#FF8A80;--paper:#0E1013;--sheet:#1A1D21;--card:#22262B;--rule:#2C3036;--wash:#22262B}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.6 Georgia,'Times New Roman',serif}
a{color:var(--red)}.wrap{max-width:700px;margin:0 auto;padding:0 16px 40px;background:var(--sheet);border-left:1px solid #CFC7B5;border-right:1px solid #CFC7B5;box-shadow:0 0 24px rgba(0,0,0,.08);min-height:100vh}@media(prefers-color-scheme:dark){.wrap{border-color:#2C3036}}
.banner{display:block;width:100%;height:auto;margin:16px 0 6px;border-radius:2px}
header.mast{text-align:center;border-top:3px solid var(--ink);border-bottom:1px solid var(--ink);padding:10px 0 14px}
.title{font-weight:bold;letter-spacing:.16em;font-size:26px;line-height:1.2;margin:0}.title .cap{font-size:38px}
.title a{color:inherit;text-decoration:none}.tag-line{font-style:italic;font-size:15px;margin-top:8px}.tag-line .by{color:var(--red)}
nav{font:12px Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase;text-align:center;margin:14px 0 0}nav a{color:var(--mute);text-decoration:none;margin:0 10px}nav a:hover{color:var(--red)}
.date{font:11px Arial,sans-serif;letter-spacing:.1em;color:var(--mute);text-align:center;margin:22px 0 0;text-transform:uppercase}
h1.page{font-size:30px;margin:28px 0 8px}h2{font:bold 12px Arial,sans-serif;letter-spacing:.16em;color:var(--red);border-bottom:2px solid var(--red);padding-bottom:4px;margin:34px 0 14px}
h3{font:bold 12px Arial,sans-serif;color:var(--mute);margin:14px 0 2px}p{margin:0 0 14px}
p.stand{font:italic 14px/1.4 Arial,sans-serif;color:var(--mute);margin:-6px 0 12px}p.lead{background:var(--wash);border-left:5px solid var(--red);padding:14px 16px;font-size:19px}
.tag{font:bold 12px Arial,sans-serif;letter-spacing:.08em;padding:2px 7px;border-radius:2px}.tag.up{color:#1B5E20;background:#C8E6C9}.tag.down{color:#B3261E;background:#F8D0CC}
ol{padding-left:22px}li{margin-bottom:8px}p.more{font:14px/1.5 Arial,sans-serif;color:var(--mute);margin:-8px 0 20px}p.more a{color:var(--mute)}ul.src{font:13px/1.5 Arial,sans-serif;padding-left:18px}ul.src li{margin:3px 0}
.sub{background:var(--card);border:1px solid var(--rule);padding:18px;margin:30px 0;border-radius:4px}.sub h2{margin-top:0}
.sub form{display:flex;gap:8px;flex-wrap:wrap}.sub input[type=email]{flex:1 1 220px;padding:11px;font:16px Arial,sans-serif;border:1px solid var(--mute);border-radius:3px;background:var(--paper);color:var(--ink)}
.sub button{padding:11px 18px;font:bold 14px Arial,sans-serif;background:var(--red);color:#fff;border:0;border-radius:3px;cursor:pointer}.sub small{display:block;font:12px Arial,sans-serif;color:var(--mute);margin-top:8px;width:100%}
.hp{position:absolute;left:-9999px}#msg{font:14px Arial,sans-serif;margin-top:8px;width:100%}
ul.arch{list-style:none;padding:0}ul.arch li{border-bottom:1px solid var(--rule);padding:12px 0;margin:0}ul.arch .d{font:bold 12px Arial,sans-serif;letter-spacing:.08em;color:var(--mute);text-transform:uppercase}ul.arch a{font-size:19px;text-decoration:none}ul.arch p{font-size:15px;color:var(--mute);margin:4px 0 0}
p.sub-note{font:14px/1.5 Arial,sans-serif;color:var(--mute);margin:0 0 12px}footer .copy{font:12px Arial,sans-serif;font-style:normal;display:inline-block;margin-top:6px}footer{font:italic 13px Georgia,serif;color:var(--mute);text-align:center;border-top:1px solid var(--mute);padding-top:10px;margin-top:40px}

.col{margin:0 0 4px;--c:#24344D;--t:#E4E9F1}.col.money{--c:#1F6B4F;--t:#E1EFE8}.col.machine{--c:#5B3FA0;--t:#ECE6F6}.col.wit{--c:#B34D12;--t:#F8E8DB}
.cb{display:block;width:calc(100% + 32px);max-width:none;height:auto;margin:34px -16px 0}.cbody{padding-top:16px}
.col h2{margin-top:34px}
p.lead{background:none;border:0;padding:0;font-size:19px}p.lead .dc{float:left;font:bold 56px/46px Georgia,serif;color:var(--c);padding:4px 10px 0 0}@media(prefers-color-scheme:dark){p.lead .dc{color:#8FA6CC}}
.ledger{background:var(--t);border-top:3px solid var(--c);margin:0 0 18px;color:#1B2430}.ledger .row{display:flex;gap:14px;align-items:center;padding:14px;border-bottom:1px solid rgba(0,0,0,.08)}
.ledger .who{flex:1;font-size:16px;line-height:1.45}.ledger .side{width:130px;text-align:right}.ledger .amt{font:bold 28px/1 Georgia,serif;color:var(--c)}
.ledger .bar{height:8px;background:rgba(0,0,0,.12);margin-top:8px}.ledger .bar i{display:block;height:8px;background:var(--c)}.ledger .sc{font:10px Arial,sans-serif;color:#4C7A68;margin-top:3px}
.ledger a{color:#1D4ED8}@media(max-width:480px){.ledger .row{flex-direction:column;align-items:flex-start}.ledger .side{width:100%;text-align:left}}
.owcard{background:var(--card);border:1px solid var(--rule);border-top:4px solid var(--c);padding:14px 16px;margin:0 0 14px}.owcard.down{border-top-color:#B3261E}
.owcard .hd{margin:0 0 8px;font-size:18px}.owcard p{margin:0 0 8px;font-size:16px}.owcard p.more{margin:8px 0 0}
.tag.up{background:#1F6B4F;color:#fff}.tag.down{background:#B3261E;color:#fff}
.darkpanel{background:#2A1F4A;color:#F1ECFA;padding:20px 22px 8px;margin:0 0 16px}.darkpanel a{color:#CFC2F2}.darkpanel p.more{color:#B9ABE0}.darkpanel p.more a{color:#CFC2F2}
.scut{background:var(--t);border:2px dashed var(--c);padding:16px 18px 6px;margin:0 0 12px;color:#1B2430;font-style:italic}.scut a{color:#1D4ED8}
.stamp{display:inline-block;border:2px solid var(--c);color:var(--c);font:bold 11px Arial,sans-serif;letter-spacing:3px;padding:3px 8px;margin:0 0 10px;font-style:normal}
.erratum{border-top:4px double var(--c);border-bottom:4px double var(--c);padding:14px 4px 4px;margin:0 0 16px}.erratum .lab{display:block;font:bold 11px Arial,sans-serif;letter-spacing:2px;color:var(--c);margin:0 0 6px}
.autoreply{border:1px solid #BFB1E3;background:#fff;margin:0 0 16px;color:#1B2430}.autoreply .status{background:var(--t);border-bottom:1px solid #BFB1E3;padding:8px 14px;font:11px/1.6 Arial,sans-serif;color:#4A3487;letter-spacing:.5px}.autoreply .ar{padding:16px 18px 2px}.autoreply a{color:#1D4ED8}
.note{background:var(--t);border:1px solid #CFC2F2;padding:20px 26px 8px;margin:0 0 18px;font-style:italic;color:#1B2430}.note .orn{text-align:center;color:var(--c);letter-spacing:6px;margin:0 0 10px;font-style:normal}.note a{color:#1D4ED8}
.callrule{border-left:4px solid var(--c);padding-left:14px}
.boxed{border:1px solid var(--ink);background:var(--card);padding:16px 18px 4px;margin:0 0 16px}
ol.three{list-style:none;padding:0;counter-reset:n}ol.three li{counter-increment:n;display:flex;gap:14px;align-items:center;margin:0 0 14px}ol.three li:before{content:counter(n);flex:none;width:46px;height:46px;border-radius:23px;background:var(--c);color:#fff;font:bold 24px/46px Georgia,serif;text-align:center}
.masthead{display:block;width:calc(100% + 32px);max-width:none;height:auto;margin:0 -16px}.byline{text-align:center;font:italic 14px Georgia,serif;margin:10px 0 0}.byline .by{color:var(--red)}
.col p a{word-break:break-word}
'''
JS = '''<script>
document.querySelectorAll('form.subscribe').forEach(function(f){f.addEventListener('submit',function(e){e.preventDefault();
var m=f.querySelector('.msg');m.textContent='Subscribing...';
fetch(f.action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:f.email.value,website:f.website.value})})
.then(function(r){return r.json().catch(function(){return{}}).then(function(j){m.textContent=r.ok?(j.message||'Check your inbox to confirm.'):(j.error||'Something went wrong. Please try again.')})})
.catch(function(){m.textContent='Could not reach the server. Please try again later.'})})});
</script>'''
def title_html():
    words = SITE.upper().split(); return ' '.join(f'<span class="cap">{w[0]}</span>{w[1:]}' for w in words)
def subscribe_box():
    return f'''<div class="sub"><h2>GET IT IN YOUR INBOX</h2><p class="sub-note">Written every weekday morning by software, with one human on the loop and a firm policy of staying out of it.</p><form class="subscribe" action="{SUBSCRIBE_ACTION}" method="post"><input type="email" name="email" required placeholder="you@example.com" aria-label="Email address"><input class="hp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true"><button type="submit">Subscribe</button><span class="msg" id="msg" aria-live="polite"></span><small>One email each weekday morning. Unsubscribe any time, with a quick confirmation.</small></form></div>'''
def page(title, body, rel='', desc=META_DESC, canon='/'):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{BASE}{canon}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:image" content="{BASE}/banners/00_masthead.png"><link rel="stylesheet" href="{rel}style.css"></head><body><div class="wrap">
<img class="masthead" src="{rel}banners/00_masthead.png" alt="Overheard in the Bay. {E(TAGLINE)}" width="1200" height="380">
<p class="byline">{E(BYLINE)}</p>
<nav><a href="{rel or './'}">Today</a><a href="{rel}archive/">Archive</a><a href="{rel}about/">About</a><a href="{rel}unsubscribe/">Unsubscribe</a></nav>
{body}
<footer>Informed, opinionated, occasionally wrong. Verify before repeating at dinner.<br><span class="copy">Written by Claude, an AI model made by Anthropic. All views expressed are strictly AI generated and are not the views of any human on, in, or around the loop, including the one who designed this for human consumption.</span><br><span class="copy">No humans in the loop. One human on the loop.</span><br><span class="copy">&copy; {datetime.date.today().year} Humans Not Included Media, publisher of Overheard in the Bay. All rights reserved.</span></footer></div>{JS}</body></html>'''
def w(path, content):
    p = os.path.join(OUT, path); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'w', encoding='utf-8').write(content)
files = sorted(f for f in os.listdir(SRC) if re.fullmatch(r'SCUTTLEBUTT_\d{4}-\d{2}-\d{2}\.md', f) and f[12:22] >= MIN_DATE)
eds = [(f[12:22], parse(os.path.join(SRC, f))) for f in files]
if not eds: sys.exit('no editions found in ' + SRC)
eds.sort(reverse=True)
os.makedirs(OUT, exist_ok=True)
shutil.copy(os.path.join(ROOT, 'template', 'banner.png'), os.path.join(OUT, 'banner.png'))
bsrc = os.path.join(ROOT, 'template', 'banners')
if os.path.isdir(bsrc):
    shutil.copytree(bsrc, os.path.join(OUT, 'banners'), dirs_exist_ok=True)
w('style.css', CSS)
for iso, secs in eds:
    w(f'editions/{iso}/index.html', page(f'{SITE} — {long_date(iso)}', f'<p class="date">{long_date(iso)}</p>' + render(secs, '../../') + subscribe_box(), rel='../../', desc=first_para(secs), canon=f'/editions/{iso}/'))
latest_iso, latest = eds[0]
w('index.html', page(SITE, f'<p class="date">{long_date(latest_iso)} &middot; <a href="editions/{latest_iso}/">permalink</a></p>' + render(latest) + subscribe_box(), desc=first_para(latest)))
items = ''.join(f'<li><span class="d">{long_date(i)}</span><br><a href="../editions/{i}/">{E(SITE)}, {long_date(i)}</a><p>{E(first_para(s))}</p></li>' for i, s in eds)
w('archive/index.html', page(f'Archive — {SITE}', f'<h1 class="page">Archive</h1><ul class="arch">{items}</ul>' + subscribe_box(), rel='../', canon='/archive/'))
w('about/index.html', page(f'About — {SITE}', f'''<h1 class="page">About</h1><p>{E(SITE)} is a short weekday briefing on what is actually going on in Bay Area tech. It covers who is up, who is down, what people are whispering and what the press is getting wrong. It is written to be read in five minutes and repeated at dinner, where it will be credited to you.</p><p>The tone is dry on purpose. The takes are meant to be correct, and the jokes are there to help them along. Stories are chosen for water-cooler interest, and the number of press releases a story generated counts against it.</p><p><strong>How this is made.</strong> Every weekday morning, software searches the news, picks the stories, writes the takes, attaches the links and sends the email, all before most readers have located their coffee. The daily run is fully automated, so in the technical sense there are no humans in the loop. The software in question is Claude, an AI model made by Anthropic, which this briefing occasionally covers, so read those items with whatever discount you think fair.</p><p>There is, however, a human on the loop, which is a different thing and a much less restful job. The curator conceived the whole enterprise and designed every part of it, from the sections and the voice to the rules on what counts as a story, how dry the jokes should be, and when an old story earns an update. The curator reads each edition every morning, in the manner of a nervous parent at a school play.</p><p>The software is told to link only to pages it actually read, and it still gets things wrong now and then. That is what the footer means by occasionally wrong, and it is why every item carries its sources. Think of them as receipts.</p><p>Readers are welcome to forward the email and to quote short excerpts with a link back to the original. Please do not republish whole editions without permission. The software has no feelings about this, but the publisher does.</p><p>As Heard by Always-On Listening. Questions, corrections and tips are welcome at <a href="mailto:human@overheardnews.com">human@overheardnews.com</a>, where an actual human will read them.</p>''' + subscribe_box(), rel='../', canon='/about/'))
w('unsubscribe/index.html', page(f'Unsubscribe — {SITE}', '''<h1 class="page">Unsubscribe</h1><p>Every email has an <strong>Unsubscribe</strong> link in the footer. Click it, confirm in the follow-up email, and you are off the list. You will not be asked to log in, and nobody will ask why you are leaving, though the software may privately wonder.</p><p>If that link has gone missing, write to <a href="mailto:human@overheardnews.com?subject=Unsubscribe">human@overheardnews.com</a> with the subject &ldquo;Unsubscribe&rdquo; and you will be removed by hand, by an actual human, who will try not to take it personally.</p>''', rel='../', canon='/unsubscribe/'))
w('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
urls = ['/', '/archive/', '/about/', '/unsubscribe/'] + [f'/editions/{i}/' for i, _ in eds]
w('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{BASE}{u}</loc></url>' for u in urls) + '</urlset>')
print('built', len(eds), 'editions ->', OUT)
