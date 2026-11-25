"""Builds data/cards.json: the evidence cards behind the Stances page's "big questions" (ICE, police, corporate).

Each item points one way. For roll calls the side follows from her recorded vote (data/votes.json) and which side a
Yea is on, so a vote can't be put on the wrong side by hand. Headlines come from the rules below, stated on each
card. The Overview reads its ICE, police and corporate tiles from this file, so the two pages can't disagree.
Usage: python3 -I scripts/build_cards.py   (after build_stances.py and build_establishment.py)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT

load = lambda p: json.load(open(os.path.join(ROOT, p)))
picks, votes, stm, st = load("data/card_picks.json"), load("data/votes.json"), load("data/statements.json"), load("data/stances.json")
calc = load("data/fec/establishment_calc.json")
by = {f'{v["y"]}-{v["n"]:03d}': v for v in votes}
iss = {i["id"]: i for i in st["issues"]}
problems = []
usd = lambda x: f"${round(x):,}"
money = {"corp24": usd(calc["2024"]["cat"].get("corporate", 0)), "corp26": usd(calc["2026"]["cat"].get("corporate", 0)),
         "ncorp24": calc["2024"]["ncorp"], "ncorp26": calc["2026"]["ncorp"],
         "trade24": usd(calc["2024"]["cat"].get("trade", 0)), "trade26": usd(calc["2026"]["cat"].get("trade", 0)),
         "labor26": usd(calc["2026"]["cat"].get("labor", 0))}

def release(sub):
    hits = [s for s in stm if sub in s["u"]]
    if len(hits) != 1: problems.append(f"release {sub!r} matched {len(hits)}"); return None
    return hits[0]["u"]

def roll_item(rid, yea_side, what, title=None):
    v = by.get(rid)
    if not v: problems.append(f"roll {rid} not found"); return None
    if v["member"] not in ("Yea", "Nay"): return None             # no stance taken
    side = yea_side if v["member"] == "Yea" else ("con" if yea_side == "pro" else "pro")
    brk = v["dSide"] in ("Yea", "Nay") and v["member"] != v["dSide"]
    text = f"Voted {v['member']} on {what or title}. It {'passed' if v['result'].startswith('Pass') else 'failed'} {v['yea']}–{v['nay']}; Democrats {v['dY']}–{v['dN']}."
    return {"d": v["date"][:7], "s": side, "t": text, "u": f"https://clerk.house.gov/Votes/{v['y']}{v['n']:03d}", "brk": brk}

cards = []
for c in picks["cards"]:
    items = []
    if c.get("rollsFromIssue"):
        for r in iss[c["rollsFromIssue"]]["rolls"]:
            it = roll_item(r["id"], c.get("issueYeaOverrides", {}).get(r["id"], c["issueYea"]), None, f"{r['bill']}, {r['title']}")
            if it: items.append(it)
    for r in c.get("rolls", []):
        it = roll_item(r["roll"], r["yea"], r["t"])
        if it: items.append(it)
    for it in c["items"]:
        out = {"d": it["d"], "s": it["s"], "t": it["t"].format(**money), "hi": it.get("hi", 0)}
        if "stmt" in it:
            out["u"] = release(it["stmt"]); out["more"] = [u for u in (release(m) for m in it.get("more", [])) if u]
        else:
            out["u"] = "money.html#pacs"
        items.append(out)
    pro = [i for i in items if i["s"] == "pro"]; con = [i for i in items if i["s"] == "con"]
    pv = [i for i in pro if "clerk.house.gov" in i["u"]]; cv = [i for i in con if "clerk.house.gov" in i["u"]]
    # Headline rules, one per card, stated on the card
    if c["key"] == "ice":
        v = "No" if not pro else ("Mostly no" if len(con) >= 3 * len(pro) else "Mixed")
        rule = f"\"No\" when nothing found in her record points toward ICE: {len(cv)} votes and {len(con) - len(cv)} statements and actions point the other way."
    elif c["key"] == "police":
        v = "Mixed" if min(len(pv), len(cv)) >= 3 else ("Mostly yes" if len(pv) > len(cv) else "Mostly no")
        rule = f"\"Mixed\" when at least 3 picked votes point each way. She cast {len(pv)} on the police or tough-on-crime side and {len(cv)} against."
    else:
        v = "Mostly no" if pv == [] and pro else ("No" if not pro else "Mixed")
        rule = f"Her votes decide the headline: all {len(cv)} business, finance and labor votes picked went the consumer or labor way. It is \"Mostly no\" rather than \"No\" because corporate PAC money to her campaign roughly tripled."
    items.sort(key=lambda i: i["d"], reverse=True)
    cards.append({"key": c["key"], "q": c["q"], "eb": c["eb"], "v": v, "rule": rule, "pro": c["pro"], "con": c["con"],
                  "section": c["section"], "items": items, "n": len(items), "npro": len(pro), "ncon": len(con)})
    print(f"{c['q']:<16} {v:<10} pro {len(pro)} / con {len(con)}  ({len(pv)}/{len(cv)} votes)")
if problems: raise SystemExit("\n".join(problems))
json.dump({"cards": cards}, open(os.path.join(ROOT, "data/cards.json"), "w"), indent=1, ensure_ascii=False)
