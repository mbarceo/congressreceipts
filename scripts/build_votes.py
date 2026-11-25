"""Builds data/votes.json: the member's vote on every roll call in data/raw (House or Senate, from votes_common).

Party tallies are counted from individual members' votes, so House and Senate files give the same fields.
dY/dN/rY/rN follow the party letter in the official file. Senate rows add iY/iN (independents) and cY/cN (the
Democratic caucus: Democrats plus independents in votes_common.CAUCUS, e.g. Sanders and King). dSide/rSide are the
caucus's majority side, matching the party-unity math in build_alignment.py; on Senate pages show cY–cN beside dSide,
because on a close Democratic split the caucus side can differ from the dY–dN majority.
Usage: python3 -I scripts/build_votes.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT
from votes_common import load_rolls, party_side, MY_ID, CHAMBER

def side(r, party):
    s, y, n = party_side(r, party, by_caucus=True)
    if y + n == 0: return ""          # no Yea/Nay votes from this caucus (quorum calls, Speaker elections)
    return s or "Split"

out = []
for r in load_rolls():
    _, dY, dN = party_side(r, "D"); _, rY, rN = party_side(r, "R")
    row = {"y": r["y"], "n": r["n"], "date": r["date"], "bill": r["bill"], "q": r["q"], "desc": r["desc"],
           "type": r["type"], "result": r["result"],
           "yea": sum(1 for v in r["votes"].values() if v == "Yea"), "nay": sum(1 for v in r["votes"].values() if v == "Nay"),
           "dY": dY, "dN": dN, "rY": rY, "rN": rN}
    if CHAMBER == "senate":   # independents, and the Democratic caucus tally that dSide is computed from
        _, row["iY"], row["iN"] = party_side(r, "I")
        _, row["cY"], row["cN"] = party_side(r, "D", by_caucus=True)
    row.update({"dSide": side(r, "D"), "rSide": side(r, "R"), "member": r["votes"].get(MY_ID) or "Not in record", "url": r["url"]})
    out.append(row)
with open(os.path.join(ROOT, "data/votes.json"), "w") as f:
    f.write("[\n" + ",\n".join(json.dumps(v, ensure_ascii=False) for v in out) + "\n]\n")
print(len(out), "roll calls written")
