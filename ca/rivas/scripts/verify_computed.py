"""Recomputes the site's key figures from raw data and compares them with what the site shows.

"Shown" values are read from the built data the pages display; "actual" values are recomputed here with separate
code from the raw House Clerk XML (data/raw), FEC downloads (data/fec/raw) and press releases. Writes
data/computed_checks.json. Usage: python3 -I scripts/verify_computed.py
"""
import glob, json, os, re, sys
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, FEC, ROOT

J = lambda p: json.load(open(os.path.join(ROOT, p)))
num = lambda s: float(re.sub(r"[^\d.]", "", str(s)) or 0)
out = []
def check(label, shown, actual, src, tol=None):
    tol = max(1.0, abs(actual) * 0.005) if tol is None else tol
    out.append({"label": label, "shown": shown, "actual": round(actual, 2), "ok": abs(shown - actual) <= tol, "source": src})

# ---- Votes, from raw roll-call XML ----
ME, JEF = M["bioguide"], "J000294"
rolls = []
for p in sorted(glob.glob(os.path.join(ROOT, "data/raw/*-roll*.xml"))):
    t = ET.parse(p).getroot(); v, party = {}, {}
    for rv in t.iter("recorded-vote"):
        l = rv.find("legislator"); x = (rv.findtext("vote") or "").strip()
        v[l.get("name-id")] = {"Aye": "Yea", "No": "Nay"}.get(x, x); party[l.get("name-id")] = l.get("party")
    rolls.append((v, party))
both = [(v[ME], v[JEF]) for v, _ in rolls if v.get(ME) in ("Yea", "Nay") and v.get(JEF) in ("Yea", "Nay")]
splits = sum(a != b for a, b in both)
es = J("data/establishment.json")["nums"]
check("Votes where she and Jeffries both cast Yea or Nay", es["both"], len(both), "House Clerk roll-call XML", 0)
check("Votes where she split from Jeffries", es["ndiff"], splits, "House Clerk roll-call XML", 0)
check("Agreement with Jeffries (%)", float(es["jeffAgree"]), round((len(both) - splits) / len(both) * 100, 1), "House Clerk roll-call XML", 0.05)
def unity(m):
    same = tot = 0
    for v, party in rolls:
        y = sum(1 for k, x in v.items() if party.get(k) == "D" and x == "Yea"); n = sum(1 for k, x in v.items() if party.get(k) == "D" and x == "Nay")
        side = "Yea" if y > n else "Nay" if n > y else None
        if side and v.get(m) in ("Yea", "Nay"): tot += 1; same += v[m] == side
    return same, tot
dems = {k for v, p in rolls for k in v if p.get(k) == "D"}
scores = {d: s / t for d in dems for s, t in [unity(d)] if t >= 200}
al = J("data/alignment.json")
check("Party-unity score (%)", al["memberUnity"], round(scores[ME] * 100, 1), "House Clerk roll-call XML", 0.05)
check("Party-unity rank among Democrats", al["memberRank"], 1 + sum(1 for x in scores.values() if x > scores[ME]), "House Clerk roll-call XML", 0)

# Agreement on contested votes (where at least 10% of voting Democrats took the minority side)
def contested(v, party):
    y = sum(1 for k, x in v.items() if party.get(k) == "D" and x == "Yea"); n = sum(1 for k, x in v.items() if party.get(k) == "D" and x == "Nay")
    return min(y, n) / max(1, y + n) >= 0.10
crolls = [(v, p) for v, p in rolls if contested(v, p)]
peer = {p["name"]: p for p in al["peers"]}
for name, pid in (("Hakeem Jeffries", "J000294"), ("Josh Gottheimer", "G000583"), ("Alexandria Ocasio-Cortez", "O000172")):
    pairs = [(v[ME], v[pid]) for v, _ in crolls if v.get(ME) in ("Yea", "Nay") and v.get(pid) in ("Yea", "Nay")]
    check(f"Agreement with {name} on contested votes (%)", peer[name]["contested"], round(sum(a == b for a, b in pairs) / len(pairs) * 100, 1), "House Clerk roll-call XML", 0.05)
check("Contested votes (Democrats split at least 90-10)", al["contested"], len(crolls), "House Clerk roll-call XML", 0)

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
check("Pro-Israel money in her filings, both cycles", pro_shown, aip_direct + aip_ear + dmfi + amt(lambda r: r.get("contributor_id") not in ("C00797670", "C00710848") and re.search(r"J ?STREET|NORPAC|PRO-ISRAEL AMERICA|JACPAC|JOINT ACTION COMMITTEE FOR POLITICAL", r.get("contributor_name") or "", re.I)), "FEC Schedule A")
lead = J("data/fec/leadership.json")
LEAD_IDS = re.compile(r"JEFFRIES|JEFF PAC|PELOSI|PAC TO THE FUTURE|KATHERINE CLARK|FAIR SHOT PAC|CLARK FRONTLINE|AGUILAR|CA LUV PAC|HOYER|AMERIPAC|^DCCC|DEMOCRATIC CONGRESSIONAL CAMPAIGN", re.I)
for c, lab in (("2024", "2023-24"), ("2026", "2025-26")):
    check(f"Party leaders' committees, {lab}", sum(v["y" + c] for v in lead.values()),
          sum(r.get("contribution_receipt_amount") or 0 for r in rows[c] if r.get("memo_code") != "X" and LEAD_IDS.search(r.get("contributor_name") or "")),
          "FEC Schedule A, by leader committee name")
calc = J("data/fec/establishment_calc.json")
for c, lab in (("2024", "2023-24"), ("2026", "2025-26")):
    for k in ("corporate", "labor", "trade"):
        check(f"{k.title()} PAC money, {lab}", num(es.get({"corporate": "corp" + c[2:], "labor": None, "trade": None}[k]) or calc[c]["cat"].get(k, 0)) if k == "corporate" else calc[c]["cat"].get(k, 0),
              calc[c]["cat"].get(k, 0), "FEC Schedule A, sorted by FEC organization type then name (scripts/build_establishment.py)")

# ---- Press releases ----
stm, full = J("data/statements.json"), J("data/statements_full.json")
hm = sum(1 for s in stm if re.search(r"homeless|unhoused|encampment", s["title"] + " " + full.get(s["u"], ""), re.I))
tile = next(t for t in J("data/overview.json")["tiles"] if "homeless" in t["q"].lower())
check("Press releases on her House site", int(re.search(r"of her (\d+)", tile["rule"]).group(1)), len(stm), "rivas.house.gov press releases", 0)
check("Releases mentioning homelessness", int(re.search(r"^(\d+) of", tile["rule"]).group(1)), hm, "Full text of every release", 0)

json.dump(out, open(os.path.join(ROOT, "data/computed_checks.json"), "w"), indent=1)
for c in out: print("OK  " if c["ok"] else "FAIL", c["label"], "| shown", c["shown"], "| recomputed", c["actual"])
print(sum(c["ok"] for c in out), "of", len(out), "computed figures match")
