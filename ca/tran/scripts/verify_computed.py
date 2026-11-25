"""Recomputes every figure the site derives from FEC and House Clerk data and checks it against the
number shown on the site. Writes data/computed_checks.json. Usage: python3 -I scripts/verify_computed.py
"""
import json, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = os.path.join(ROOT, "data/fec/raw")
load = lambda c: json.load(open(os.path.join(RAW, f"committee_contribs_{c}.json")))
tot = lambda c: json.load(open(os.path.join(RAW, f"totals_{c}.json")))["results"][0]
summ = json.load(open(os.path.join(ROOT, "data/fec/summary.json")))
align = json.load(open(os.path.join(ROOT, "data/alignment.json")))
calc = json.load(open(os.path.join(ROOT, "data/fec/establishment_calc.json")))
lead = json.load(open(os.path.join(ROOT, "data/fec/leadership.json")))

def amt(rows, pred, memo=None):
    return sum((r.get("contribution_receipt_amount") or 0) for r in rows if pred(r) and (memo is None or (r.get("memo_code") == "X") == memo))
name = lambda rx: (lambda r: re.search(rx, r.get("contributor_name") or "", re.I))
r24, r26 = load("2024"), load("2026")
checks = []
def check(label, shown, actual, tol=0.006, src="FEC Schedule A (committee contributions), api.open.fec.gov"):
    ok = abs(actual - shown) <= max(1, abs(shown) * tol)
    checks.append({"label": label, "shown": shown, "actual": round(actual, 2), "ok": ok, "source": src})

