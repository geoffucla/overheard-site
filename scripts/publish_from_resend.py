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
    if not (b.get("name") or "").startswith("Overheard in the Bay"): continue
    if (b.get("segment_id") or SEGMENT) != SEGMENT: continue
    if not b.get("sent_at"): continue
    cands.append(b)
if not cands:
    print("no sent production broadcasts found"); sys.exit(0)

made = 0
for b in sorted(cands, key=lambda x: x["sent_at"], reverse=True)[:4]:
    s = b["sent_at"].replace("Z", "+00:00").replace(" ", "T")
    s = re.sub(r"([+-]\d\d)$", r"\1:00", s)
    iso = datetime.fromisoformat(s).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    out = os.path.join(ROOT, "output", f"SCUTTLEBUTT_{iso}.md")
    if os.path.exists(out):
        continue
    full = api("/broadcasts/" + b["id"])
    text = full.get("text") or ""
    if "Overheard in the Bay" not in text:
        print("broadcast", b["id"], "has no plain text; skipping"); continue
    tmp = "/tmp/email_" + iso + ".txt"
    open(tmp, "w").write(text)
    subprocess.run([sys.executable, os.path.join(ROOT, "template", "text_to_md.py"), tmp, out], check=True)
    md = open(out).read()
    heads = re.findall(r"^## (.+)$", md, re.M)
    if not md.startswith("# Overheard in the Bay") or len(heads) < 4 or heads[-1].strip() != "THREE THINGS TO BRING UP TODAY":
        os.remove(out)
        print("validation failed for", iso, heads[-1:] ); sys.exit(1)
    print("wrote", out); made += 1
print("new editions:", made)
