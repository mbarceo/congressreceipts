"""Builds data/allegiance.json for Republican members: the Allegiance page, which replaces Establishment.

Four axes, each from a primary source:
  leadership  agreement with the party leader and party unity (data/establishment.json, data/alignment.json) and money
              from the leader's committees, the NRCC and Trump's committees (data/fec/leadership.json)
  trump       roll calls where Trump's position is documented (data/allegiance_items.json "trump.picks"; each pick
              cites the White House statement or Trump's own post). The member's vote and every tally come from votes.json
  jan6        the two Jan. 6, 2021 objections to the 2020 count (House Clerk roll calls 2021-010 Arizona and 2021-011
              Pennsylvania), read from the Clerk's XML; shown only for members who served then
  mandate     votes and bills matched to a cited page of the Mandate for Leadership ("mandate.items"), plus the
              Heritage Action scorecard figure when it has been recorded ("mandate.heritageAction")
Numbers in {braces} in allegiance_items.json are filled here; never type a number there. The headline is an editorial
call under the rule in "why"; it stays "TBD" (shown as "Coming soon") until the evidence is in.
Run after build_votes, build_alignment, build_establishment. Usage: python3 -I scripts/build_allegiance.py
"""
import json, os, sys, urllib.request
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, ROOT
from votes_common import MY_ID, LEADER, OWN, OWN_NAME

if OWN != "R": raise SystemExit("build_allegiance.py is for Republican members; Democrats use build_establishment.py")
J = lambda p, d=None: json.load(open(os.path.join(ROOT, p))) if os.path.exists(os.path.join(ROOT, p)) else d
items = J("data/allegiance_items.json")
if not items: raise SystemExit("data/allegiance_items.json missing")
votes = {f"{v['y']}-{v['n']:03d}": v for v in J("data/votes.json", [])}
est = J("data/establishment.json", {})
al = J("data/alignment.json", {})
problems = []

# ---- Jan. 6, 2021 objections: official Clerk roll calls, read straight from the XML ----
JAN6 = [("2021-010", "Arizona", "https://clerk.house.gov/evs/2021/roll010.xml", "https://clerk.house.gov/Votes/202110"),
        ("2021-011", "Pennsylvania", "https://clerk.house.gov/evs/2021/roll011.xml", "https://clerk.house.gov/Votes/202111")]
jan6 = []
for rid, state, xml_url, page in JAN6:
    try:
        req = urllib.request.Request(xml_url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=60).read())
    except Exception as e:
        problems.append(f"Jan 6 roll {rid}: could not read the Clerk XML ({e})"); continue
    meta = root.find("vote-metadata"); tot = {"Yea": 0, "Nay": 0}
    mine = None
    for rv in root.iter("recorded-vote"):
        leg = rv.find("legislator"); v = (rv.findtext("vote") or "").strip()
        v = {"Aye": "Yea", "No": "Nay"}.get(v, v)
        if v in tot: tot[v] += 1
        if leg.get("name-id") == MY_ID: mine = v
    jan6.append({"id": rid, "state": state, "question": (meta.findtext("vote-question") or "").strip(), "date": (meta.findtext("action-date") or "").strip(),
                 "result": (meta.findtext("vote-result") or "").strip(), "yea": tot["Yea"], "nay": tot["Nay"], "vote": mine or "Not in record",
                 "url": page, "xml": xml_url})
objected = sum(1 for j in jan6 if j["vote"] == "Yea")
served = [j for j in jan6 if j["vote"] != "Not in record"]

# ---- Trump-position votes: Trump's documented position, the member's recorded vote ----
trump_rows = []
for p in items.get("trump", {}).get("picks", []):
    v = votes.get(p["roll"])
    if not v: problems.append(f"trump pick {p['roll']}: not in votes.json"); continue
    pos = p["trump"]                       # Trump's position expressed as the Yea/Nay he wanted on this question
    me = v["member"]
    status = "missed" if me in ("Not Voting", "Not in record") else "present" if me == "Present" else "with" if me == pos else "against"
    want = pos; r_with = v["rY"] if want == "Yea" else v["rN"]; r_against = v["rN"] if want == "Yea" else v["rY"]
    trump_rows.append({"rAgainst": r_against, "rTot": r_with + r_against, "quote": p.get("quote", ""), "must": p.get("must", []), "id": p["roll"], "date": v["date"], "bill": v["bill"], "q": v["q"], "title": v["desc"] or v["q"], "topic": p.get("topic", ""),
                       "trump": pos, "vote": me, "status": status, "result": v["result"], "yea": v["yea"], "nay": v["nay"],
                       "pY": v.get("pY", v["dY"]), "pN": v.get("pN", v["dN"]), "url": v["url"], "source": p["source"], "note": p.get("note", "")})
