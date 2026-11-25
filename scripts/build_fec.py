"""Builds data/fec/summary.json for the Money tab from FEC data in data/fec/raw.

Pie slices come from the FEC cycle totals. Pro-Israel money = direct gifts from pro-Israel PACs
plus individual donations earmarked through a pro-Israel conduit (e.g. JStreetPAC). Earmarked
gifts are already inside the FEC's individual totals, so they are moved out of the itemized-
individual slice to avoid counting them twice. Usage: python3 -I scripts/build_fec.py
"""
import collections, json, os, re
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC, need

ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
RAW = os.environ.get("TRACKER_FEC_RAW") or os.path.join(ROOT, "data/fec/raw")   # override only for tests
PRO_ISRAEL = re.compile(r"JSTREET|J STREET|\bDMFI\b|DEMOCRATIC MAJORITY FOR ISRAEL|ISRAEL|\bAIPAC\b|NORPAC|"
                        r"PRO-ISRAEL AMERICA|JOINT ACTION COMMITTEE FOR POLITICAL AFFAIRS|JACPAC|TO PROTECT OUR HERITAGE", re.I)
KIND = {"11C": "PAC or committee", "11B": "Party", "12": "Joint fundraising"}
LABEL = FEC.get("cycleLabels", {})
SUMMARY = os.environ.get("TRACKER_FEC_SUMMARY") or os.path.join(ROOT, "data/fec/summary.json")   # override only for tests

def date(s): return (s or "")[:10]
out = {"cycles": {}, "pacs": [], "jeffries": {}}
pacs = {}
allsl = collections.Counter()
throughs = []
for cycle in tuple(map(str, FEC["cycles"])):
    t = json.load(open(os.path.join(RAW, f"totals_{cycle}.json")))["results"][0]
    rows = json.load(open(os.path.join(RAW, f"committee_contribs_{cycle}.json")))
    pro_direct = pro_earmark = 0.0
    pac15 = misfiled = 0.0
    for r in rows:
        amt = r.get("contribution_receipt_amount") or 0
        name = (r.get("contributor_name") or "").strip()
        memo = r.get("memo_code") == "X"
        line = r.get("line_number")
        if line == "15" and r.get("receipt_type") == "15K" and not memo:
            line = "11C"; pac15 += amt  # PAC gift filed as "other receipts"
        elif line in ("11AI", "11A") and (r.get("contributor_id") or "").startswith("C") and not memo:
            # A registered committee's gift filed on the individual line (Padilla 2022: AIPAC PAC $5,000). It counts as
            # PAC money here, and comes out of the itemized-individual total below so it isn't counted twice.
            line = "11C"; misfiled += amt
        is_pro = bool(PRO_ISRAEL.search(name))
        if memo:
            # Conduit memo: individual gifts passed through this committee (ActBlue, JStreetPAC, ...)
            if not is_pro: continue
            pro_earmark += amt
            key = (name + " (earmarked donations)", r.get("contributor_id"))
            kind = "Earmarked via conduit"
        else:
            if line not in KIND: continue
            if is_pro and line == "11C": pro_direct += amt
            key = (name, r.get("contributor_id"))
            kind = KIND[line]
        p = pacs.setdefault(key, {"name": key[0], "id": key[1], "kind": kind, "proIsrael": is_pro, "amount": 0.0, "n": 0, "byCycle": {}})
        p["amount"] += amt; p["n"] += 1
        p["byCycle"][cycle] = round(p["byCycle"].get(cycle, 0) + amt, 2)
    ind_item = t["individual_itemized_contributions"]
    ind_item -= misfiled
    moved = min(pro_earmark, ind_item)
    sl = {
        "small": t["individual_unitemized_contributions"],
        "large": ind_item - moved,
        "proisrael": pro_direct + moved,
        "otherpac": t["other_political_committee_contributions"] + pac15 + misfiled - pro_direct,
        "party": t["political_party_committee_contributions"],
        "other": max(0.0, t["transfers_from_other_authorized_committee"] + (t["candidate_contribution"] or 0)
                     + (t["other_receipts"] or 0) - pac15 + (t["offsets_to_operating_expenditures"] or 0)),
    }
    sl = {k: round(v, 2) for k, v in sl.items()}
    allsl.update(sl)
    through = date(t["coverage_end_date"])
    throughs.append(through)
    out["cycles"][cycle] = {"label": LABEL.get(cycle) or f"{int(cycle) - 1}-{cycle[2:]}", "slices": sl, "through": through, "receipts": t["receipts"],
                            "proDirect": round(pro_direct, 2), "proEarmark": round(pro_earmark, 2),
                            "note": f"Pro-Israel slice: ${pro_direct:,.0f} in direct PAC gifts plus ${moved:,.0f} in individual donations earmarked through J Street PAC."}
