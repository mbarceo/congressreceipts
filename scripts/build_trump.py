"""Builds data/trump.json for ANY member, either party: how the member voted on the roll calls where the White House
stated a position (data/trump_positions.json, one selection rule shared by every tracker, see
scripts/build_trump_positions.py). Nothing here depends on the member's party except the "own party" tallies.

The headline stays "TBD" (shown as "Coming soon") until the maintainers approve a rule; the proposed rule is printed in
"why" so it is fixed in writing before anyone looks at a verdict.
Usage: python3 -I scripts/build_trump.py   (run for a member with ./tr <state>/<member> build_trump)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, ROOT
from votes_common import OWN_NAME

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if str(M.get("chamber", "house")).lower() == "senate":
    # The White House statements are matched to House roll calls only; Senate roll calls need their own pass (not built yet).
    print("skipped: the Trump section covers House members only so far; no data/trump.json written for a senator")
    sys.exit(0)
pos = json.load(open(os.path.join(REPO, "data/trump_positions.json")))
votes = {f'{v["y"]}-{v["n"]:03d}': v for v in json.load(open(os.path.join(ROOT, "data/votes.json")))}
rows, problems = [], []
for p in pos["counted"]:
    v = votes.get(p["roll"])
    if not v: problems.append(f"{p['roll']} not in votes.json"); continue
    me, want = v["member"], p["trump"]
    status = "missed" if me in ("Not Voting", "Not in record") else "present" if me == "Present" else "with" if me == want else "against"
    pY, pN = v.get("pY", v["dY"]), v.get("pN", v["dN"])           # the member's own party, official party letter
    rows.append({"id": p["roll"], "date": v["date"], "bill": v["bill"], "q": v["q"], "title": p["title"], "trump": want, "vote": me, "status": status,
                 "result": v["result"], "yea": v["yea"], "nay": v["nay"], "pY": pY, "pN": pN,
                 "ownAgainst": pN if want == "Yea" else pY, "ownTotal": pY + pN, "url": v["url"],
                 "statement": p["statement"], "statementUrl": p["url"], "quote": p["quote"], "truncated": p["truncated"]})
rows.sort(key=lambda r: r["date"], reverse=True)
cast = [r for r in rows if r["status"] in ("with", "against")]
with_t = sum(1 for r in cast if r["status"] == "with")
nums = {"trumpN": len(cast), "trumpWith": with_t, "trumpAgainst": len(cast) - with_t, "trumpPct": f"{100 * with_t / len(cast):.0f}" if cast else None,
        "trumpMissed": sum(1 for r in rows if r["status"] == "missed")}
RULE = ("Counts every House roll call on final disposition of a measure (passage, adopting a resolution, concurring in a Senate amendment, "
        "or suspending the rules and passing it) for which the White House issued a statement of administration policy that states a position on passage. "
        "Support means Trump wanted a Yea; opposition means a Nay. The rule applies to every member of either party; the votes that were examined but not counted, "
        "and why, are listed below.")
PROPOSED = ("Proposed headline thresholds, not yet approved: \"Reliably with Trump\" at 95% or more of counted votes cast with his position and with it on every vote where "
            "10 or more of the member's own party voted the other way; \"Mostly with Trump\" at 80% to 94%; \"Often against Trump\" below 80%. The headline stays \"Coming soon\" until these are approved.")
out = {"headline": "TBD", "rule": RULE, "why": PROPOSED, "examined": pos["examined"], "counted": len(pos["counted"]), "skipped": pos["skipped"],
       "ownParty": OWN_NAME, "rows": rows, "nums": nums, "sapIndex": pos["sapIndex"]}
json.dump(out, open(os.path.join(ROOT, "data/trump.json"), "w"), indent=1, ensure_ascii=False)
print(f"trump.json: {nums['trumpWith']} of {nums['trumpN']} cast with the White House position; {nums['trumpMissed']} missed; {len(pos['skipped'])} examined votes skipped")
for p in problems: print("PROBLEM:", p)
if problems: sys.exit(1)
