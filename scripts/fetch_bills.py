"""Downloads every bill the member sponsored or cosponsored, from the congress.gov API, into data/member_bills.json.

Use it to find bills behind a stance (e.g. police militarization, voting rights) instead of guessing from press releases.
Each row: kind (sponsored | cosponsored), congress, type, number, title, introducedDate, policyArea, latest action, and
a congress.gov URL. Claims made from it are then checked against govinfo BILLSTATUS by verify_bills.py (data/bills.json).
Needs a congress.gov key (free: https://api.congress.gov/sign-up/), kept in the Keychain and passed by the wrapper:
Usage: ./scripts/with_congress_key.sh python3 -I scripts/fetch_bills.py
"""
import json, os, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, ROOT

KEY = os.environ.get("CONGRESS_API_KEY") or sys.exit("No CONGRESS_API_KEY. Run through ./scripts/with_congress_key.sh")
API = "https://api.congress.gov/v3"
SLUG = {"HR": "house-bill", "S": "senate-bill", "HRES": "house-resolution", "SRES": "senate-resolution",
        "HJRES": "house-joint-resolution", "SJRES": "senate-joint-resolution",
        "HCONRES": "house-concurrent-resolution", "SCONRES": "senate-concurrent-resolution"}
ORD = lambda n: f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"

def get(path, **params):
    params.update(api_key=KEY, format="json")
    url = f"{API}{path}?" + urllib.parse.urlencode(params)
    for wait in (5, 30, 120, None):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
        except urllib.error.HTTPError as e:   # never print the error object: its URL carries the key
            if e.code not in (429, 500, 502, 503) or wait is None: sys.exit(f"congress.gov API error {e.code} on {path}")
        except (urllib.error.URLError, TimeoutError):
            if wait is None: sys.exit(f"Network error on {path}")
        time.sleep(wait)

import urllib.parse
rows = []
for kind in ("sponsored", "cosponsored"):
    off = 0
    while True:
        d = get(f"/member/{M['bioguide']}/{kind}-legislation", limit=250, offset=off)
        batch = d.get(f"{kind}Legislation", [])
        for b in batch:
            if not b.get("number"): continue          # amendments have no bill number here
            t = (b.get("type") or "").upper()
            rows.append({"kind": kind, "congress": b.get("congress"), "type": t, "number": b["number"],
                         "bill": f"{t.lower()}{b['number']}", "title": b.get("title") or "",
                         "introducedDate": b.get("introducedDate"), "policyArea": (b.get("policyArea") or {}).get("name"),
                         "latest": (b.get("latestAction") or {}).get("text"), "latestDate": (b.get("latestAction") or {}).get("actionDate"),
                         "url": f"https://www.congress.gov/bill/{ORD(b['congress'])}-congress/{SLUG.get(t, t.lower())}/{b['number']}"})
        print(f"{kind}: {len(batch)} at offset {off}")
        if len(batch) < 250: break
        off += 250; time.sleep(0.5)
json.dump(rows, open(os.path.join(ROOT, "data/member_bills.json"), "w"), indent=1, ensure_ascii=False)
print(len(rows), "bills:", sum(r["kind"] == "sponsored" for r in rows), "sponsored,", sum(r["kind"] == "cosponsored" for r in rows), "cosponsored")
