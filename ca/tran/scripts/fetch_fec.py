"""Downloads Derek Tran's campaign finance data from the FEC API into data/fec/raw/.

Pulls cycle totals plus every contribution from PACs and other committees (Schedule A),
for the 2024 and 2026 cycles. Uses FEC_API_KEY from the environment, else the public
DEMO_KEY (limited to a few dozen calls an hour). Usage: python3 -I scripts/fetch_fec.py
"""
import json, os, time, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data/fec/raw")
os.makedirs(OUT, exist_ok=True)
KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")
CMTE = "C00851790"
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
            if attempt == 2: raise
            time.sleep(3)

def save(name, data):
    json.dump(data, open(os.path.join(OUT, name), "w"))

for cycle in (2024, 2026):
    f = f"totals_{cycle}.json"
    if not os.path.exists(os.path.join(OUT, f)):
        save(f, get(f"/committee/{CMTE}/totals/", cycle=cycle))
        print("saved", f)
    f = f"committee_contribs_{cycle}.json"
    if os.path.exists(os.path.join(OUT, f)):
        continue
    rows, last = [], {}
    while True:
        d = get("/schedules/schedule_a/", committee_id=CMTE, two_year_transaction_period=cycle,
                contributor_type="committee", per_page=100, sort="-contribution_receipt_date", **last)
        rows += d["results"]
        li = d["pagination"].get("last_indexes")
        print(f"{cycle}: {len(rows)} of {d['pagination']['count']} committee contributions")
        if not li or not d["results"] or len(rows) >= d["pagination"]["count"]:
            break
        last = li
        time.sleep(1)
    save(f, rows)
for cycle in (2024, 2026):
    f = f"by_employer_{cycle}.json"
    if not os.path.exists(os.path.join(OUT, f)):
        save(f, get("/schedules/schedule_a/by_employer/", committee_id=CMTE, cycle=cycle, per_page=100, sort="-total"))
        print("saved", f)
# Largest individual contributions (itemized, $200+), top rows by amount, for the top-donor list
for cycle in (2024, 2026):
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
# Outside spending (independent expenditures) for or against Tran, by committee: shows any UDP, HMP, DCCC, Fairshake money
for cycle in (2024, 2026):
    f = f"ie_by_candidate_{cycle}.json"
    if not os.path.exists(os.path.join(OUT, f)):
        save(f, get("/schedules/schedule_e/by_candidate/", candidate_id="H4CA45170", cycle=cycle, per_page=100, sort="-total"))
        print("saved", f)
print("done")
