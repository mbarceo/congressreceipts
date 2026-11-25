"""Finds the member's FEC candidate and committee IDs and writes them into tracker.config.json.

Run this once, with your own FEC API key, before fetch_fec.py:
    FEC_API_KEY=your_key python3 -I scripts/resolve_fec.py
It searches candidates by name and state (House: also district; Senate, member.chamber "senate": office S),
lists every match with its principal campaign committee, and writes the IDs only when exactly one candidate
matches. If several match (for example a candidate ID per cycle), it prints them and stops so you can pick;
nothing is guessed.

Senators serve six-year terms but FEC data comes in two-year cycles, so for a senator it also writes
fec.cycles and fec.cycleLabels: the cycle of the election that began the current term through the current
cycle (from the candidate's FEC election years), e.g. Padilla (elected 2022, next up 2028) gets 2022, 2024,
2026 in 2026. Pass --keep-cycles to leave fec.cycles as it is. Add a cycle by hand if you want an earlier one
(e.g. an appointed senator's first months, as with Padilla's 2020 cycle).
"""
import datetime, json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC, ROOT

KEY = os.environ.get(FEC["keyEnv"])
if not KEY: raise SystemExit(f"Set {FEC['keyEnv']} to your FEC API key first (the shared DEMO_KEY is too limited).")

def get(path, **params):
    params["api_key"] = KEY
    url = "https://api.open.fec.gov/v1" + path + "?" + urllib.parse.urlencode(params, doseq=True)
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
    except urllib.error.HTTPError as e:   # report the path only: the full URL carries the API key
        raise SystemExit(f"FEC API error {e.code} on {path}: {'rate limit or bad key' if e.code in (403, 429) else e.reason}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise SystemExit(f"Network error on {path}: {getattr(e, 'reason', e)}") from None

last = M["name"].split()[-1]
senate = M.get("chamber", "house") == "senate"
params = dict(q=last, state=M["state"], office="S" if senate else "H", per_page=50)
if not senate: params["district"] = M["district"].zfill(2)       # senators run statewide: no district
res = get("/candidates/search/", **params)["results"]
res = [r for r in res if last.lower() in r["name"].lower() and r["party"] in ("DEM", "DFL")] or res
rows = []
for r in res:
    cm = get(f"/candidate/{r['candidate_id']}/committees/", designation="P", per_page=20)["results"]
    time.sleep(0.5)
    rows.append((r, cm))
    print(f"{r['candidate_id']}  {r['name']}  {r['party']}  cycles {r.get('election_years')}")
    for c in cm: print(f"    principal committee {c['committee_id']}  {c['name']}  (cycles {c.get('cycles')})")

def election_day(y):
    """First Tuesday after the first Monday in November."""
    d = datetime.date(y, 11, 2)
    while d.weekday() != 1: d += datetime.timedelta(days=1)
    return d

def senate_cycles(election_years, today=None):
    """Cycles (even end years) from the election that began the current term through the current cycle, with labels."""
    today = today or datetime.date.today()
    cur = today.year + today.year % 2
    held = [y for y in election_years or () if election_day(y) < today]
    nxt = min((y for y in election_years or () if election_day(y) >= today), default=None)
    if not held:   # appointed and not yet elected: start from the cycle that contains the swearing-in
        since = M.get("inOfficeSince") or today.isoformat()
        first = int(since[:4]) + int(since[:4]) % 2
    else:
        first = max(held)
    cycles = list(range(first, cur + 1, 2))
    lab = lambda c: f"{c - 1}-{str(c)[2:]}" + (f" ({c} election)" if held and c == first else " (re-election)" if c == nxt else " (in office)")
    return cycles, {str(c): lab(c) for c in cycles}

ok = [(r, cm) for r, cm in rows if len(cm) == 1]
if len(rows) == 1 and len(ok) == 1:
    r, cm = ok[0]
    CFG["fec"]["candidateId"], CFG["fec"]["committeeId"] = r["candidate_id"], cm[0]["committee_id"]
    if senate and "--keep-cycles" not in sys.argv:
        CFG["fec"]["cycles"], CFG["fec"]["cycleLabels"] = senate_cycles(r.get("election_years"))
        print(f"Senate cycles from election years {r.get('election_years')}: {CFG['fec']['cycleLabels']}")
    json.dump(CFG, open(os.path.join(ROOT, "tracker.config.json"), "w"), indent=2, ensure_ascii=False)
    print(f"\nWrote candidateId={r['candidate_id']} committeeId={cm[0]['committee_id']} to tracker.config.json")
else:
    print("\nNot unique, so nothing was written. Set fec.candidateId and fec.committeeId in tracker.config.json by hand.")
    print("If the member has one candidate ID but a different committee per cycle, fetch_fec.py needs a per-cycle committee map.")
