"""Publish the newest sent production edition from Resend into output/.
Runs in GitHub Actions. Needs env RESEND_API_KEY. Writes output/SCUTTLEBUTT_YYYY-MM-DD.md
if it does not exist yet. Exits 0 when there is nothing new, 1 on a real failure."""
import os, re, sys, json, subprocess, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

SEGMENT = "995bb00b-9636-4dc4-9f94-68c0dcf928ed"
KEY = os.environ["RESEND_API_KEY"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def api(path):
    req = urllib.request.Request("https://api.resend.com" + path,
        headers={"Authorization": "Bearer " + KEY, "User-Agent": "overheard-publisher/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

lst = api("/broadcasts").get("data", [])
cands = []
for b in lst:
    if b.get("status") != "sent": continue
    if not (b.get("name") or "").startswith(("Overheard in the Bay", "Terms Undisclosed")): continue
    if "Texas Blend" in (b.get("name") or ""): continue
    if (b.get("segment_id") or SEGMENT) != SEGMENT: continue
    if not b.get("sent_at"): continue
    cands.append(b)
if not cands:
    print("no sent production broadcasts found"); sys.exit(0)

made = 0
seen = set()
def iso_of(b):
    s = b["sent_at"].replace("Z", "+00:00").replace(" ", "T")
    s = re.sub(r"([+-]\d\d)$", r"\1:00", s)
    return datetime.fromisoformat(s).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")

for b in sorted(cands, key=lambda x: x["sent_at"], reverse=True)[:6]:
    iso = iso_of(b)
    if iso in seen:
        continue          # newest broadcast for this date already handled
    seen.add(iso)
    out = os.path.join(ROOT, "output", f"SCUTTLEBUTT_{iso}.md")
    updated = "(updated)" in (b.get("name") or "").lower()
    if os.path.exists(out) and not updated:
        continue
    full = api("/broadcasts/" + b["id"])
    text = full.get("text") or ""
    if not any(k in text for k in ("Overheard in the Bay", "Terms Undisclosed")):
        print("broadcast", b["id"], "has no plain text; skipping"); continue
    tmp = "/tmp/email_" + iso + ".txt"
    open(tmp, "w").write(text)
    cand = out + ".new"
    subprocess.run([sys.executable, os.path.join(ROOT, "template", "text_to_md.py"), tmp, cand], check=True)
    md = open(cand).read()
    heads = re.findall(r"^## (.+)$", md, re.M)
    if not md.startswith(("# Overheard in the Bay", "# Terms Undisclosed")) or len(heads) < 4 or heads[-1].strip() != "THREE THINGS TO BRING UP TODAY":
        os.remove(cand)
        print("validation failed for", iso, heads[-1:]); sys.exit(1)
    if os.path.exists(out) and open(out).read() == md:
        os.remove(cand); continue     # nothing changed
    os.replace(cand, out)
    print("wrote", out, "(updated)" if updated else ""); made += 1
print("new editions:", made)
