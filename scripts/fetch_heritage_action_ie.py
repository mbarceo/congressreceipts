"""Reads Heritage Action for America's independent expenditures from the FEC API into data/heritage_action_ie.json.

Heritage Action is a 501(c)(4) and the Heritage Foundation a 501(c)(3): neither has a PAC that gives to candidates.
Heritage Action's only FEC registration (C90013525) is as an independent expenditure filer, so what the FEC records
is ads, mail and similar spending it paid for itself for or against named candidates (Schedule E). This script
saves that record once for everyone; a tracker can then look up its member by FEC candidate id.

Rows come from the FEC "schedules/schedule_e" endpoint for committee C90013525. The same spending can appear twice
(a 24/48-hour notice and the later periodic report), so rows with the same candidate, date, amount, payee and
support/oppose flag count once, preferring the periodic report. Each row keeps the link to the filing image.
Support ("S") and oppose ("O") are the filer's own designation on the FEC form.

Not a member-neutral claim of alignment: it only shows what Heritage Action itself reported spending on a candidate.
Absence of a row means no reported independent expenditure, not anything about the member's views.

Raw pages are cached in data/heritage_action/raw/ (not committed), so a re-run picks up where it stopped.
Requests are one at a time, three seconds apart. A 429 stops the run (wait an hour; the key allows ~1,000 calls/hr).
Usage: ./scripts/with_fec_key.sh python3 -I scripts/fetch_heritage_action_ie.py
"""
import datetime, json, os, sys, time, urllib.error, urllib.parse, urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RAW = os.path.join(REPO, "data/heritage_action/raw")
OUT = os.path.join(REPO, "data/heritage_action_ie.json")
COMMITTEE = "C90013525"
API = "https://api.open.fec.gov/v1/schedules/schedule_e/"
KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")
os.makedirs(RAW, exist_ok=True)

def get(params):
    url = API + "?" + urllib.parse.urlencode({**params, "api_key": KEY})
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429: raise SystemExit("FEC rate limit hit. Wait an hour, then re-run; saved pages are kept.")
            if attempt == 2: raise SystemExit(f"FEC API error {e.code}; saved pages are kept.") from None   # never re-raise: the URL carries the key
            time.sleep(3)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2: raise SystemExit(f"Network error: {getattr(e, 'reason', e)}; saved pages are kept.") from None
            time.sleep(3)

# Page through, resuming from the cached pages (each file holds its request cursor and its results)
rows, page, params = [], 0, {"committee_id": COMMITTEE, "per_page": 100, "sort": "-expenditure_date"}
while True:
    f = os.path.join(RAW, f"page_{page:03d}.json")
    if os.path.exists(f):
        d = json.load(open(f))
    else:
        d = get(params); json.dump(d, open(f, "w")); print("saved", os.path.basename(f)); time.sleep(3)
    rows += d["results"]
    last = d["pagination"].get("last_indexes")
    if not d["results"] or not last or len(rows) >= d["pagination"]["count"]: break
    params.update(last); page += 1

# One row per distinct expenditure, preferring the periodic report over the notice
best = {}
for r in rows:
    k = (r["candidate_id"], r["expenditure_date"], r["expenditure_amount"], r["payee_name"], r["support_oppose_indicator"])
    if k not in best or (best[k]["is_notice"] and not r["is_notice"]): best[k] = r
items = sorted(best.values(), key=lambda r: (r["expenditure_date"], r["candidate_id"] or ""))

cands = {}
for r in items:
    cid = r["candidate_id"]
    if not cid: continue
    c = cands.setdefault(cid, {"candidateId": cid, "name": r["candidate_name"], "office": r["candidate_office"],
                               "state": r["candidate_office_state"], "district": r["candidate_office_district"],
                               "party": r["candidate_party"], "support": 0.0, "oppose": 0.0, "count": 0, "years": set(), "items": []})
    side = "support" if r["support_oppose_indicator"] == "S" else "oppose"
    c[side] = round(c[side] + r["expenditure_amount"], 2); c["count"] += 1; c["years"].add(r["expenditure_date"][:4])
    c["items"].append({"date": r["expenditure_date"], "amount": r["expenditure_amount"], "side": side,
                       "election": r["election_type_full"], "description": r["expenditure_description"], "filing": r["pdf_url"]})
for c in cands.values(): c["years"] = sorted(c["years"])

out = {"read": datetime.date.today().isoformat(),
       "source": "FEC Schedule E, Heritage Action for America (C90013525), independent expenditures",
       "committeeUrl": f"https://www.fec.gov/data/committee/{COMMITTEE}/",
       "note": "Spending Heritage Action reported for or against named candidates. Not a score and not a statement about any member's views.",
       "rowsRead": len(rows), "distinctExpenditures": len(items),
       "candidates": sorted(cands.values(), key=lambda c: -(c["support"] + c["oppose"]))}
json.dump(out, open(OUT, "w"), indent=1)
print(f'{len(rows)} rows -> {len(items)} distinct expenditures, {len(cands)} candidates, ${sum(c["support"]+c["oppose"] for c in cands.values()):,.2f}')
