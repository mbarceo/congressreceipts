"""Reads Track AIPAC's published "Israel Lobby Total" for the member and each peer in tracker.config.json.

Derek's page typed these numbers by hand. This reads them from each member's public page and records the URL
and read date, so the Money page can show them with a source. Track AIPAC says it compiles from fec.gov but
does not itemize; the page labels it as a third-party figure. Slug pattern: member-first-last-st-dd-party.
Usage: python3 -I scripts/fetch_trackaipac.py
"""
import datetime, json, os, re, sys, time, unicodedata, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, ROOT

BASE = "https://www.trackaipac.com/tracker/people/"
PARTY = {"Democrat": "d", "Republican": "r"}

def slug(name, dist, party):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\s*\((r|d)\)", "", n); n = re.sub(r"[^a-z ]", "", n.replace("-", " ")).strip().replace(" ", "-")
    st, dd = dist.split("-"); return f"member-{n}-{st.lower()}-{int(dd):02d}-{party}"

def read(u):
    try:
        h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)
    m = re.search(r"Israel Lobby Total</dt><dd[^>]*>\s*\$([\d,]+)", h) or re.search(r"Israel Lobby Total[\s\S]{0,300}?\$([\d,]+)", h)
    return (int(m.group(1).replace(",", "")) if m else None), ("rejects AIPAC" if re.search(r"rejects?\s+AIPAC", h, re.I) else "")

people = [{"name": M["name"], "dist": M["districtLabel"], "group": "me", "party": "d"}] + \
         [{"name": p["name"], "dist": p["dist"], "group": p["group"], "party": "r" if "(R)" in p["name"] else "d"} for p in CFG["peers"]]
out, missing = [], []
for p in people:
    s = p.get("slug") or slug(p["name"], p["dist"], p["party"]); u = BASE + s
    total, flag = read(u); time.sleep(0.6)
    if total is None: missing.append((p["name"], u, flag)); continue
    out.append({**p, "total": total, "url": u, "rejects": flag == "rejects AIPAC"})
    print(f'{p["name"]:<26} {p["dist"]:<6} ${total:>10,}')
if missing: print("\nNOT READ (set a 'slug' on the peer in tracker.config.json):", *missing, sep="\n  ")
json.dump({"read": datetime.date.today().isoformat(), "source": "Track AIPAC (trackaipac.com), Israel Lobby Total", "members": out},
          open(os.path.join(ROOT, "data/trackaipac.json"), "w"), indent=1)
