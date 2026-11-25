"""Builds data/cards.json: the evidence cards behind the Stances page's "big questions" (ICE, police, corporate).

Each item points one way. For roll calls the side follows from her recorded vote (data/votes.json) and which side a
Yea is on, so a vote can't be put on the wrong side by hand. Headlines come from the rules below, stated on each
card. The Overview reads its ICE, police and corporate tiles from this file, so the two pages can't disagree.
Usage: python3 -I scripts/build_cards.py   (after build_stances.py and build_establishment.py)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT, M
from votes_common import is_vote_url
PR = M.get("pronouns") or {"subj": "they", "obj": "them", "poss": "their"}
SUBJ, POSS = PR["subj"].capitalize(), PR["poss"]

load = lambda p: json.load(open(os.path.join(ROOT, p)))
picks, votes, stm, st = load("data/card_picks.json"), load("data/votes.json"), load("data/statements.json"), load("data/stances.json")
calc = load("data/fec/establishment_calc.json")
by = {f'{v["y"]}-{v["n"]:03d}': v for v in votes}
iss = {i["id"]: i for i in st["issues"]}
problems = []
usd = lambda x: f"${round(x):,}"
# Money placeholders for card text, one set per FEC cycle: {corp24} {ncorp24} {trade24} {labor24}, {corp26} ...
# plus {corpCur}/{corpPrev} etc. for the latest and previous cycle, so cards work for any cycles in fec.cycles.
money, cyc = {}, sorted(calc, key=int)
for c in cyc:
    cat = calc[c]["cat"]
    money.update({f"corp{c[2:]}": usd(cat.get("corporate", 0)), f"ncorp{c[2:]}": calc[c].get("ncorp", 0),
                  f"trade{c[2:]}": usd(cat.get("trade", 0)), f"labor{c[2:]}": usd(cat.get("labor", 0))})
for tag, c in (("Cur", cyc[-1]), ("Prev", cyc[-2] if len(cyc) > 1 else None)):
    if c: money.update({k[:-2] + tag: v for k, v in list(money.items()) if k.endswith(c[2:]) and not k.endswith(("Cur", "Prev"))})

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
    return {"d": v["date"][:7], "s": side, "t": text, "u": v["url"], "brk": brk}

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
        if "bill" in it:   # "bill": "118-s4991" (Congress-number): links congress.gov; list it in data/bills.json so verify_bills.py checks the role
            bc, bn = it["bill"].split("-") if "-" in it["bill"] else ("119", it["bill"])
            bt = "".join(ch for ch in bn if ch.isalpha()); slug = {"s": "senate-bill", "hr": "house-bill", "sres": "senate-resolution", "hres": "house-resolution",
                "sjres": "senate-joint-resolution", "hjres": "house-joint-resolution", "sconres": "senate-concurrent-resolution", "hconres": "house-concurrent-resolution"}[bt]
            ordc = f"{bc}{'th' if 10 <= int(bc) % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(int(bc) % 10, 'th')}"
            out["u"] = f"https://www.congress.gov/bill/{ordc}-congress/{slug}/{bn[len(bt):]}"
            out["more"] = it.get("more", [])
        elif "u" in it:
            out["u"] = it["u"]
        elif "stmt" in it:
            out["u"] = release(it["stmt"]); out["more"] = [u for u in (release(m) for m in it.get("more", [])) if u]
        else:
            out["u"] = "money.html#pacs"
        items.append(out)
    pro = [i for i in items if i["s"] == "pro"]; con = [i for i in items if i["s"] == "con"]
    pv = [i for i in pro if is_vote_url(i["u"])]; cv = [i for i in con if is_vote_url(i["u"])]
    other = lambda xs, vs: len(xs) - len(vs)
    nv = lambda n: f"{n} vote" + ("" if n == 1 else "s")
    # Headline rules, one per card, stated on the card
    if c["key"] == "ice":
        v = "No" if not pro else ("Mostly no" if len(con) >= 3 * len(pro) else "Mixed")
        rule = (f"\"No\" when nothing found in {POSS} record points toward ICE; \"Mostly no\" when at least three times as many items point "
                f"the other way. Toward enforcement: {nv(len(pv))} and {other(pro, pv)} statements or actions. Against: {nv(len(cv))} and {other(con, cv)} statements or actions.")
    elif c["key"] == "police" and c.get("countAll"):
        # Whole record: votes, bills and funding each count as one item
        v = "Mixed" if min(len(pro), len(con)) >= 3 else ("Mostly yes" if len(pro) > len(con) else "Mostly no")
        rule = (f"\"Mixed\" when at least 3 items point each way, counting votes, bills and funding. On the police side: {nv(len(pv))} and "
                f"{other(pro, pv)} bills, resolutions or funding items. On the reform side: {nv(len(cv))} and {other(con, cv)} bills or statements.")
    elif c["key"] == "police":
        v = "Mixed" if min(len(pv), len(cv)) >= 3 else ("Mostly yes" if len(pv) > len(cv) else "Mostly no")
        rule = f"\"Mixed\" when at least 3 picked votes point each way. {SUBJ} cast {len(pv)} on the police or tough-on-crime side and {len(cv)} against."
    else:
        share = len(pv) / (len(pv) + len(cv)) if pv or cv else 0
        v = ("Mostly no" if pro else "No") if not pv else ("Mostly no" if share <= 1/3 else "Mostly yes" if share >= 2/3 else "Mixed")
        rule = (f"{POSS.capitalize()} votes decide the headline: {len(pv)} of the {len(pv) + len(cv)} business, finance and labor votes picked went the business way "
                f"(a third or fewer is \"Mostly no\", two thirds or more \"Mostly yes\")."
                + (f" With none, it is \"Mostly no\" rather than \"No\" because other items, such as corporate PAC money, point the business way." if not pv and pro else ""))
    items.sort(key=lambda i: i["d"], reverse=True)
    cards.append({"key": c["key"], "q": c["q"], "eb": c["eb"], "v": v, "rule": rule, "pro": c["pro"], "con": c["con"],
                  "section": c["section"], "items": items, "n": len(items), "npro": len(pro), "ncon": len(con)})
    print(f"{c['q']:<16} {v:<10} pro {len(pro)} / con {len(con)}  ({len(pv)}/{len(cv)} votes)")
if problems: raise SystemExit("\n".join(problems))
json.dump({"cards": cards}, open(os.path.join(ROOT, "data/cards.json"), "w"), indent=1, ensure_ascii=False)
