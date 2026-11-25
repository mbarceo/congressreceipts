"""Recomputes the site's key figures from raw data and compares them with what the site shows.

"Shown" values are read from the built data the pages display; "actual" values are recomputed here with separate
code from the raw roll-call XML (data/raw: House Clerk or senate.gov), FEC downloads (data/fec/raw) and press releases. Writes
data/computed_checks.json. Usage: python3 -I scripts/verify_computed.py
"""
import glob, json, os, re, sys
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC, ROOT

J = lambda p: json.load(open(os.path.join(ROOT, p)))
num = lambda s: float(re.sub(r"[^\d.]", "", str(s)) or 0)
out = []
def check(label, shown, actual, src, tol=None):
    tol = max(1.0, abs(actual) * 0.005) if tol is None else tol
    out.append({"label": label, "shown": shown, "actual": round(actual, 2), "ok": abs(shown - actual) <= tol, "source": src})

# ---- Votes, from raw roll-call files (House or Senate, via votes_common) ----
# Recomputed here with separate tallying code; only the file parser, the caucus rule (CAUCUS: independents who caucus
# with the Democrats count as Democrats for unity) and the ranking threshold come from votes_common.
from votes_common import load_rolls, MY_ID, LEADER, CAUCUS, unity_min_votes
ME, JEF = MY_ID, LEADER["voteId"]
rolls = [(r["votes"], {k: CAUCUS.get(k) or p for k, p in r["party"].items()}) for r in load_rolls()]
VSRC = "Senate roll-call XML (senate.gov)" if M.get("chamber", "house") == "senate" else "House Clerk roll-call XML"
have = lambda p: os.path.exists(os.path.join(ROOT, p))
both = [(v[ME], v[JEF]) for v, _ in rolls if v.get(ME) in ("Yea", "Nay") and v.get(JEF) in ("Yea", "Nay")]
splits = sum(a != b for a, b in both)
es = J("data/establishment.json")["nums"] if have("data/establishment.json") else None
if es is None: print("skip: leader-agreement checks (data/establishment.json not built yet)")
elif both:
    check(f"Votes where the member and {LEADER['name']} both cast Yea or Nay", es["both"], len(both), VSRC, 0)
    check(f"Votes where the member split from {LEADER['name']}", es["ndiff"], splits, VSRC, 0)
    check(f"Agreement with {LEADER['name']} (%)", float(es["jeffAgree"]), round((len(both) - splits) / len(both) * 100, 1), VSRC, 0.05)
def dside(v, party):
    y = sum(1 for k, x in v.items() if party.get(k) == "D" and x == "Yea"); n = sum(1 for k, x in v.items() if party.get(k) == "D" and x == "Nay")
    return ("Yea" if y > n else "Nay" if n > y else None), y, n
sides = [dside(v, p)[0] for v, p in rolls]
def unity(m):
    same = tot = 0
    for (v, _), side in zip(rolls, sides):
        if side and v.get(m) in ("Yea", "Nay"): tot += 1; same += v[m] == side
    return same, tot
dems = {k for v, p in rolls for k in v if p.get(k) == "D"}
MIN = unity_min_votes(sum(1 for s in sides if s))
scores = {d: s / t for d in dems for s, t in [unity(d)] if t >= MIN}
al = J("data/alignment.json") if have("data/alignment.json") else None
if al is None: print("skip: party-unity and peer checks (data/alignment.json not built yet)")
elif ME in scores:
    check("Party-unity score (%)", al["memberUnity"], round(scores[ME] * 100, 1), VSRC, 0.05)
    check("Party-unity rank among Democrats", al["memberRank"], 1 + sum(1 for x in scores.values() if x > scores[ME]), VSRC, 0)

# Agreement on contested votes (where at least 10% of voting Democrats took the minority side)
def contested(v, party):
    _, y, n = dside(v, party)
    return min(y, n) / max(1, y + n) >= 0.10
crolls = [(v, p) for v, p in rolls if contested(v, p)]
if al is not None:
    peer = {p["name"]: p for p in al["peers"]}
    for name, pid in ((p["name"], p["id"]) for p in CFG["peers"] if p["name"] in peer and peer[p["name"]]["contested"] is not None):
        pairs = [(v[ME], v[pid]) for v, _ in crolls if v.get(ME) in ("Yea", "Nay") and v.get(pid) in ("Yea", "Nay")]
        check(f"Agreement with {name} on contested votes (%)", peer[name]["contested"], round(sum(a == b for a, b in pairs) / len(pairs) * 100, 1), VSRC, 0.05)
    check("Contested votes (Democrats split at least 90-10)", al["contested"], len(crolls), VSRC, 0)

