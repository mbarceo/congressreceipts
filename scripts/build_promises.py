"""Builds data/promises_built.json for the Overview's promise scorecard from data/promises.json.

Each action either names a roll call (her vote and the tally are filled from data/votes.json, so they can't be
mistyped), a press release (must match exactly one entry in data/statements.json), or another source URL.
The build stops if any reference can't be resolved. Usage: python3 -I scripts/build_promises.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT
from votes_common import roll_phrases, fill_text

load = lambda p: json.load(open(os.path.join(ROOT, p)))
data, votes, stm = load("data/promises.json"), load("data/votes.json"), load("data/statements.json")
by = {f'{v["y"]}-{v["n"]:03d}': v for v in votes}
problems = []
STATUSES = {"delivered", "progress", "stalled", "contradicted", "none"}

def release(sub):
    hits = [s for s in stm if sub in s["u"]]
    if len(hits) != 1: problems.append(f"release {sub!r} matched {len(hits)} entries"); return None
    return hits[0]["u"]

sources = {}
for k, s in data["sources"].items():
    sources[k] = {"label": s["label"], "u": release(s["stmt"]) if "stmt" in s else s["u"]}

out = []
for p in data["promises"]:
    if p["status"] not in STATUSES: problems.append(f"{p['issue']}: bad status {p['status']}")
    if not p.get("why"): problems.append(f"{p['issue']}: status needs a 'why'")
    acts = []
    for a in p["actions"]:
        if "roll" in a:
            v = by.get(a["roll"])
            if not v: problems.append(f"{p['issue']}: roll {a['roll']} not found"); continue
            text = fill_text(a["text"], roll_phrases([v]), p["issue"], problems)   # {vote} {yea} {nay} {Vote} {DemMaj} ... (votes_common)
            acts.append({"text": text, "u": v["url"], "vote": v["member"]})
        elif "stmt" in a:
            u = release(a["stmt"])
            if u: acts.append({"text": a["text"], "u": u})
        else:
            acts.append({"text": a["text"], "u": a["u"]})
    out.append({**{k: p[k] for k in ("issue", "kind", "status", "promise", "quote", "why")},
                "src": [sources[s] for s in p["src"]], "actions": acts})
if problems: raise SystemExit("\n".join(problems))
json.dump({"noPromise": data["noPromise"], "promises": out}, open(os.path.join(ROOT, "data/promises_built.json"), "w"), indent=1, ensure_ascii=False)
for p in out: print(f"{p['status']:<10} {p['kind']:<8} {p['issue']} ({len(p['actions'])} actions)")
