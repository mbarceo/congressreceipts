"""Checks bill claims against govinfo's official BILLSTATUS records (data/billstatus/), writes data/bill_checks.json.

Each entry: bill, the role claimed (sponsor, cosponsor or none), and an optional public law that must be listed.
A bill that checked out OK is not fetched again while its key (bill, role, law, House-passage flag, CHECKER_VERSION)
is unchanged and the check is under recheckDays old (data/verify_policy.json, 15); see verify_all.py.
Usage: python3 -I scripts/verify_bills.py [--fresh]
"""
import hashlib, json, os, sys, time, urllib.request
from datetime import date
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, ROOT

OUT = os.path.join(ROOT, "data/billstatus"); os.makedirs(OUT, exist_ok=True)
ME = M["bioguide"]
# The bills this tracker's pages make claims about, from data/bills.json:
#   {"bills": [{"bill": "hr6644", "role": "sponsor"|"cosponsor"|"none", "law": "119-101" or null, "housePassed": true (optional:
#   a House passage action must be in the record), "note": "..."}]}
# (Luz Rivas example: hr5157 sponsor; s1071 law 119-60, the NDAA that carried it; hr6644 law 119-101.)
_bp = os.path.join(ROOT, "data/bills.json")
_BL = json.load(open(_bp))["bills"] if os.path.exists(_bp) else []
BILLS = [(b["bill"], b.get("role", "none"), b.get("law")) for b in _BL]
PASS = {b["bill"] for b in _BL if b.get("housePassed")}
PASS_RX = ("Passed/agreed to in House", "On passage Passed", "On motion to suspend the rules and pass the bill", "agreed to in House")
if not BILLS: print("no data/bills.json entries: nothing to check (list every bill a page makes a claim about)")
# A bill id may carry its Congress ("118-s4991"); a bare one ("hr6644") is the 119th.
split = lambda b: (b.split("-")[0], b.split("-")[1]) if "-" in b else ("119", b)
url_for = lambda b: (lambda c, n: f"https://www.govinfo.gov/bulkdata/BILLSTATUS/{c}/{''.join(ch for ch in n if ch.isalpha())}/BILLSTATUS-{c}{n}.xml")(*split(b))
CHECKER_VERSION = 1   # bump when this check is tightened, so earlier results are not reused
_pol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "verify_policy.json")
RECHECK_DAYS = json.load(open(_pol)).get("recheckDays", 15) if os.path.exists(_pol) else 15
_bc = os.path.join(ROOT, "data/bill_checks.json")
prev = json.load(open(_bc)) if os.path.exists(_bc) and "--fresh" not in sys.argv else {}
def fresh_enough(r, key):
    try: age = (date.today() - date.fromisoformat(r.get("checked", ""))).days
    except ValueError: return False
    return r.get("key") == key and r.get("ok") and age < RECHECK_DAYS
res = {}
for b, role, law in BILLS:
    key = hashlib.sha1(f"{CHECKER_VERSION}|{b}|{role}|{law}|{b in PASS}".encode()).hexdigest()[:16]
    if b in prev and fresh_enough(prev[b], key):
        res[b] = prev[b]; print("KEEP", b, "| checked", prev[b]["checked"]); continue
    p = os.path.join(OUT, b + ".xml")
    if not os.path.exists(p) or os.path.getsize(p) < 1000:
        try:
            open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(url_for(b), headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
            time.sleep(0.7)
        except Exception as e:
            res[b] = {"ok": False, "issue": f"fetch failed: {e}"}; continue
    bill = ET.parse(p).getroot().find("bill")
    kids = lambda tag: list(bill.find(tag)) if bill.find(tag) is not None else []
    sponsors = [s.findtext("bioguideId") for s in kids("sponsors")]
    cos = {c.findtext("bioguideId"): c.findtext("sponsorshipDate") for c in kids("cosponsors")}
    laws = [l.findtext("number") for l in kids("laws")]
    acts = sorted((a.findtext("actionDate"), a.findtext("text") or "") for a in kids("actions"))
    issues = []
    if role == "sponsor" and ME not in sponsors: issues.append(f"{M['short']} is not the sponsor")
    if role == "cosponsor" and ME not in cos: issues.append(f"{M['short']} is not a cosponsor")
    if law and law not in laws: issues.append(f"Public Law {law} not listed")
    if b in PASS and not any(k in t for _, t in acts for k in PASS_RX): issues.append("no House passage action found")
    res[b] = {"ok": not issues, "title": bill.findtext("title"), "role": role, "introduced": bill.findtext("introducedDate"),
              "laws": laws, "latestAction": acts[-1][0] if acts else None, "latestText": acts[-1][1][:120] if acts else None,
              "url": url_for(b), "issue": "; ".join(issues), "key": key, "checked": date.today().isoformat()}
    print("OK  " if not issues else "FAIL", b, "|", (res[b]["title"] or "")[:55], "| laws", laws, "| latest", res[b]["latestAction"], res[b]["issue"])
json.dump(res, open(os.path.join(ROOT, "data/bill_checks.json"), "w"), indent=1)