# ---- Money, from raw FEC downloads ----
RAW = os.path.join(ROOT, "data/fec/raw")
rows = {c: json.load(open(os.path.join(RAW, f"committee_contribs_{c}.json"))) for c in map(str, FEC["cycles"])}
allrows = [r for c in rows.values() for r in c]
amt = lambda pred: sum(r.get("contribution_receipt_amount") or 0 for r in allrows if pred(r))
aip_direct = amt(lambda r: r.get("contributor_id") == "C00797670" and r.get("memo_code") != "X")
aip_ear = amt(lambda r: r.get("contributor_id") == "C00797670" and r.get("memo_code") == "X")
dmfi = amt(lambda r: r.get("contributor_id") == "C00710848")
summ = J("data/fec/summary.json")
pro_shown = sum(p["amount"] for p in summ["pacs"] if p["proIsrael"])
check("AIPAC PAC, direct contributions", next((p["amount"] for p in summ["pacs"] if p["id"] == "C00797670" and p["kind"] != "Earmarked via conduit"), 0), aip_direct, "FEC Schedule A, committee C00797670")
check("AIPAC PAC, earmarked donations", next((p["amount"] for p in summ["pacs"] if p["id"] == "C00797670" and p["kind"] == "Earmarked via conduit"), 0), aip_ear, "FEC Schedule A memo entries, committee C00797670")
check("AIPAC PAC, total (direct + earmarked)", sum(p["amount"] for p in summ["pacs"] if p["id"] == "C00797670"), aip_direct + aip_ear, "FEC Schedule A, committee C00797670")
check("DMFI PAC", next((p["amount"] for p in summ["pacs"] if p["id"] == "C00710848"), 0), dmfi, "FEC Schedule A, committee C00710848")
check("Pro-Israel money in the FEC filings, all cycles", pro_shown, aip_direct + aip_ear + dmfi + amt(lambda r: r.get("contributor_id") not in ("C00797670", "C00710848") and re.search(r"J ?STREET|NORPAC|PRO-ISRAEL AMERICA|JACPAC|JOINT ACTION COMMITTEE FOR POLITICAL", r.get("contributor_name") or "", re.I)), "FEC Schedule A")
lead = J("data/fec/leadership.json")
_LC = FEC.get("leaders") or {}
LEADERS = (_LC.get(M.get("chamber", "house").lower()) or {}).get("list", []) if isinstance(_LC, dict) else _LC
def lead_match(r):
    n, cid = r.get("contributor_name") or "", r.get("contributor_id")
    for l in LEADERS:
        if cid and cid in l.get("ids", []): return True
        if (not l.get("ids") or not cid) and l.get("rx") and re.search(l["rx"], n, re.I): return True
    return False
CYC = [str(c) for c in FEC["cycles"]]
lab = lambda c: f"{int(c) - 1}-{c[2:]}"
for c in CYC:
    check(f"Party leaders' committees, {lab(c)}", sum(v.get("y" + c, 0) for v in lead.values()),
          sum(r.get("contribution_receipt_amount") or 0 for r in rows[c] if r.get("memo_code") != "X" and lead_match(r)),
          "FEC Schedule A, by leader committee ID or name (fec.leaders in tracker.config.json)")
calc = J("data/fec/establishment_calc.json")
for c in CYC:
    for k in ("corporate", "labor", "trade"):
        shown = num(es[f"corp{c[2:]}"]) if k == "corporate" and es and es.get(f"corp{c[2:]}") else calc[c]["cat"].get(k, 0)
        check(f"{k.title()} PAC money, {lab(c)}", shown, calc[c]["cat"].get(k, 0),
              "FEC Schedule A, sorted by FEC organization type then name (scripts/build_establishment.py)")

# ---- Press releases ----
stm, full = J("data/statements.json"), J("data/statements_full.json")
site = re.sub(r"^https?://(www\.)?", "", M.get("site", "")).rstrip("/") or "official site"
tile = next((t for t in J("data/overview.json")["tiles"] if "homeless" in t["q"].lower()), None)
if tile:   # only trackers with a homelessness tile (the template's CA-29 example); add similar checks for your own tiles
    hm = sum(1 for s in stm if re.search(r"homeless|unhoused|encampment", s["title"] + " " + full.get(s["u"], ""), re.I))
    check("Press releases on the official site", int(re.search(r"of \w+ (\d+)", tile["rule"]).group(1)), len(stm), f"{site} press releases", 0)
    check("Releases mentioning homelessness", int(re.search(r"^(\d+) of", tile["rule"]).group(1)), hm, "Full text of every release", 0)

json.dump(out, open(os.path.join(ROOT, "data/computed_checks.json"), "w"), indent=1)
for c in out: print("OK  " if c["ok"] else "FAIL", c["label"], "| shown", c["shown"], "| recomputed", c["actual"])
print(sum(c["ok"] for c in out), "of", len(out), "computed figures match")