trump_rows.sort(key=lambda r: r["date"], reverse=True)
cast = [r for r in trump_rows if r["status"] in ("with", "against")]
with_t = sum(1 for r in cast if r["status"] == "with")

# ---- Mandate for Leadership matches ----
mandate_rows = []
for it in items.get("mandate", {}).get("items", []):
    row = {k: it[k] for k in ("proposal", "page", "quote", "kind", "source", "match", "bill", "billUrl", "billMust") if k in it}
    if it.get("roll"):
        v = votes.get(it["roll"])
        if not v: problems.append(f"mandate item {it['roll']}: not in votes.json"); continue
        row.update({"roll": it["roll"], "vote": v["member"], "result": v["result"], "yea": v["yea"], "nay": v["nay"], "date": v["date"], "url": v["url"], "q": v["q"]})
    mandate_rows.append(row)
ha = items.get("mandate", {}).get("heritageAction") or {}

# AUTO headline: the rule stated in items["rule"], applied identically to every member
pct = 100 * with_t / len(cast) if cast else None
broke = [r for r in cast if r["rAgainst"] >= 10]
if items["headline"] == "AUTO":
    if not cast: items["headline"] = "TBD"
    elif pct >= 95 and all(r["status"] == "with" for r in broke): items["headline"] = "Reliably with Trump"
    elif pct >= 80: items["headline"] = "Mostly with Trump"
    else: items["headline"] = "Often against Trump"
nums = {"jan6n": len(served), "jan6obj": objected,
        "trumpN": len(cast), "trumpWith": with_t, "trumpAgainst": len(cast) - with_t,
        "trumpPct": f"{100 * with_t / len(cast):.0f}" if cast else None,
        "mandateN": sum(1 for r in mandate_rows if r.get("vote") in ("Yea", "Nay")),
        "mandateYea": sum(1 for r in mandate_rows if r.get("vote") == "Yea"),
        "haScore": ha.get("score"),
        **{k: est.get("nums", {}).get(k) for k in ("jeffAgree", "both", "ndiff", "leaderName", "unity", "rank", "dems", "contested", "jeffC")},
        **{k: v for k, v in est.get("nums", {}).items() if k.startswith(("lead", "nrcc", "trump"))}}
nums = {k: v for k, v in nums.items() if v is not None}
class Safe(dict):
    def __missing__(self, k): problems.append(f"no value for {{{k}}}"); return "{" + k + "}"
fill = lambda s: str(s).format_map(Safe(nums))

out = {"question": items["question"], "headline": items["headline"], "rule": items.get("rule", ""), "why": fill(items.get("why", "")),
       "summary": fill(items.get("summary", "")), "tiles": [[fill(a), fill(b)] for a, b in items.get("tiles", [])],
       "leader": {"name": LEADER["name"], "title": LEADER.get("title", ""), "agree": est.get("nums", {}).get("jeffAgree"), "both": est.get("nums", {}).get("both"),
                  "splits": est.get("nums", {}).get("ndiff"), "unity": al.get("memberUnity"), "rank": al.get("memberRank"), "tied": al.get("memberTied", 0),
                  "ofParty": al.get("dems"), "medianUnity": al.get("medianUnity"), "contested": al.get("contested"),
                  "peers": al.get("peers", []), "diffs": est.get("jeffriesDiffs", [])},
       "money": {"leaders": est.get("leaders", []), "cycles": est.get("cycles", []), "section": est.get("leaderSection", {}),
                 "categories": est.get("categories", {})},
       "trump": {"intro": fill(items.get("trump", {}).get("intro", "")), "rows": trump_rows, "with": with_t, "cast": len(cast),
                 "missed": sum(1 for r in trump_rows if r["status"] == "missed")},
       "jan6": {"intro": fill(items.get("jan6", {}).get("intro", "")), "rows": jan6, "served": len(served), "objected": objected},
       "mandate": {"intro": fill(items.get("mandate", {}).get("intro", "")), "rows": mandate_rows, "heritageAction": ha,
                   "disavowal": items.get("mandate", {}).get("disavowal", {})},
       "maga": [{**x, "text": fill(x["text"])} for x in items.get("maga", {}).get("items", [])],
       "signs": {k: [{**s, "text": fill(s["text"])} for s in v] for k, v in items.get("signs", {}).items()},
       "timeline": sorted(({**e, "text": fill(e["text"])} for e in items.get("timeline", [])), key=lambda e: e["d"], reverse=True),
       "nums": nums}
json.dump(out, open(os.path.join(ROOT, "data/allegiance.json"), "w"), indent=1, ensure_ascii=False)
print("allegiance.json:", out["headline"], "|", nums)
for p in problems: print("PROBLEM:", p)
if problems: sys.exit(1)
