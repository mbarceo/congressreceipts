"""Reads Track AIPAC's published "Israel Lobby Total" for the member and each peer in tracker.config.json.

Derek's page typed these numbers by hand. This reads them from each member's public page and records the URL
and read date, so the Money page can show them with a source. Track AIPAC says it compiles from fec.gov but
does not itemize; the page labels it as a third-party figure. Slug pattern: member-first-last-st-dd-party (House), member-first-last-st-sen-party (Senate).
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
    if "-" not in dist:                       # a senator: dist is just the state, e.g. "CA"
        return f"member-{n}-{dist.lower()}-sen-{party}"
    st, dd = dist.split("-"); return f"member-{n}-{st.lower()}-{int(dd):02d}-{party}"

def read(u):
    try:
        h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)
    m = re.search(r"Israel Lobby Total</dt><dd[^>]*>\s*\$([\d,]+)", h) or re.search(r"Israel Lobby Total[\s\S]{0,300}?\$([\d,]+)", h)
    return (int(m.group(1).replace(",", "")) if m else None), ("rejects AIPAC" if re.search(r"rejects?\s+AIPAC", h, re.I) else "")

# A senator's "dist" is the state ("CA"), which makes the -sen- slug. A peer or the member can carry "slug" (or
# member.trackaipacSlug) to override a slug Track AIPAC spells differently (nicknames, middle names).
me = {"name": M["name"], "dist": M["districtLabel"] if M.get("chamber", "house") != "senate" else M["state"], "group": "me",
      "party": PARTY.get(M.get("party"), "d")}
if M.get("trackaipacSlug"): me["slug"] = M["trackaipacSlug"]
people = [me] + [{"name": p["name"], "dist": p.get("dist") or p.get("state", ""), "group": p["group"],
                  "party": "r" if "(R)" in p["name"] else "i" if "(I)" in p["name"] else "d", **({"slug": p["slug"]} if p.get("slug") else {})}
                 for p in CFG["peers"]]
out, missing = [], []
for p in people:
    s = p.get("slug") or slug(p["name"], p["dist"], p["party"]); u = BASE + s
    total, flag = read(u); time.sleep(0.6)
    if total is None and not p.get("slug"):   # independents (Sanders, King) and party switchers: try the other party letters
        for alt in ("i", "d", "r"):
            if alt == p["party"]: continue
            u2 = BASE + slug(p["name"], p["dist"], alt); t2, f2 = read(u2); time.sleep(0.6)
            if t2 is not None: total, flag, u = t2, f2, u2; break
    if total is None: missing.append((p["name"], u, flag)); continue
    p.pop("slug", None)
    out.append({**p, "total": total, "url": u, "rejects": flag == "rejects AIPAC"})
    print(f'{p["name"]:<26} {p["dist"]:<6} ${total:>10,}')
if missing: print("\nNOT READ (set a 'slug' on the peer in tracker.config.json):", *missing, sep="\n  ")
json.dump({"read": datetime.date.today().isoformat(), "source": "Track AIPAC (trackaipac.com), Israel Lobby Total", "members": out},
          open(os.path.join(ROOT, "data/trackaipac.json"), "w"), indent=1)
