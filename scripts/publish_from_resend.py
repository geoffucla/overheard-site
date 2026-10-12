"""Publish the newest sent production edition(s) from Resend into each edition's output folder.
Runs in GitHub Actions. Needs env RESEND_API_KEY. Reads template/editions.json and, for every edition that has a
production segment, writes SCUTTLEBUTT_YYYY-MM-DD.md into that edition's output_dir if it does not exist yet (or when the
newest broadcast for the date is marked "(updated)"). Broadcasts are matched on the edition's full name AND its production
segment, so a Texas send can never publish to the Bay site or the reverse. Exits 0 when there is nothing new, 1 on a real failure.
Optional env EDITION limits the run to one edition."""
import os, re, sys, json, subprocess, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

KEY = os.environ["RESEND_API_KEY"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "template", "editions.json")))
LEGACY = {"bay": ("Overheard in the Bay",)}   # old broadcast names still accepted for the Bay edition

def api(path):
    req = urllib.request.Request("https://api.resend.com" + path,
        headers={"Authorization": "Bearer " + KEY, "User-Agent": "overheard-publisher/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def iso_of(b):
    s = b["sent_at"].replace("Z", "+00:00").replace(" ", "T")
    s = re.sub(r"([+-]\d\d)$", r"\1:00", s)
    return datetime.fromisoformat(s).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")

lst = api("/broadcasts").get("data", [])
only = os.environ.get("EDITION")
total = 0
for key, ed in CFG.items():
    if only and key != only: continue
    seg = ed.get("production_segment") or ""
    if not seg:
        print(key, ": no production segment yet, skipping"); continue
    prefixes = (ed["name"],) + LEGACY.get(key, ())
    cands = []
    for b in lst:
        if b.get("status") != "sent": continue
        if not (b.get("name") or "").startswith(prefixes): continue
        if (b.get("segment_id") or seg) != seg: continue
        if not b.get("sent_at"): continue
        cands.append(b)
    if not cands:
        print(key, ": no sent production broadcasts found"); continue
    outdir = os.path.join(ROOT, ed.get("output_dir", "output")); os.makedirs(outdir, exist_ok=True)
    seen = set(); made = 0
    for b in sorted(cands, key=lambda x: x["sent_at"], reverse=True)[:6]:
        iso = iso_of(b)
        if iso in seen:
            continue          # newest broadcast for this date already handled
        seen.add(iso)
        out = os.path.join(outdir, f"SCUTTLEBUTT_{iso}.md")
        updated = "(updated)" in (b.get("name") or "").lower()
        if os.path.exists(out) and not updated and len(seen) > 2:
            continue     # older dates are left alone; the two newest are rebuilt so converter fixes self-heal
        full = api("/broadcasts/" + b["id"])
        text = full.get("text") or ""
        htm = full.get("html") or ""
        def valid(md):
            heads = re.findall(r"^## (.+)$", md, re.M)
            ok = md.startswith(("# Overheard in the Bay", "# Terms Undisclosed")) and len(heads) >= 4 and heads[-1].strip() == "THREE THINGS TO BRING UP TODAY"
            return ok, heads[-1:]
        cand = out + ".new"; md = None; why = ""
        print(key, iso, "text chars:", len(text), "html chars:", len(htm), "has ==== rule:", "=" * 20 in text)
        env = {**os.environ, "EDITION": key}
        # 1) our own plain-text format (has a ==== rule under the header); 2) fall back to parsing the HTML
        if "=" * 20 in text and any(k in text for k in ("Overheard in the Bay", "Terms Undisclosed")):
            tmp = "/tmp/email_" + key + "_" + iso + ".txt"
            open(tmp, "w", encoding="utf-8").write(text)
            r = subprocess.run([sys.executable, os.path.join(ROOT, "template", "text_to_md.py"), tmp, cand], env=env)
            if r.returncode == 0 and os.path.exists(cand):
                m1 = open(cand, encoding="utf-8").read(); ok, why = valid(m1)
                if ok: md = m1
        if md is None and htm:
            tmp = "/tmp/email_" + key + "_" + iso + ".html"
            open(tmp, "w", encoding="utf-8").write(htm)
            r = subprocess.run([sys.executable, os.path.join(ROOT, "template", "html_to_md.py"), tmp, cand], env=env)
            print(key, iso, "html_to_md exit code:", r.returncode)
            if r.returncode == 0 and os.path.exists(cand):
                m2 = open(cand, encoding="utf-8").read(); ok, why = valid(m2)
                if ok: md = m2; print(key, iso, ": built from the email HTML")
        if md is None:
            if os.path.exists(cand): os.remove(cand)
            print("validation failed for", key, iso, why); sys.exit(1)
        if os.path.exists(cand): os.remove(cand)
        if os.path.exists(out) and open(out, encoding="utf-8").read() == md:
            continue     # nothing changed
        open(out, "w", encoding="utf-8").write(md)
        print("wrote", out, "(updated)" if updated else ""); made += 1
    print(key, "new editions:", made); total += made
print("total new editions:", total)