js24 = amt(r24, name(r"JSTREET"), True); js26 = amt(r26, name(r"JSTREET"), True)
check("J Street earmarked donations, 2023-24", 83533, js24)
check("J Street earmarked donations, 2025-26", 131010, js26)
check("J Street earmarked donations, total", 214543, js24 + js26)
check("J Street direct contributions, 2025-26", 2057, amt(r26, name(r"^JSTREETPAC$"), False))
check("JACPAC earmarked donations, 2025-26", 2500, amt(r26, name(r"JOINT ACTION COMMITTEE"), True))
check("DMFI PAC, 2023-24", 1000, amt(r24, name(r"DMFI"), False))
pro = sum(c["slices"]["proisrael"] for k, c in summ["cycles"].items() if k != "all")
check("Total pro-Israel money", 220100, pro)
check("Total raised, both cycles", 12502347, tot("2024")["receipts"] + tot("2026")["receipts"])
check("Pro-Israel share of money raised (%)", 1.8, pro / (tot("2024")["receipts"] + tot("2026")["receipts"]) * 100, tol=0.03)
check("AIPAC PAC (C00797670) to Tran, both cycles", 0, amt(r24 + r26, lambda r: r.get("contributor_id") == "C00797670"))
check("United Democracy Project spending for/against Tran", 0, sum(x["total"] for x in summ["outside"] if x["id"] == "C00799031"), src="FEC Schedule E by candidate")
check("End Citizens United, 2023-24 (direct + earmarked)", 9550, amt(r24, name(r"END CITIZENS UNITED")))
check("End Citizens United, 2025-26", 0, amt(r26, name(r"END CITIZENS UNITED")))
check("Corporate PAC money, 2025-26", 305250, calc["2026"]["cat"].get("corporate", 0), src="FEC Schedule A, classified by FEC organization type, then name (scripts/build_establishment.py)")
check("Corporate PACs that gave, 2025-26", 91, calc["2026"]["ncorp"], tol=0)
check("Corporate PAC money, 2023-24", 0, calc["2024"]["cat"].get("corporate", 0))
check("Trade association money, 2025-26", 137507, calc["2026"]["cat"].get("trade", 0))
check("Trade association money, 2023-24", 35500, calc["2024"]["cat"].get("trade", 0))
check("Labor PAC money, 2025-26", 196500, calc["2026"]["cat"].get("labor", 0))
check("Jeffries committees, total", 74942, lead["Hakeem Jeffries"]["y2024"] + lead["Hakeem Jeffries"]["y2026"])
check("Jeffries Battleground Protection Fund", 56942, amt(r26, name(r"JEFFRIES BATTLEGROUND"), False))
check("Party leaders' committees, 2023-24", 56500, sum(v["y2024"] for v in lead.values()))
check("Party leaders' committees, 2025-26", 135759, sum(v["y2026"] for v in lead.values()))
ie = summ["outside"]
check("Outside spending for Tran, 2023-24", 4358605, sum(x["total"] for x in ie if x["cycle"] == "2024" and x["side"] == "support"), src="FEC Schedule E by candidate")
check("House Majority PAC for Tran, 2023-24", 1889515, sum(x["total"] for x in ie if x["id"] == "C00495028" and x["side"] == "support"), src="FEC Schedule E by candidate")
check("Congressional Leadership Fund against Tran, 2023-24", 11363827, sum(x["total"] for x in ie if x["id"] == "C00504530"), src="FEC Schedule E by candidate")
check("Fairshake spending for/against Tran, 2025-26", 0, sum(x["total"] for x in ie if "FAIRSHAKE" in (x["committee"] or "").upper()), src="FEC Schedule E by candidate")
check("Party-unity score (%)", 94.0, align["tranUnity"], tol=0, src="House Clerk roll-call XML (scripts/build_alignment.py)")
check("Party-unity rank among Democrats", 189, align["tranRank"], tol=0, src="House Clerk roll-call XML")
check("Agreement with Jeffries on contested votes (%)", 45.8, next(p["contested"] for p in align["peers"] if p["name"] == "Hakeem Jeffries"), tol=0, src="House Clerk roll-call XML")
# Leadership PAC gifts in the two days after the Red to Blue announcement (Mar 28, 2024)
early = [r for r in r24 if re.search(r"JEFF PAC|AMERIPAC|FAIR SHOT|CA LUV|CALIFORNIA LEADERSHIP UNITED", r.get("contributor_name") or "", re.I) and (r.get("contribution_receipt_date") or "")[:10] in ("2024-03-28", "2024-03-29")]
check("Leadership PACs giving $5,000 on Mar 28-29, 2024", 4, len({r["contributor_name"] for r in early}), tol=0)
check("Jeffries for Congress, both cycles", 8000, amt(r24 + r26, name(r"^JEFFRIES FOR CONGRESS"), False))
check("Jeffries leadership PAC (JEFF PAC), 2023-24", 10000, amt(r24, name(r"JEFF PAC"), False))
check("Each Red to Blue-week leadership PAC gift ($)", 5000, max(r["contribution_receipt_amount"] for r in early), tol=0)
# AIPAC PAC gifts to Michelle Steel in 2023-24: sum of the itemized rows on ProPublica (saved copy)
import html as _h
_idx = json.load(open(os.path.join(ROOT, "data/sources/index.json")))
_u = "https://projects.propublica.org/itemizer/committee/C00704981/pac-donations/C00797670"
_t = re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", open(os.path.join(ROOT, "data/sources", _idx[_u]["file"]), encoding="utf-8", errors="replace").read())))
_rows = re.findall(r"Political Action Committee (?:[A-Z][a-z]+\.? \d{1,2}, (\d{4})) \$([\d,]+)", _t)
check("AIPAC PAC to Michelle Steel, 2023-24", 19512, sum(int(a.replace(",", "")) for y, a in _rows if y in ("2023", "2024")), tol=0, src="ProPublica FEC Itemizer rows (saved copy)")
json.dump(checks, open(os.path.join(ROOT, "data/computed_checks.json"), "w"), indent=1)
for c in checks: print("OK  " if c["ok"] else "FAIL", c["label"], "| shown", c["shown"], "| recomputed", c["actual"])
print(sum(c["ok"] for c in checks), "of", len(checks), "computed figures match")
