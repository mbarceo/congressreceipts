"""Builds data/stances.json from hand-picked roll calls, title-matched statements and curated releases.

Reads data/stance_picks.json, data/votes.json, data/statements.json, data/statements_full.json and
data/trackaipac.json. Her vote on each roll comes from the Clerk record, never from the picks file.
A curated release (statementPicks) must match exactly one statement, and its snippet regex must match the
release's full text, or the build stops. Usage: python3 -I scripts/build_stances.py
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, ROOT

def load(p, default=None):
    f = os.path.join(ROOT, p)
    return json.load(open(f)) if os.path.exists(f) else default

picks, votes, stm = load("data/stance_picks.json"), load("data/votes.json"), load("data/statements.json")
full, ta = load("data/statements_full.json", {}), load("data/trackaipac.json", {"members": []})
by = {f'{v["y"]}-{v["n"]:03d}': v for v in votes}
english = [s for s in stm if s["lang"] == "en"]
problems = []

def clerk(rid):
    return by[rid]["url"]

def snippet(u, rx):
    """A sentence-sized window around the first match in the release's full text, or None."""
    t = full.get(u)
    m = t and re.search(rx, t, re.I)
    if not m: return None
    a = max(t.rfind(". ", 0, m.start()) + 2, t.rfind("“", 0, m.start()), m.start() - 240, 0)
    e = [x for x in (t.find(". ", m.end()), t.find("”", m.end())) if x > 0]
    b = min(min(e) + 1 if e else len(t), m.end() + 240)
    if a > 0 and t[a - 1] not in " “": a = t.find(" ", a) + 1      # window cut mid-word: snap to a word start
    if b < len(t) and t[b] != " ": b = t.rfind(" ", a, b)               # ...and to a word end
    return ("…" if a > 0 else "") + t[a:b].strip().strip("“”\"") + ("…" if b < len(t) else "")

def pick_statement(sub):
    hits = [s for s in stm if sub in s["u"]]
    if len(hits) != 1: problems.append(f"statementPick {sub!r} matched {len(hits)} releases"); return None
    return hits[0]

out = []
for iss in picks["issues"]:
    rolls = []
    for rid in iss["rolls"]:
        v = by.get(rid)
        if not v: problems.append(f"{iss['id']}: roll {rid} not in votes.json"); continue
        rolls.append({"id": rid, "date": v["date"], "bill": v["bill"], "title": v["desc"] or v["q"], "q": v["q"],
                      "vote": v["member"], "result": v["result"], "yea": v["yea"], "nay": v["nay"],
                      "dY": v["dY"], "dN": v["dN"], "rY": v["rY"], "rN": v["rN"], "dSide": v["dSide"], **{k: v[k] for k in ("cY", "cN") if k in v},
                      "url": clerk(rid), "note": iss.get("notes", {}).get(rid)})
    rolls.sort(key=lambda r: r["date"], reverse=True)
    sts = {}
    if iss.get("statementRx"):
        rx = re.compile(iss["statementRx"], re.I)
        for s in english:
            if rx.search(s["title"]): sts[s["u"]] = {"date": s["date"], "title": s["title"], "kind": s["kind"], "u": s["u"]}
    for sp in iss.get("statementPicks", []):
        s = pick_statement(sp["u"])
        if not s: continue
        q = snippet(s["u"], sp["rx"])
        if not q: problems.append(f"{iss['id']}: snippet /{sp['rx']}/ not found in {s['u']}"); continue
        sts[s["u"]] = {"date": s["date"], "title": s["title"], "kind": s["kind"], "u": s["u"], "quote": q}
    sts = sorted(sts.values(), key=lambda s: s["date"], reverse=True)
    cast = [r for r in rolls if r["vote"] in ("Yea", "Nay")]
    out.append({"id": iss["id"], "name": iss["name"], "intro": iss["intro"], "rolls": rolls, "statements": sts,
                "withDems": sum(1 for r in cast if r["vote"] == r["dSide"]), "cast": len(cast),
                "breaks": sum(1 for r in cast if r["dSide"] in ("Yea", "Nay") and r["vote"] != r["dSide"])})
    print(f"{iss['name']}: {len(rolls)} votes ({out[-1]['breaks']} break with party), {len(sts)} statements")

