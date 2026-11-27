"""Downloads the full text of every press release in data/statements.json into data/statements_full.json.

Statement titles and 260-character excerpts miss a lot (e.g. a homelessness paragraph inside a housing release),
so issue searches should use the full text. Cached: re-runs only fetch new releases.
Release bodies are found by layout: house.gov "evo-press-release__body"; WordPress/Elementor (senate.gov sites
such as Padilla's and Schiff's) "theme-post-content" widget; other WordPress themes "entry-content". A page with
none of these is reported as missing rather than saved as a whole page of navigation text.
Senate "js-press-release" layout (vanhollen.senate.gov): the RawHTML block up to the share buttons.
Requests go one at a time, 3 s apart (senate.gov bot protection). --limit N fetches at most N new releases.
Usage: python3 -I scripts/fetch_statement_bodies.py [--limit N]
"""
import html, json, os, re, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT

SRC, OUT = os.path.join(ROOT, "data/statements.json"), os.path.join(ROOT, "data/statements_full.json")
have = json.load(open(OUT)) if os.path.exists(OUT) else {}
text = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()

def extract(h):
    i = h.find("evo-press-release__body")
    if i >= 0:   # house.gov (unchanged from the House trackers)
        seg = re.split(r"### Media|Back to top|Contact Us|\bIssues :|-?\d{2,3}\.\d{6,} -?\d{2,3}\.\d{6,}", html.unescape(re.sub(r"<[^>]+>", " ", h[i:])))[0]
        return re.sub(r"\s+", " ", seg.replace("evo-press-release__body\">", "")).strip()
    h = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", h, flags=re.S)
    m = re.search(r'class="js-press-release[^"]*"[^>]*>(.*?)(?=ShareButtons|<!--stopindex-->|<footer)', h, re.S)
    if m:        # senate.gov "ArticleBlock" sites: release text sits in one RawHTML block
        return text(re.sub(r"<[^>]*$", "", m.group(1)))
    m = re.search(r'data-widget_type="theme-post-content\.default"\s*>(.*?)(?=data-widget_type="|<footer|data-elementor-type="footer")', h, re.S)
    if m:        # Elementor post-content widget: everything up to the next widget (share buttons, related posts)
        return text(re.sub(r"<[^>]*$", "", m.group(1)))   # drop the next widget's unfinished opening tag
    m = re.search(r'<div[^>]+class="[^"]*\bentry-content\b[^"]*"[^>]*>(.*?)(?=<footer|<div[^>]+class="[^"]*\b(?:sharedaddy|post-navigation|entry-footer)\b)', h, re.S)
    if m:
        return text(m.group(1))
    m = re.search(r'<div class\s*=\s*"content">(.*?)(?=</div>\s*</div>\s*</div>\s*</main>)', h, re.S)   # barragan.house.gov
    if m:
        return text(m.group(1))
    return None

def body(u):
    for attempt in range(3):
        try:
            h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8", "replace")
            t = extract(h)
            time.sleep(3)
            return u, t if t and len(t) > 40 else None
        except urllib.error.HTTPError as e:
            if e.code in (403, 429): sys.exit(f"HTTP {e.code} from {u}: stopping (bot protection). Wait a few hours, then re-run; finished texts are kept.")
            time.sleep(3)
        except Exception:
            time.sleep(3)
    return u, None

LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
todo = [s["u"] for s in json.load(open(SRC)) if s["u"] not in have][:LIMIT]
for n, u in enumerate(todo, 1):   # one request at a time; saves after every release so an interrupted run resumes
    u, t = body(u)
    if t: have[u] = t
    json.dump(have, open(OUT, "w"), ensure_ascii=False)
    print(n, "of", len(todo), "ok" if t else "MISSING", u, flush=True)
json.dump(have, open(OUT, "w"), ensure_ascii=False)
missing = [s["u"] for s in json.load(open(SRC)) if s["u"] not in have]
print(len(have), "full texts;", len(todo), "fetched this run;", len(missing), "missing")
for u in missing[:10]: print("  missing:", u)
