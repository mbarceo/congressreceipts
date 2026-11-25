"""Builds data/cards.json: the evidence cards behind the Stances page's big questions (palestine, ice, police, corporate).

Items come from data/card_picks.json in the order shown. For roll-call items, his vote, the vote wording, Democratic
tallies, the item's side, the "Breaks with party" pill and the date come from data/votes.json (key "tran"), so a vote
can't be typed wrong. Money figures come from data/fec/establishment_calc.json (corporate, trade, labor PACs),
data/fec/summary.json (pro-Israel money) and data/fec/raw (End Citizens United, AIPAC PAC), via placeholders.
palestine.js, ice.js, corporate.js and scripts/extract_claims.js read the output.
Usage: python3 -I scripts/build_cards.py
"""
import json, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
load = lambda p: json.load(open(os.path.join(ROOT, p)))
picks, votes = load("data/card_picks.json"), load("data/votes.json")
calc, summ = load("data/fec/establishment_calc.json"), load("data/fec/summary.json")
raw = {c: load(f"data/fec/raw/committee_contribs_{c}.json") for c in ("2024", "2026")}
by = {f'{v["y"]}{v["n"]}': v for v in votes}
problems = []
usd = lambda x: f"${round(x):,}"
CLERK = "https://clerk.house.gov/Votes/"

# ---- Money ----
def amt(rows, pred):
    return sum((r.get("contribution_receipt_amount") or 0) for r in rows if pred(r))
ecu = {c: amt(raw[c], lambda r: re.search(r"END CITIZENS UNITED", r.get("contributor_name") or "", re.I)) for c in raw}
aipac = amt(raw["2024"] + raw["2026"], lambda r: r.get("contributor_id") == "C00797670")
pro_isr = summ["cycles"]["all"]["slices"]["proisrael"]
jstreet = sum(p["amount"] for p in summ["pacs"] if p["proIsrael"] and "JSTREET" in p["name"].upper())
cat = lambda y, k: calc[y]["cat"].get(k, 0)
money = {"corp24": usd(cat("2024", "corporate")), "corp26": usd(cat("2026", "corporate")),
         "ncorp24": str(calc["2024"]["ncorp"]), "ncorp26": str(calc["2026"]["ncorp"]),
         "trade24": usd(cat("2024", "trade")), "trade26": usd(cat("2026", "trade")),
         "labor24": usd(cat("2024", "labor")), "labor26": usd(cat("2026", "labor")),
         "ecu24": usd(ecu["2024"]), "aipac": usd(aipac),
         "proisrael_about": usd(round(pro_isr, -4))}
# Wording the money text depends on
if round(ecu["2026"]) != 0: problems.append(f"End Citizens United gave {usd(ecu['2026'])} in 2025-26; corporate card says 'nothing'")
if jstreet < 0.9 * pro_isr: problems.append(f"J Street is {jstreet/pro_isr:.0%} of pro-Israel money; palestine card says 'almost all'")
if cat("2026", "trade") <= cat("2024", "trade"): problems.append("trade money did not go up; corporate card says 'up from'")

# ---- Votes ----
VOTE = {"Yea": "Voted for", "Nay": "Voted against", "Present": "Voted “Present” on", "Not Voting": "Did not vote on"}
def dmaj(v):
    hi, lo = max(v["dY"], v["dN"]), min(v["dY"], v["dN"])
    word = "no" if v["dN"] > v["dY"] else "yes" if v["dY"] > v["dN"] else None
    return (f"Most Democrats voted {word}" if word else "Democrats split"), f"{hi}–{lo}", word
def breaks(v):
    return v["tran"] in ("Yea", "Nay") and v["dSide"] in ("Yea", "Nay") and v["tran"] != v["dSide"]

# 2025 Congressional Review Act resolutions on environmental and energy rules (passage votes, Republican-backed)
ENV = re.compile(r"Environmental Protection|\bEPA\b|Department of Energy|Energy Efficiency|Ocean Energy|Land Management|National Park Service|Fish and Wildlife", re.I)
env = [v for v in votes if v["y"] == 2025 and "J RES" in v["bill"] and v["q"].startswith("On Passage")
       and re.search(r"disapprov", v["desc"], re.I) and ENV.search(v["desc"]) and v["rY"] > v["rN"]]
env_nay = sum(v["tran"] == "Nay" for v in env)
env_count = f"all {len(env)}" if env_nay == len(env) else f"{env_nay} of the {len(env)}"

def fill(t, ctx, where):
    def rep(m):
        k = m.group(1)
        if k not in ctx: problems.append(f"{where}: no value for {{{k}}}"); return m.group(0)
        return ctx[k]
    return re.sub(r"\{(\w+)\}", rep, t)