# ---- Israel / Palestine card: every item sourced; her vote filled from the Clerk record ----
isr = picks["israel"]; items = []
me = next((m for m in ta["members"] if m["group"] == "me"), None)
fec = load("data/fec/summary.json")   # optional: items using {aipac...} placeholders are skipped without it
money = {}
if fec:
    pro = [p for p in fec["pacs"] if p["proIsrael"]]
    aip = [p for p in pro if p["id"] == "C00797670"]
    usd = lambda x: f"${round(x):,}"
    raised = sum(fec["cycles"]["all"]["slices"].values())
    money = {"aipacTotal": usd(sum(p["amount"] for p in aip)),
             "aipacDirect": usd(sum(p["amount"] for p in aip if p["kind"] != "Earmarked via conduit")),
             "aipacEarmark": usd(sum(p["amount"] for p in aip if p["kind"] == "Earmarked via conduit")),
             "dmfi": usd(sum(p["amount"] for p in pro if p["id"] == "C00710848")),
             "proTotal": usd(sum(p["amount"] for p in pro)), "proPct": f"{sum(p['amount'] for p in pro) / raised * 100:.1f}%",
             "through": __import__("datetime").date.fromisoformat(fec["cycles"]["all"]["through"]).strftime("%b %-d, %Y")}
for it in isr["items"]:
    ctx, url = {}, it.get("u", "")
    if it.get("roll"):
        v = by[it["roll"]]; ctx = {"vote": v["member"], "yea": v["yea"], "nay": v["nay"], "dY": v["dY"], "dN": v["dN"], "rY": v["rY"], "rN": v["rN"], "cY": v.get("cY", v["dY"]), "cN": v.get("cN", v["dN"])}
        url = clerk(it["roll"])
    elif it.get("rolls"):
        vs = [by[r] for r in it["rolls"]]; same = {v["member"] for v in vs}
        ctx = {"n": len(vs), "yeaCount": sum(1 for v in vs if v["member"] == "Yea"), "nayCount": sum(1 for v in vs if v["member"] == "Nay"),
               "vote": same.pop() if len(same) == 1 else None}
        if "{vote}" in it["text"] and ctx["vote"] is None:
            problems.append(f"israel: {it['rolls']} have different votes, so {{vote}} can't describe them; split the item or use {{yeaCount}}")
            continue
        url = it.get("u") or clerk(it["rolls"][0])   # set "u" to a page anchor (e.g. stances.html#war-powers) to link a list instead
    elif not url.endswith(".html"):
        s = pick_statement(url); url = s["u"] if s else ""
        if s and it.get("rx") and not snippet(s["u"], it["rx"]): problems.append(f"israel: /{it['rx']}/ not found in {s['u']}")
    if "{aipac" in it["text"] or "{pro" in it["text"]:
        if not money: continue                      # no FEC data yet: leave the item out rather than guess
        ctx.update(money); url = "money.html#israel"
    if "{trackaipac}" in it["text"]:
        if not me: problems.append("trackaipac.json has no entry for the member; run fetch_trackaipac.py"); continue
        ctx["trackaipac"] = f"${me['total']:,}"; url = me["url"]
    d = it.get("dir", "neutral")
    if it.get("yea") and ctx.get("vote") in ("Yea", "Nay"):   # "yea": the side a Yea vote is on, so the recorded vote sets the direction
        d = it["yea"] if ctx["vote"] == "Yea" else {"isr": "pal", "pal": "isr"}.get(it["yea"], it["yea"])
    items.append({"d": it["d"], "dir": d, "t": it["text"].format(**ctx), "u": url})
if problems: raise SystemExit("\n".join(problems))
json.dump({"member": M["name"], "issues": out,
           "israel": {"question": isr["question"], "headline": isr["headline"], "headlineWhy": isr.get("headlineWhy", ""), "summary": isr["summary"], "items": items}},
          open(os.path.join(ROOT, "data/stances.json"), "w"), indent=1, ensure_ascii=False)
print("Israel card:", len(items), "items")
