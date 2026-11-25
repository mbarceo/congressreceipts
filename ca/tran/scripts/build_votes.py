"""Builds data/votes.json: Rep. Derek Tran's vote on every House roll call in data/raw.

Usage: python3 -I scripts/build_votes.py
"""
import glob, json, os, re
import xml.etree.ElementTree as ET
from datetime import datetime

TRAN = "T000491"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
out = []

for path in sorted(glob.glob(os.path.join(ROOT, "data/raw/*-roll*.xml"))):
    year = int(os.path.basename(path)[:4])
    t = ET.parse(path).getroot()
    m = t.find("vote-metadata")
    g = lambda k: (m.findtext(k) or "").strip()
    vote = None
    for rv in t.iter("recorded-vote"):
        leg = rv.find("legislator")
        if leg is not None and leg.get("name-id") == TRAN:
            vote = (rv.findtext("vote") or "").strip()
    party = {}
    for tp in m.iter("totals-by-party"):
        p = (tp.findtext("party") or "").strip()
        party[p] = {k: int(tp.findtext(k) or 0) for k in ("yea-total", "nay-total", "present-total", "not-voting-total")}
    tot = m.find(".//totals-by-vote")
    yea = int(tot.findtext("yea-total") or 0) if tot is not None else 0
    nay = int(tot.findtext("nay-total") or 0) if tot is not None else 0
    d = party.get("Democratic", {})
    r = party.get("Republican", {})
    # Majority position of each party (only for Yea/Nay votes)
    def side(x):
        if not x: return ""
        return "Yea" if x["yea-total"] > x["nay-total"] else ("Nay" if x["nay-total"] > x["yea-total"] else "Split")
    dside, rside = side(d), side(r)
    # Normalize "Aye"/"No" to Yea/Nay
    norm = {"Aye": "Yea", "No": "Nay"}.get(vote, vote)
    out.append({
        "y": year,
        "n": int(g("rollcall-num")),
        "date": datetime.strptime(g("action-date"), "%d-%b-%Y").strftime("%Y-%m-%d"),
        "bill": re.sub(r"\s+", " ", g("legis-num")),
        "q": g("vote-question"),
        "desc": g("vote-desc"),
        "type": g("vote-type"),
        "result": g("vote-result"),
        "yea": yea, "nay": nay,
        "dY": d.get("yea-total", 0), "dN": d.get("nay-total", 0),
        "rY": r.get("yea-total", 0), "rN": r.get("nay-total", 0),
        "dSide": dside, "rSide": rside,
        "tran": norm or "Not in record",
    })

out.sort(key=lambda v: (v["y"], v["n"]))
with open(os.path.join(ROOT, "data/votes.json"), "w") as f:
    f.write("[\n" + ",\n".join(json.dumps(v, ensure_ascii=False) for v in out) + "\n]\n")
print(len(out), "roll calls written")
