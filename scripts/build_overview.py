"""Builds data/overview.json for the Overview page: quick-verdict tiles and constituent events.

Every verdict is computed from data already in the project, with the rule that produced it written next to it:
data/stances.json, data/votes.json, data/statements.json + statements_full.json, data/promises_built.json.
The "Establishment Democrat?" tile is read by the page straight from data/establishment.json (owned by the
Establishment build), so it is not computed here. The build stops if a reference can't be resolved.
Usage: python3 -I scripts/build_overview.py   (run after build_stances.py, build_promises.py and build_cards.py)
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT, M

load = lambda p: json.load(open(os.path.join(ROOT, p)))
st, votes, stm, full = load("data/stances.json"), load("data/votes.json"), load("data/statements.json"), load("data/statements_full.json")
prom, ev = load("data/promises_built.json"), load("data/events.json")
by = {f'{v["y"]}-{v["n"]:03d}': v for v in votes}
iss = {i["id"]: i for i in st["issues"]}
problems = []

def release(sub):
    hits = [s for s in stm if sub in s["u"]]
    if len(hits) != 1: problems.append(f"release {sub!r} matched {len(hits)}"); return None
    return hits[0]

tiles = []
# 1. Israel / Palestine: the Stances card's own headline
isr = st["israel"]
tiles.append({"q": isr["question"], "v": isr["headline"], "href": "stances.html#israel-palestine",
              "rule": "The headline of the Israel and Palestine card, which tags each of its items by direction.",
              "n": len(isr["items"])})

# 2-3a. ICE, police and corporate: read from the Stances evidence cards (data/cards.json) so the two pages agree
cards = {c["key"]: c for c in load("data/cards.json")["cards"]}
for key in ("ice", "police", "corporate"):
    c = cards[key]
    tiles.append({"q": c["q"], "v": c["v"], "href": f"stances.html#card-{key}", "rule": c["rule"], "n": c["n"]})

# 4-6. Member-specific tiles, from tracker.config.json "overview" (see its _note):
#   costPromise: start of the promise "issue" whose scorecard status answers "Delivering on cost of living?" (null: no tile)
#   costPledge: how the tile's rule names that pledge (default "cost-of-living")
#   themes: [{"q", "rx", "section", "noun", "note"}]: how often press releases mention a topic (under 10% = not a major theme);
#           the optional note is added after the rule
#   votes:  [{"q", "roll", "section", "what"}]: one recorded vote
from config import CFG
OV = CFG.get("overview", {})
PR = M.get("pronouns") or {"poss": "their"}
LAB = {"delivered": "Delivered", "progress": "In progress", "stalled": "Stalled", "contradicted": "Contradicted", "none": "No action found"}
CP = OV.get("costPromise", "Economic opportunity")   # null or "" turns the tile off
pc = next((p for p in prom["promises"] if p["issue"].startswith(CP)), None) if CP else None
if pc:
    tiles.append({"q": "Delivering on cost of living?", "v": LAB[pc["status"]], "href": "#scorecard",
                  "rule": f"The promise scorecard's status for {PR['poss']} {OV.get('costPledge') or 'cost-of-living'} pledge. " + pc["why"], "n": len(pc["actions"])})
for t in OV.get("themes", []):
    rx = re.compile(t["rx"], re.I)
    hm = [s for s in stm if rx.search(s["title"] + " " + full.get(s["u"], ""))]
    share = len(hm) / len(stm)
    tiles.append({"q": t["q"], "v": "Not a major theme" if share < 0.10 else "A recurring theme", "href": f"stances.html#{t['section']}",
                  "rule": f"{len(hm)} of {PR['poss']} {len(stm)} press releases ({share:.0%}) mention {t['noun']} at all; under 10% counts as not a major theme." + (f" {t['note']}" if t.get("note") else ""),
                  "n": len(hm)})
for t in OV.get("votes", []):
    ep = by[t["roll"]]
    tiles.append({"q": t["q"], "v": "Voted yes" if ep["member"] == "Yea" else ("Voted no" if ep["member"] == "Nay" else ep["member"]),
                  "href": f"stances.html#{t['section']}",
                  "rule": f"{PR['poss'].capitalize()} vote on {t['what']}, which {'passed' if ep['result'].lower().startswith(('pass', 'agreed', 'bill passed')) else 'ended'} {ep['yea']}–{ep['nay']} (roll {t['roll']}).",
                  "n": 1})
# The Establishment tile is drawn by index.html itself from data/establishment.json (headline and 'why'), so it isn't added here.

events = []
for e in ev["events"]:
    u = e.get("u")
    if "stmt" in e:
        s = release(e["stmt"]); u = s["u"] if s else None
    if not u: continue
    events.append({k: e[k] for k in ("date", "type", "role", "title") if k in e} | {k: e[k] for k in ("approx", "city", "notes") if k in e} | {"source": u})
if problems: raise SystemExit("\n".join(problems))
json.dump({"tiles": tiles, "events": events}, open(os.path.join(ROOT, "data/overview.json"), "w"), indent=1, ensure_ascii=False)
for t in tiles: print(f"{t['q']:<32} {t['v']:<20} n={t['n']}")
print(len(events), "events")
