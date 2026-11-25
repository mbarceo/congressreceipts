"""Downloads the member's campaign finance data from the FEC API into data/fec/raw/.

Pulls cycle totals plus every contribution from PACs and other committees (Schedule A),
for every two-year cycle in fec.cycles (House: e.g. 2024, 2026; Senate: the term's election
cycle through the current one, e.g. 2022, 2024, 2026). Uses FEC_API_KEY from the environment,
else the public DEMO_KEY (as few as 10 calls an hour; a senator's election cycle alone can need
dozens of pages, so use a real key). Finished files are kept, so a re-run resumes.
Usage: python3 -I scripts/fetch_fec.py
"""
import datetime, json, os, time, urllib.parse, urllib.request
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC, need

ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
OUT = os.path.join(ROOT, "data/fec/raw")
os.makedirs(OUT, exist_ok=True)
KEY = os.environ.get(FEC["keyEnv"], "DEMO_KEY")
CMTE = need(FEC["committeeId"], "fec.committeeId")
CAND = need(FEC["candidateId"], "fec.candidateId")
API = "https://api.open.fec.gov/v1"

def get(path, **params):
    params["api_key"] = KEY
    url = f"{API}{path}?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise SystemExit("FEC rate limit hit. Wait an hour or set FEC_API_KEY, then re-run; finished files are kept.")
            # never re-raise the error object: its URL carries the API key
            if attempt == 2: raise SystemExit(f"FEC API error {e.code} on {path}; finished files are kept.") from None
            time.sleep(3)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2: raise SystemExit(f"Network error on {path}: {getattr(e, 'reason', e)}; finished files are kept.") from None
            time.sleep(3)

def save(name, data):
    json.dump(data, open(os.path.join(OUT, name), "w"))

# A cycle is named by its even end year and starts on Jan 1 of the year before; one that hasn't started has no data
future = [c for c in FEC["cycles"] if int(c) - 1 > datetime.date.today().year]
if future: raise SystemExit(f"fec.cycles lists {future}, which haven't started yet. Remove them from tracker.config.json.")

for cycle in tuple(FEC["cycles"]):
    f = f"totals_{cycle}.json"
    if not os.path.exists(os.path.join(OUT, f)):
        save(f, get(f"/committee/{CMTE}/totals/", cycle=cycle))
        print("saved", f)
    f = f"committee_contribs_{cycle}.json"
    if os.path.exists(os.path.join(OUT, f)):
        continue
    # Big races (Schiff 2023-24: ~250,000 rows, mostly earmarks) need more calls than the hourly key limit allows,
    # so progress is kept in a .partial file and a re-run continues from the last page instead of starting over.
    part = os.path.join(OUT, f + ".partial")
    rows, last = json.load(open(part)).values() if os.path.exists(part) else ([], {})
    pages = 0
    while True:
        try:
            d = get("/schedules/schedule_a/", committee_id=CMTE, two_year_transaction_period=cycle,
                    contributor_type="committee", per_page=100, sort="-contribution_receipt_date", **last)
        except SystemExit:
            json.dump({"rows": rows, "last": last}, open(part, "w")); print(f"progress kept: {len(rows)} rows"); raise
        rows += d["results"]; pages += 1
        if pages % 50 == 0: json.dump({"rows": rows, "last": d["pagination"].get("last_indexes") or {}}, open(part, "w"))
        li = d["pagination"].get("last_indexes")
        print(f"{cycle}: {len(rows)} of {d['pagination']['count']} committee contributions")
        if not li or not d["results"] or len(rows) >= d["pagination"]["count"]:
            break
        last = li
        time.sleep(1)
    save(f, rows)
    if os.path.exists(part): os.remove(part)
for cycle in tuple(FEC["cycles"]):
    f = f"by_employer_{cycle}.json"
    if not os.path.exists(os.path.join(OUT, f)):
        save(f, get("/schedules/schedule_a/by_employer/", committee_id=CMTE, cycle=cycle, per_page=100, sort="-total"))
        print("saved", f)
# Largest individual contributions (itemized, $200+), top rows by amount, for the top-donor list
for cycle in tuple(FEC["cycles"]):
    f = f"top_individuals_{cycle}.json"
    if os.path.exists(os.path.join(OUT, f)):
        continue
    rows, last = [], {}
    for page in range(4):
        d = get("/schedules/schedule_a/", committee_id=CMTE, two_year_transaction_period=cycle,
                is_individual="true", per_page=100, sort="-contribution_receipt_amount", **last)
        rows += d["results"]
        li = d["pagination"].get("last_indexes")
        if not li or not d["results"]:
            break
        last = li
        time.sleep(1)
    save(f, rows)
    print("saved", f, len(rows))
# Outside spending (independent expenditures) for or against the member, by committee: shows any UDP, HMP, DCCC, Fairshake money
for cycle in tuple(FEC["cycles"]):
    f = f"ie_by_candidate_{cycle}.json"
    if not os.path.exists(os.path.join(OUT, f)):
        save(f, get("/schedules/schedule_e/by_candidate/", candidate_id=CAND, cycle=cycle, per_page=100, sort="-total"))
        print("saved", f)
print("done")
