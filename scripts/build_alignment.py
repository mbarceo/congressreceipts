"""Builds data/alignment.json: how often the member votes with selected colleagues.

Reads roll calls through votes_common (House or Senate). Agreement counts only roll calls where both
members voted Yea or Nay. Party unity, the unity ranking and "contested" votes use the Democratic caucus:
Democrats plus independents listed in votes_common.CAUCUS (Senate: Sanders, King). A member is ranked only with
at least votes_common.unity_min_votes() party-side votes (House 200; Senate half of the caucus's side-taking roll calls).
Usage: python3 -I scripts/build_alignment.py
"""
import json, os, re
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC, need
from votes_common import load_rolls, MY_ID, caucus, party_side, unity_min_votes

ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
TRAN = MY_ID   # bioguide (House) or LIS id (Senate)
PEERS = [(p["id"], p["name"], p.get("dist", ""), p["group"]) for p in CFG["peers"]]
ISRAEL = re.compile(r"israel|iran|gaza|hamas|antisemit|hezbollah|international criminal court|illegitimate court|jewish|palestin", re.I)

rolls = [{"votes": r["votes"], "party": r["party"], "id": r["id"],
          "israel": bool(ISRAEL.search(r["desc"] + " " + r["bill"]))} for r in load_rolls()]

def agree(a, b, subset=None):
    same = tot = 0
    for r in rolls:
        if subset and not subset(r): continue
        va, vb = r["votes"].get(a), r["votes"].get(b)
        if va in ("Yea", "Nay") and vb in ("Yea", "Nay"):
            tot += 1; same += va == vb
    return same, tot

def dem_side(r):
    side, y, n = party_side(r, "D", by_caucus=True)
    return side, min(y, n) / max(1, y + n)

# Party unity for every member of the Democratic caucus: share of Yea/Nay votes cast with the caucus majority
sides = [dem_side(r) for r in rolls]
dems = {k for r in rolls for k in r["party"] if caucus(r, k) == "D"}
MIN_VOTES = unity_min_votes(sum(1 for s, _ in sides if s))
unity = {}
for d in dems:
    same = tot = 0
    for r, (side, _) in zip(rolls, sides):
        v = r["votes"].get(d)
        if side and v in ("Yea", "Nay"):
            tot += 1; same += v == side
    if tot >= MIN_VOTES: unity[d] = same / tot
ranked = sorted(unity, key=lambda k: -unity[k])
contested = lambda r, s=dict(zip([x["id"] for x in rolls], sides)): s[r["id"]][1] >= 0.10

out = {"memberUnity": round(unity[TRAN] * 100, 1), "memberRank": 1 + sum(1 for k in ranked if unity[k] > unity[TRAN]),  # ties share a rank
       "memberTied": sum(1 for k in ranked if unity[k] == unity[TRAN]) - 1, "dems": len(ranked),
       "medianUnity": round(sorted(unity.values())[len(unity) // 2] * 100, 1),
       "rolls": len(rolls), "contested": sum(1 for r in rolls if contested(r)),
       "israelRolls": sum(1 for r in rolls if r["israel"]), "peers": []}
for pid, name, dist, group in PEERS:
    s, t = agree(TRAN, pid); cs, ct = agree(TRAN, pid, contested); is_, it = agree(TRAN, pid, lambda r: r["israel"])
    out["peers"].append({"id": pid, "name": name, "dist": dist, "group": group,
                         "all": round(100 * s / t, 1) if t else None, "n": t,
                         "contested": round(100 * cs / ct, 1) if ct else None, "nc": ct,
                         "israel": round(100 * is_ / it, 1) if it else None, "ni": it,
                         "unity": round(unity[pid] * 100, 1) if pid in unity else None})
json.dump(out, open(os.path.join(ROOT, "data/alignment.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "peers"}))
for p in out["peers"]:
    print(f'{p["name"]:26} all {p["all"]}% ({p["n"]})  contested {p["contested"]}% ({p["nc"]})  israel {p["israel"]}% ({p["ni"]})  unity {p["unity"]}')
