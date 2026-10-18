#!/usr/bin/env python3
"""Build the Terms Undisclosed main site (www.termsundisclosed.com): a home page that explains the project and links to
every edition, plus a general About page. Reads template/editions.json. No edition content lives here.
Usage: python3 build_home.py [repo_root]    Writes <repo_root>/site-home/"""
import os, re, sys, html, json, shutil, datetime
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'site-home')
CFG = json.load(open(os.path.join(ROOT, 'template', 'editions.json')))
BASE = 'https://www.termsundisclosed.com'
E = html.escape
# reuse the edition site's stylesheet so the home page always matches it
_bs = open(os.path.join(ROOT, 'template', 'build_site.py'), encoding='utf-8').read()
CSS = _bs[_bs.index("CSS = '''") + 9:_bs.index("'''\nJS = ")]
exec(_bs[_bs.index("def parse(path):"):_bs.index("COLS = {")])                      # parse()
exec(_bs[_bs.index("SEARCH_JS = r'''"):_bs.index("def title_html")])                # SEARCH_JS, plain, index_entries, search_box
CSS += '''
.ed{margin:0 0 22px;padding:0 0 18px;border-bottom:1px solid #E5E0D8}.ed:last-child{border-bottom:0;margin-bottom:6px}
.ed h3.edn{font:bold 22px Georgia,serif;color:#1F2933;margin:0 0 6px}.ed p{font-size:16px;margin:0 0 12px}
.ed .btn{display:inline-block;background:#B3261E;color:#fff;text-decoration:none;font:bold 13px Arial,sans-serif;letter-spacing:.06em;padding:10px 16px;border-radius:3px;margin:0 8px 6px 0}
.ed .soon{display:inline-block;border:1px solid #B34D12;color:#B34D12;font:bold 12px Arial,sans-serif;letter-spacing:.12em;padding:8px 12px;border-radius:3px}
.ed a.alt{font:bold 13px Arial,sans-serif;color:#1D4ED8}
'''
live = [(k, v) for k, v in CFG.items() if v.get('status') == 'live']
nums = len(CFG)
def card(key, fam, inner, title):
    return (f'<section class="col {fam}"><img class="bar" src="banners/bar_{key}.png?v=2026101801" alt="{E(title)}" width="1200" height="220">'
            f'<div class="cbody bw">{inner}</div></section>')
what = ('<p>Terms Undisclosed is a short weekday briefing on what is actually going on in business and tech, written for people who need to be '
        'clued in and quotable before their first meeting. It covers funding, deals, regulation, rumors and the occasional absurdity, and it is written to be '
        'read in five minutes and repeated at dinner.</p>'
        '<p>It comes in regional editions, called blends, each with its own local stories and its own coffee. Every edition is written by software, with one human on the loop.</p>'
        '<p class="more" style="font:14px/1.5 Arial,sans-serif"><a href="about/">How this is made</a></p>')
eds = ''
for k, v in CFG.items():
    if v.get('status') == 'live':
        acts = f'<a class="btn" href="{v["site"]}/">Read today&rsquo;s edition</a><a class="alt" href="{v["site"]}/subscribe/">Subscribe</a>'
    else:
        acts = '<span class="soon">COMING SOON</span>'
    eds += f'<div class="ed"><h3 class="edn">{E(v["short"])}</h3><p>{E(v["blurb"])}</p><p>{acts}</p></div>'
body_cards = card('15_what', 'news', what, 'What this is') + card('16_blends', 'wit', eds, 'Pick your blend')
def dl(rel, left='THE BLENDS'):
    links = f'<a href="{rel or "./"}">Home</a><a href="{rel}about/">About</a><a href="{rel}search/">Search</a>' + ''.join(f'<a href="{v["site"]}/">{E(v["short"])}</a>' for k, v in live)
    return f'<div class="dl"><span class="dd">{left}</span><nav class="dn">{links}</nav></div>'
