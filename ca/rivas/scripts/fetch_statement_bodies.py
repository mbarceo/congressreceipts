"""Downloads the full text of every press release in data/statements.json into data/statements_full.json.

Statement titles and 260-character excerpts miss a lot (e.g. a homelessness paragraph inside a housing release),
so issue searches should use the full text. Cached: re-runs only fetch new releases.
Usage: python3 -I scripts/fetch_statement_bodies.py
"""
import html, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT

SRC, OUT = os.path.join(ROOT, "data/statements.json"), os.path.join(ROOT, "data/statements_full.json")
have = json.load(open(OUT)) if os.path.exists(OUT) else {}

def body(u):
    for attempt in range(3):
        try:
            h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8", "replace")
            i = h.find("evo-press-release__body")
            seg = h[i:] if i >= 0 else h
            seg = re.split(r"### Media|Back to top|Contact Us", html.unescape(re.sub(r"<[^>]+>", " ", seg)))[0]
            time.sleep(0.4)
            return u, re.sub(r"\s+", " ", seg.replace("evo-press-release__body\">", "")).strip()
        except Exception:
            time.sleep(2)
    return u, None

todo = [s["u"] for s in json.load(open(SRC)) if s["u"] not in have]
with ThreadPoolExecutor(4) as ex:
    for u, t in ex.map(body, todo):
        if t: have[u] = t
json.dump(have, open(OUT, "w"), ensure_ascii=False)
print(len(have), "full texts;", len(todo), "fetched this run;", sum(1 for s in json.load(open(SRC)) if s["u"] not in have), "missing")
