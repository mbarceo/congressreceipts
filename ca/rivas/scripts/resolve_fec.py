"""Finds the member's FEC candidate and committee IDs and writes them into tracker.config.json.

Run this once, with your own FEC API key, before fetch_fec.py:
    FEC_API_KEY=your_key python3 -I scripts/resolve_fec.py
It searches House candidates by name, state and district, lists every match with its principal campaign
committee, and writes the IDs only when exactly one candidate matches. If several match (for example a
candidate ID per cycle), it prints them and stops so you can pick; nothing is guessed.
"""
import json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC, ROOT

KEY = os.environ.get(FEC["keyEnv"])
if not KEY: raise SystemExit(f"Set {FEC['keyEnv']} to your FEC API key first (the shared DEMO_KEY is too limited).")

def get(path, **params):
    params["api_key"] = KEY
    url = "https://api.open.fec.gov/v1" + path + "?" + urllib.parse.urlencode(params, doseq=True)
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"FEC API error {e.code} on {path}: {'rate limit or bad key' if e.code in (403, 429) else e.reason}")

last = M["name"].split()[-1]
res = get("/candidates/search/", q=last, state=M["state"], district=M["district"].zfill(2), office="H", per_page=50)["results"]
res = [r for r in res if last.lower() in r["name"].lower() and r["party"] in ("DEM", "DFL")] or res
rows = []
for r in res:
    cm = get(f"/candidate/{r['candidate_id']}/committees/", designation="P", per_page=20)["results"]
    time.sleep(0.5)
    rows.append((r, cm))
    print(f"{r['candidate_id']}  {r['name']}  {r['party']}  cycles {r.get('election_years')}")
    for c in cm: print(f"    principal committee {c['committee_id']}  {c['name']}  (cycles {c.get('cycles')})")

ok = [(r, cm) for r, cm in rows if len(cm) == 1]
if len(rows) == 1 and len(ok) == 1:
    r, cm = ok[0]
    CFG["fec"]["candidateId"], CFG["fec"]["committeeId"] = r["candidate_id"], cm[0]["committee_id"]
    json.dump(CFG, open(os.path.join(ROOT, "tracker.config.json"), "w"), indent=2, ensure_ascii=False)
    print(f"\nWrote candidateId={r['candidate_id']} committeeId={cm[0]['committee_id']} to tracker.config.json")
else:
    print("\nNot unique, so nothing was written. Set fec.candidateId and fec.committeeId in tracker.config.json by hand.")
    print("If she has one candidate ID but a different committee per cycle, tell me; fetch_fec.py then needs a per-cycle committee map.")