def page(title, body, rel='', desc='', canon='/', after=''):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{BASE}{canon}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:image" content="{BASE}/banner.png"><link rel="stylesheet" href="{rel}style.css"><link rel="icon" href="{rel}favicon.svg" type="image/svg+xml"><link rel="icon" href="{rel}favicon-32x32.png" sizes="32x32" type="image/png"><link rel="shortcut icon" href="{rel}favicon.ico"><link rel="apple-touch-icon" href="{rel}apple-touch-icon.png"></head><body><div class="wrap">
<picture><source media="(max-width:520px)" srcset="{rel}banners/00_masthead_m.png?v=2026101801"><img class="mastn" src="{rel}banners/00_masthead.png?v=2026101801" alt="Terms Undisclosed. News, deals, rumors and unsolicited opinions" width="1200" height="362"></picture>
{dl(rel)}{body}{after}
<footer>Informed, opinionated, occasionally wrong. Verify before repeating at dinner.<br><span class="copy">Designed by hand, written by Claude.</span><br><span class="copy">All views expressed are strictly AI generated and are not those of any human.</span><br><span class="copy">No humans in the loop. One human on the loop.</span><br><span class="copy">&copy; {datetime.date.today().year} Humans Not Included Media, publisher of Terms Undisclosed. All rights reserved.</span></footer></div></body></html>'''
def w(path, content):
    p = os.path.join(OUT, path); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'w', encoding='utf-8').write(content)
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
bsrc = os.path.join(ROOT, 'template', 'banners')
shutil.copytree(bsrc, os.path.join(OUT, 'banners'))
hsrc = os.path.join(ROOT, 'template', 'editions', 'home')
for _f in os.listdir(hsrc):
    shutil.copy(os.path.join(hsrc, _f), os.path.join(OUT, 'banner.png' if _f == 'banner.png' else os.path.join('banners', _f)))
isrc = os.path.join(ROOT, 'template', 'icons')
if os.path.isdir(isrc):
    for _f in os.listdir(isrc): shutil.copy(os.path.join(isrc, _f), os.path.join(OUT, _f))
w('style.css', CSS)
DESC = 'Terms Undisclosed: a short weekday briefing on business and tech, in regional editions, written by AI.'
w('index.html', page('Terms Undisclosed', body_cards, desc=DESC))
ENTRIES = []
for k, v in CFG.items():
    od = os.path.join(ROOT, v.get('output_dir', 'output'))
    if v.get('status') != 'live' or not os.path.isdir(od): continue
    for f in sorted(os.listdir(od)):
        if re.fullmatch(r'SCUTTLEBUTT_\d{4}-\d{2}-\d{2}\.md', f) and f[12:22] >= v['min_date']:
            ENTRIES += index_entries(f[12:22], parse(os.path.join(od, f)), v['site'] + '/', v['short'])
ENTRIES.sort(key=lambda e: e['d'], reverse=True)
w('search.json', json.dumps(ENTRIES, ensure_ascii=False, separators=(',', ':')))
chips = '<div class="sfc"><button type="button" class="on" data-ed="">All</button>' + ''.join(f'<button type="button" data-ed="{E(v["short"])}">{E(v["short"])}</button>' for k, v in live) + '</div>'
w('search/index.html', page('Search — Terms Undisclosed', search_box('../search.json', '', chips), rel='../', desc='Search every edition of Terms Undisclosed.', canon='/search/', after=SEARCH_JS))
about = ('<h1 class="page">About</h1><p>Terms Undisclosed is a family of short weekday briefings on what is actually going on in business and tech, one edition per region. '
 'Each covers who is up, who is down, what people are whispering and what the press is getting wrong. Each is written to be read in five minutes and repeated at dinner, where it will be credited to you.</p>'
 '<p>The tone is dry on purpose. The takes are meant to be correct, and the jokes are there to help them along. Stories are chosen for water-cooler interest, and the number of press releases a story generated counts against it.</p>'
 '<p><strong>How this is made.</strong> Every weekday morning, software searches the news, picks the stories, writes the takes, attaches the links and sends the email, all before most readers have located their coffee. The daily run is fully automated, so in the technical sense there are no humans in the loop. The software in question is Claude, an AI model made by Anthropic, which these briefings occasionally cover, so read those items with whatever discount you think fair.</p>'
 '<p>There is, however, a human on the loop, which is a different thing and a much less restful job. The curator conceived the whole enterprise and designed every part of it, from the sections and the voice to the rules on what counts as a story, how dry the jokes should be, and when an old story earns an update. The curator reads each edition every morning, in the manner of a nervous parent at a school play.</p>'
 '<p>The software is told to link only to pages it actually read, and it still gets things wrong now and then. That is what the footer means by occasionally wrong, and it is why every item carries its sources. Think of them as receipts.</p>'
 '<p>Readers are welcome to forward the email and to quote short excerpts with a link back to the original. Please do not republish whole editions without permission. The software has no feelings about this, but the publisher does.</p>'
 '<p>Designed by hand, written by Claude. Questions, corrections and tips are welcome at <a href="mailto:human@termsundisclosed.com">human@termsundisclosed.com</a>, where an actual human will read them.</p>')
w('about/index.html', page('About — Terms Undisclosed', about, rel='../', desc=DESC, canon='/about/'))
w('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
w('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{BASE}{u}</loc></url>' for u in ('/', '/about/', '/search/')) + '</urlset>')
print('built home ->', OUT)