def roll_item(c, it, where):
    vs = []
    for r in it["rolls"]:
        v = by.get(r["roll"])
        if not v: problems.append(f"{where}: roll {r['roll']} not in data/votes.json"); return None
        vs.append((r, v))
    tv = {v["tran"] for _, v in vs}
    if len(tv) != 1: problems.append(f"{where}: rolls {[r['roll'] for r, _ in vs]} have different votes {tv}; split the item"); return None
    r0, v0 = vs[0]
    vote = v0["tran"]
    other = {"pro": "con", "con": "pro", "pal": "isr", "isr": "pal"}
    sides = {r["yea"] if vote == "Yea" else other[r["yea"]] if vote == "Nay" else c.get("neutral") for r, _ in vs}
    if len(sides) != 1 or None in sides: problems.append(f"{where}: cannot place vote {vote} on a side ({sides})"); return None
    phrase, count, word = dmaj(v0)
    brk = all(breaks(v) for _, v in vs)
    ctx = dict(money)
    ctx.update({"Vote": VOTE[vote], "DemMaj": f"{phrase} ({count})", "demMaj": f"{phrase[0].lower() + phrase[1:]} ({count})",
                "dcount": count, "dside": word or "evenly", "dopposed": {"no": "opposed", "yes": "supported"}.get(word, "split on"),
                "brk_phrase": "breaking with most Democrats" if brk else "voting with most Democrats",
                "dsame": str(v0["dY"] if vote == "Yea" else v0["dN"] if vote == "Nay" else "?"),
                "env_count": env_count})
    if "{dall}" in it["t"]:
        if all(v["dSide"] == "Nay" for _, v in vs): ctx["dall"] = "opposed by most Democrats"
        elif all(v["dSide"] == "Yea" for _, v in vs): ctx["dall"] = "backed by most Democrats"
        else: problems.append(f"{where}: Democrats did not take one side on all rolls, so 'all ...' wording fails")
    if it.get("env"):
        if r0["roll"] not in {f'{v["y"]}{v["n"]}' for v in env}: problems.append(f"{where}: roll {r0['roll']} is not in the environmental CRA set")
    d = it.get("d") or v0["date"][:7]
    if len(vs) == 1 and it.get("d") and not it.get("env") and it["d"] != v0["date"][:7]: problems.append(f"{where}: date {it['d']} != roll date {v0['date'][:7]}")
    out = {"d": d, "s": sides.pop(), "t": fill(it["t"], ctx, where), "u": CLERK + r0["roll"]}
    if it.get("also"): out["urls"] = [out["u"]] + it["also"]   # sources for quoted words (the Clerk record has none)
    if it.get("hi"): out["hi"] = 1
    if brk: out["brk"] = 1
    if it.get("unv"): out["unv"] = 1
    out["votes"] = [{"roll": r["roll"], "bill": v["bill"], "q": v["q"], "date": v["date"], "vote": v["tran"], "result": v["result"],
                     "yea": v["yea"], "nay": v["nay"], "dY": v["dY"], "dN": v["dN"], "dSide": v["dSide"]} for r, v in vs]
    return out

cards = []
for c in picks["cards"]:
    items = []
    for i, it in enumerate(c["items"], 1):
        where = f"{c['key']} item {i}"
        if "rolls" in it:
            out = roll_item(c, it, where)
            if out: items.append(out)
            continue
        for chk in it.get("check", []):
            v = by.get(chk["roll"])
            if not v or v["tran"] != chk["expect"]: problems.append(f"{where}: expected {chk['expect']} on roll {chk['roll']}, data says {v and v['tran']}")
        for n in it.get("names", []):
            if not any(n in p.upper() for p in calc["2026"]["corporatePACs"]): problems.append(f"{where}: {n} not among 2025-26 corporate PACs")
        out = {"d": it["d"], "s": it["s"], "t": fill(it["t"], money, where), "u": it["u"]}
        for k in ("hi", "brk", "unv"):
            if it.get(k): out[k] = 1
        items.append(out)
    counts = {}
    for i in items: counts[i["s"]] = counts.get(i["s"], 0) + 1
    card = {k: c[k] for k in ("key", "q", "v") if k in c}
    card["sum"] = fill(c["sum"], money, c["key"] + " sum")
    card["short"] = fill(c["short"], money, c["key"] + " short")
    for k in ("pro", "con"):
        if k in c: card[k] = c[k]
    card.update({"items": items, "n": len(items), "counts": counts})
    cards.append(card)
    nv = sum(1 for i in items if "votes" in i)
    print(f"{c['q']:<16} {c['v']:<12} {len(items):>2} items ({nv} roll-call)  {counts}")
print(f"environmental CRA resolutions, 2025: against {env_nay} of {len(env)}")
if problems: raise SystemExit("\n".join(problems))
json.dump({"_note": "Generated by scripts/build_cards.py from data/card_picks.json; do not edit by hand.", "cards": cards},
          open(os.path.join(ROOT, "data/cards.json"), "w"), indent=1, ensure_ascii=False)
