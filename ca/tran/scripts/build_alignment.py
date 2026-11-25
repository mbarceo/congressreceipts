"""Builds data/alignment.json: how often Rep. Tran votes with selected House members.

Reads House Clerk roll-call XML in data/raw. Agreement counts only roll calls where both
members voted Yea or Nay. Usage: python3 -I scripts/build_alignment.py
"""
import glob, json, os, re
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TRAN = "T000491"
PEERS = [  # (id, name, district, group)
    ("J000294", "Hakeem Jeffries", "NY-8", "Party leadership"),
    ("C001101", "Katherine Clark", "MA-5", "Party leadership"),
    ("A000371", "Pete Aguilar", "CA-33", "Party leadership"),
    ("G000583", "Josh Gottheimer", "NJ-5", "Centrist"),
    ("T000486", "Ritchie Torres", "NY-15", "Centrist"),
    ("G000592", "Jared Golden", "ME-2", "Centrist"),
    ("O000172", "Alexandria Ocasio-Cortez", "NY-14", "Progressive"),
    ("O000173", "Ilhan Omar", "MN-5", "Progressive"),
    ("T000481", "Rashida Tlaib", "MI-12", "Progressive"),
    ("C001131", "Greg Casar", "TX-35", "Progressive"),
    ("K000389", "Ro Khanna", "CA-17", "Progressive"),
    ("C001110", "Lou Correa", "CA-46", "Orange County neighbor"),
    ("M001241", "Dave Min", "CA-47", "Orange County neighbor"),
    ("K000397", "Young Kim", "CA-40", "Orange County neighbor"),
]
ISRAEL = re.compile(r"israel|iran|gaza|hamas|antisemit|hezbollah|international criminal court|illegitimate court|jewish|palestin", re.I)

rolls = []
for p in sorted(glob.glob(os.path.join(ROOT, "data/raw/*-roll*.xml"))):
    t = ET.parse(p).getroot()
    m = t.find("vote-metadata")
    votes, party = {}, {}
    for rv in t.iter("recorded-vote"):
        leg = rv.find("legislator")
        v = {"Aye": "Yea", "No": "Nay"}.get((rv.findtext("vote") or "").strip(), (rv.findtext("vote") or "").strip())
        votes[leg.get("name-id")] = v
        party[leg.get("name-id")] = leg.get("party")
    desc = (m.findtext("vote-desc") or "") + " " + (m.findtext("legis-num") or "")
    rolls.append({"votes": votes, "party": party, "israel": bool(ISRAEL.search(desc)),
                  "id": os.path.basename(p)[:4] + "-" + (m.findtext("rollcall-num") or "")})

def agree(a, b, subset=None):
    same = tot = 0
    for r in rolls:
        if subset and not subset(r): continue
        va, vb = r["votes"].get(a), r["votes"].get(b)
        if va in ("Yea", "Nay") and vb in ("Yea", "Nay"):
            tot += 1; same += va == vb
    return same, tot

def dem_side(r):
    y = sum(1 for k, v in r["votes"].items() if r["party"].get(k) == "D" and v == "Yea")
    n = sum(1 for k, v in r["votes"].items() if r["party"].get(k) == "D" and v == "Nay")
    return ("Yea" if y > n else "Nay" if n > y else None), min(y, n) / max(1, y + n)

# Party unity for every Democrat: share of Yea/Nay votes cast with the Democratic majority
sides = [dem_side(r) for r in rolls]
dems = {k for r in rolls for k, p in r["party"].items() if p == "D"}
unity = {}
for d in dems:
    same = tot = 0
    for r, (side, _) in zip(rolls, sides):
        v = r["votes"].get(d)
        if side and v in ("Yea", "Nay"):
            tot += 1; same += v == side
    if tot >= 200: unity[d] = same / tot
ranked = sorted(unity, key=lambda k: -unity[k])
contested = lambda r, s=dict(zip([x["id"] for x in rolls], sides)): s[r["id"]][1] >= 0.10

out = {"tranUnity": round(unity[TRAN] * 100, 1), "tranRank": 1 + sum(1 for k in ranked if unity[k] > unity[TRAN]), "dems": len(ranked),
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
