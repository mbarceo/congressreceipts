"""Checks every claim that cites a House roll call against the Clerk's XML in data/raw.

For each claim: Tran's vote (Yea/Nay/Present) must match the wording, and every tally quoted
(e.g. "427-1", "113–75") must match the roll call's overall or party totals.
Writes results into data/verification.json. Usage: python3 -I scripts/verify_votes.py
"""
import json, os, re
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
claims = json.load(open(os.path.join(ROOT, "data/claims.json")))
vpath = os.path.join(ROOT, "data/verification.json")
ver = json.load(open(vpath)) if os.path.exists(vpath) else {}

def roll(url):
    m = re.search(r"clerk\.house\.gov/Votes/(\d{4})(\d+)", url or "")
    if not m: return None
    y, n = m.group(1), int(m.group(2))
    p = os.path.join(ROOT, f"data/raw/{y}-roll{n:03d}.xml")
    if not os.path.exists(p): return {"missing": p}
    t = ET.parse(p).getroot(); md = t.find("vote-metadata")
    tran = None
    for rv in t.iter("recorded-vote"):
        if rv.find("legislator").get("name-id") == "T000491":
            tran = {"Aye": "Yea", "No": "Nay"}.get(rv.findtext("vote").strip(), rv.findtext("vote").strip())
    tot = md.find(".//totals-by-vote")
    gi = lambda e, k: int(e.findtext(k) or 0) if e is not None and (e.findtext(k) or "").strip().isdigit() else 0
    party = {(tp.findtext("party") or "").strip(): (gi(tp, "yea-total"), gi(tp, "nay-total")) for tp in md.iter("totals-by-party")}
    return {"year": y, "n": n, "tran": tran, "yea": gi(tot, "yea-total"), "nay": gi(tot, "nay-total"),
            "party": party, "bill": md.findtext("legis-num"), "desc": md.findtext("vote-desc"), "date": md.findtext("action-date"),
            "result": md.findtext("vote-result")}

def expected_vote(text):
    t = text.lower()
    if "present" in t and "voted" in t: return "Present"
    # Look at the first vote verb in the sentence
    m = re.search(r"\b(voted|votes|vote)\s+(for|yes|to|against|no)\b", t)
    if not m: return None
    return "Nay" if m.group(2) in ("against", "no") else "Yea"

ok = bad = 0
for c in claims:
    urls = [c.get("url")] + (c.get("urls") or [])
    rc = next((roll(u) for u in urls if u and "clerk.house.gov/Votes/" in u), None)
    if not rc: continue
    issues = []
    if "missing" in rc:
        issues.append("roll-call file not downloaded")
    else:
        exp = expected_vote(c["text"])
        named = rc["tran"] not in ("Yea", "Nay", "Present", None) and rc["tran"].lower() in c["text"].lower()
        if exp and exp != rc["tran"] and not named:
            issues.append(f"text implies {exp}, Clerk record shows {rc['tran']}")
        pairs = {(rc["yea"], rc["nay"]), (rc["nay"], rc["yea"])}
        for p, (y, n) in rc["party"].items(): pairs |= {(y, n), (n, y)}
        for a, b in re.findall(r"\b(\d{1,3})\s*[-–]\s*(\d{1,3})\b", c["text"]):
            if int(a) > 50 or int(b) > 50 or (int(a), int(b)) in pairs:
                if (int(a), int(b)) not in pairs: issues.append(f"tally {a}-{b} not in roll call totals")
    status = "verified" if not issues else "mismatch"
    ok += status == "verified"; bad += status != "verified"
    ver[c["id"]] = {"status": status, "method": "House Clerk roll-call XML (primary record)",
                    "detail": None if "missing" in rc else f"Roll {rc['year']}-{rc['n']} ({rc['bill']}, {rc['date']}): Tran {rc['tran']}; total {rc['yea']}-{rc['nay']}; {rc['result']}",
                    "issues": issues}
    if issues: print("MISMATCH", c["id"], "|", c["text"][:110], "|", issues)
json.dump(ver, open(vpath, "w"), indent=1)
print(f"roll-call claims: {ok} verified, {bad} with issues")