# "Both cycles" for a House member's two cycles; a senator's six-year term usually spans three or four
both = "both cycles" if len(out["cycles"]) == 2 else f"all {len(out['cycles'])} cycles"
out["cycles"] = {"all": {"label": both[0].upper() + both[1:], "slices": {k: round(v, 2) for k, v in allsl.items()}, "through": max(throughs),
                         "note": f"Pro-Israel slice combines direct PAC gifts and donations earmarked through J Street PAC across {both}."},
                 **out["cycles"]}
for p in pacs.values():
    p["amount"] = round(p["amount"], 2)
out["pacs"] = sorted(pacs.values(), key=lambda p: -p["amount"])
# The main party leader's committees (House: Jeffries; Senate: Schumer), by FEC ID when fec.leadershipIds lists them, else by name
LIDS = set(FEC.get("leadershipIds") or ())
j = [p for p in out["pacs"] if p["id"] in LIDS or re.search(FEC["leadershipRx"], p["name"], re.I)]
out["jeffries"] = {"total": round(sum(p["amount"] for p in j), 2), "items": j}
json.dump(out, open(SUMMARY, "w"), indent=1)

for k, c in out["cycles"].items():
    tot = sum(c["slices"].values())
    print(k, c["label"], f"total ${tot:,.0f}", {s: f"{v/tot*100:.1f}%" for s, v in c["slices"].items()})
print("pro-Israel committees:", [(p["name"], p["amount"], p["byCycle"]) for p in out["pacs"] if p["proIsrael"]])
print("Leader's committees:", out["jeffries"]["total"], [(p["name"], p["kind"], p["amount"]) for p in j])
print("committees listed:", len(out["pacs"]))

