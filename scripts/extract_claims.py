"""Collects every sourced claim the site shows into data/claims.json (the claims registry).

Reads the built data each page renders (promises, stances, evidence cards, establishment, overview events) plus
data/claims_static.json for facts typed directly into the pages. Each claim: id, page, section, date, text,
quote, url, urls, plus optional must/check/manual for static facts. Usage: python3 -I scripts/extract_claims.py
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT

J = lambda p: json.load(open(os.path.join(ROOT, p)))
claims, seen = [], {}
def add(page, section, text, url, urls=(), date=None, quote=None, **extra):
    key = f"{page}:{section}"
    seen[key] = seen.get(key, 0) + 1
    urls = [u for u in [url, *urls] if u]
    claims.append({"id": f"{key}:{seen[key]}", "page": page, "section": section, "date": date, "text": text.strip(),
                   "quote": quote, "url": url or "", "urls": urls, **extra})

# Promise scorecard
for p in J("data/promises_built.json")["promises"]:
    for s in p["src"]:
        add("overview", f"Promise: {p['issue']}", (f"“{p['promise']}”" if p["quote"] else p["promise"]), s["u"], quote=p["promise"] if p["quote"] else None)
    for a in p["actions"]: add("overview", f"Promise: {p['issue']}", a["text"], a["u"])

# Stances: votes, quoted releases, Israel card
st = J("data/stances.json")
for i in st["issues"]:
    for r in i["rolls"]:
        add("stances", i["name"], f"Voted {r['vote']} on {r['bill']}, {r['title']} ({r['q']}). Result: {r['result']} {r['yea']}–{r['nay']}; Democrats {r['dY']}–{r['dN']}." + (f" {r['note']}" if r.get("note") else ""), r["url"], date=r["date"])
    for s in i["statements"]:
        if s.get("quote"): add("stances", i["name"], f"From her release of {s['date']}: “{s['quote'].strip('…').strip()}”", s["u"], date=s["date"], quote=s["quote"].strip("…").strip())
for it in st["israel"]["items"]: add("stances", "Israel and Palestine", it["t"], it["u"])

# Evidence cards
for c in J("data/cards.json")["cards"]:
    for it in c["items"]: add("stances", c["q"], it["t"], it["u"], urls=it.get("more", []))

# Establishment
es = J("data/establishment.json")
for side in ("e", "i"):
    for s in es["signs"][side]:
        add("establishment", "Signs of " + ("alignment" if side == "e" else "independence"), s["text"], s["src"][0][1], urls=[u for _, u in s["src"][1:]])
for e in es["timeline"]: add("establishment", "Timeline", e["text"], e["u"], date=e["d"])
for e in es["left"]: add("establishment", "On the left", e["text"], e["u"])

# Overview events
for e in J("data/overview.json")["events"]: add("townhalls", "Events", f"{e['date']}: {e['title']} ({e.get('role', '')})", e["source"], date=e["date"])

# Static facts typed into pages
for s in J("data/claims_static.json")["claims"]:
    add(s["page"], s["section"], s["text"], s["url"], **{k: s[k] for k in ("must", "check", "manual") if k in s})

json.dump(claims, open(os.path.join(ROOT, "data/claims.json"), "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(claims), "claims:", dict(Counter(c["page"] for c in claims)))