# ---- Employers of individual donors, and top individual donors ----
SKIP = re.compile(r"^(NOT EMPLOYED|SELF[- ]?EMPLOYED|N/?A|NULL|NONE|RETIRED|INFORMATION REQUESTED.*|UNEMPLOYED|HOMEMAKER|REQUESTED)$", re.I)
def norm(name):
    n = re.sub(r"[.,&]", " ", (name or "").upper())
    n = re.sub(r"\b(LLP|LLC|INC|PC|APC|PLLC|CORP|CORPORATION|CO|LTD|THE|LAW FIRM|LAW GROUP)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()
LAW = re.compile(r"\bLAW\b|\bLLP\b|ATTORNEY|\bLEGAL\b|\bPLLC\b|\bAPC\b" + ("|" + FEC["lawFirmsRx"] if FEC.get("lawFirmsRx") else ""), re.I)   # fec.lawFirmsRx: firms without "law" in the name
emp = {}
for cycle in tuple(map(str, FEC["cycles"])):
    p = os.path.join(RAW, f"by_employer_{cycle}.json")
    if not os.path.exists(p): continue
    for r in json.load(open(p))["results"]:
        e = (r.get("employer") or "").strip()
        if not e or SKIP.match(e): continue
        k = norm(e)
        x = emp.setdefault(k, {"name": e.title(), "total": 0.0, "count": 0, "byCycle": {}, "law": bool(LAW.search(e))})
        x["total"] += r["total"]; x["count"] += r["count"]
        x["byCycle"][cycle] = round(x["byCycle"].get(cycle, 0) + r["total"], 2)
emp_all = sorted(({**v, "total": round(v["total"], 2)} for v in emp.values()), key=lambda v: -v["total"])
out["employers"] = emp_all[:60]

donors = {}
for cycle in tuple(map(str, FEC["cycles"])):
    p = os.path.join(RAW, f"top_individuals_{cycle}.json")
    if not os.path.exists(p): continue
    for r in json.load(open(p)):
        if r.get("memo_code") == "X": continue
        nm = (r.get("contributor_name") or "").strip()
        if not nm: continue
        k = (nm.upper(), (r.get("contributor_zip") or "")[:5])
        # Privacy: donors are grouped by name and ZIP so one person's gifts add up, but only employer and
        # occupation are published. Names, cities and addresses never leave this script.
        x = donors.setdefault(k, {"employer": (r.get("contributor_employer") or "").title(),
                                  "occupation": (r.get("contributor_occupation") or "").title(),
                                  "total": 0.0, "byCycle": {}})
        a = r.get("contribution_receipt_amount") or 0
        x["total"] += a; x["byCycle"][cycle] = round(x["byCycle"].get(cycle, 0) + a, 2)
out["donors"] = sorted(({**v, "total": round(v["total"], 2)} for v in donors.values()), key=lambda v: -v["total"])[:100]
json.dump(out, open(SUMMARY, "w"), indent=1)
print("employers:", len(out["employers"]), [ (e["name"], e["total"]) for e in out["employers"][:8]])
print("donors:", len(out["donors"]))

# ---- Outside spending for or against the member ----
ie = []
for cycle in tuple(map(str, FEC["cycles"])):
    p = os.path.join(RAW, f"ie_by_candidate_{cycle}.json")
    if not os.path.exists(p): continue
    for r in json.load(open(p)).get("results", []):
        ie.append({"cycle": cycle, "committee": r.get("committee_name"), "id": r.get("committee_id"),
                   "side": "support" if r.get("support_oppose_indicator") == "S" else "oppose", "total": round(r.get("total") or 0, 2)})
out["outside"] = sorted(ie, key=lambda x: -x["total"])
json.dump(out, open(SUMMARY, "w"), indent=1)
udp = [x for x in ie if x["id"] == "C00799031" or "UNITED DEMOCRACY" in (x["committee"] or "").upper()]
print("outside spending rows:", len(ie), "| UDP rows:", udp or "none")

# ---- Industry watch: PACs and donor employers whose names match the issue categories in tracker.config.json ----
# Name matching only: a hit means "the name looks like", not a verified classification. The page says so.
watch = []
for w in FEC["watch"]:
    # optional "not": names that fit the regex but belong elsewhere (a credit union, a nurses' union under health care)
    rx, nx = re.compile(w["rx"], re.I), re.compile(w["not"], re.I) if w.get("not") else None
    hit = lambda s: bool(rx.search(s)) and not (nx and nx.search(s))
    pm = [p for p in out["pacs"] if hit(p["name"])]
    # fec.watchFull: match every donor employer and list every matching PAC and employer (default: top 60 employers, 12 listed)
    em = [e for e in (emp_all if FEC.get("watchFull") else out.get("employers", [])) if hit(e["name"])]
    cap = None if FEC.get("watchFull") else 12
    watch.append({"id": w["id"], "label": w["label"], "why": w["why"],
                  "pacTotal": round(sum(p["amount"] for p in pm), 2), "empTotal": round(sum(e["total"] for e in em), 2),
                  "pacs": [{"name": p["name"], "id": p["id"], "amount": p["amount"], "byCycle": p["byCycle"]} for p in pm[:cap]],
                  "employers": [{"name": e["name"], "total": e["total"], "byCycle": e["byCycle"]} for e in em[:cap]]})
out["watch"] = watch
out["ids"] = {"member": M["name"], "candidateId": FEC["candidateId"], "committeeId": FEC["committeeId"]}
json.dump(out, open(SUMMARY, "w"), indent=1)
print("watch:", [(w["id"], w["pacTotal"], w["empTotal"]) for w in watch])
