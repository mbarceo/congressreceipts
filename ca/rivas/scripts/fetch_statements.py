"""Collects the member's press releases from their House site into data/statements.json.

Each entry gets a date, title, short excerpt, link, topics and kind (statement, letter, bill, ...).
Usage: python3 -I scripts/fetch_statements.py   (re-run anytime to pick up new releases)
"""
import html, json, os, re, time, urllib.request
from datetime import datetime
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC, need

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BASE = M["site"]
RAW = os.path.join(ROOT, "data/statements_raw")
os.makedirs(RAW, exist_ok=True)

TOPICS = [  # (topic, keywords) — order sets the primary topic
    ("Immigration & ICE", r"\bice\b|immigra|deport|homeland security|\bdhs\b|border|noem|\bcbp\b|national guard|laken riley|asylum|daca|detention"),
    ("Foreign policy", r"israel|gaza|iran|ukraine|russia|war powers|foreign|middle east|strike|ceasefire|nato"),
    ("Science, education & technology", r"\bstem\b|education|science|school|student|research|technology|\bai\b|artificial intelligence|computer|nasa|\bnsf\b|engineer|manufactur|csun|college|universit"),
    ("Transportation & infrastructure", r"transit|\bmetro\b|sepulveda|bus stop|transportation|infrastructure|bridge|water bill|post office|sidewalk|pedestrian|airport|whiteman|\bfaa\b|telecommunication"),
    ("Veterans & military", r"veteran|military|troop|\barmy\b|defense|ndaa|\bva\b|servicemember|september 11|9/11|armed services|national security|los alamitos|\bguard\b"),
    ("Health care & safety net", r"health|medicaid|medicare|\baca\b|affordable care|drug|insurance|\bsnap\b|social security|senior|nutrition|hunger"),
    ("Cost of living & economy", r"cost|tariff|price|housing|afford|small business|econom|\btax|inflation|gas\b|electric|jobs|wage|worker|trade|grocer|rent"),
    ("Public safety & environment", r"suspicious|envelope|disaster|rideshare|environment|climate|clean air|clean water|police|law enforcement|shooting|crime|fentanyl|\bgun|firefight|wildfire|\bfire\b|safety|chemical|leak|gkn|hazard"),
    ("Rights & democracy", r"oath|censure|disapproval|resignation|oversight duties|mciver|cesar chavez|abortion|reproductive|women|ivf|lgbtq|civil rights|voting|democracy|impeach|epstein|ethic|insider trading|corruption|constitution|free speech|transparen|state of the union|doge|antisemit|islamophob|\bhate\b|political violence|protest"),
    ("Government funding", r"shutdown|appropriation|continuing resolution|funding bill|spending|budget|\bcr\b|government funding|rescission"),
    ("District & local", r"community project|grant|town hall|office hours|constituent|" + CFG["statements"]["localTerms"]),
]
KINDS = [
    ("Funding", r"secures|delivers|\$[\d.,]+|million|awarded|grant"),
    ("Bill", r"introduc|legislation|\bbill\b|\bact\b|cosponsor|passage|passes|signed into law"),
    ("Letter", r"letter|urges|urging|demand|calls on|presses|asks"),
    ("Vote", r"\bvote|votes|voted|opposes .* (bill|package|plan)"),
    ("Event", r"town hall|visit|hosts|tour|meets|joins .* (rally|event|press conference)|celebrat|honors|recogniz|commemorat"),
    ("Statement", r"statement|responds|reacts|releases"),
]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()

# House.gov (Drupal "evo") list pages: one <div class="views-row"> per release. Parse each row as its own
# block so a title, date and excerpt can never be stitched together from different rows.
def parse_rows(page_html):
    rows = []
    for blk in re.split(r'<div class="views-row', page_html)[1:]:
        a = re.search(r'<div class="h5[^>]*>\s*<a href="(/media/press-releases/[^"]+)">(.*?)</a>', blk, re.S)
        d = re.search(r'<div class="col-auto">\s*([A-Z][a-z]+ \d{1,2}, \d{4})', blk)
        b = re.search(r'evo-press-release__body">(.*?)</div>', blk, re.S)
        if a and d:
            rows.append((a.group(1), a.group(2), d.group(1), b.group(1) if b else ""))
    return rows

out, seen, page = [], set(), 0
while True:
    path = os.path.join(RAW, f"p{page}.html")
    if os.path.exists(path) and page > 0:
        s = open(path).read()
    else:
        s = get(f"{BASE}{M['pressPath']}?page={page}")
        open(path, "w").write(s)
        time.sleep(1)
    rows = parse_rows(s)
    if not rows:
        break
    new = 0
    for href, title, date, body in rows:
        if href in seen:
            continue
        seen.add(href); new += 1
        title = clean(title)
        ex = clean(body)
        ex = re.sub(r"^(?:[A-Z][A-Z .,']{2,30}|Washington, D\.?C\.?|[A-Z][a-zA-Z .]+, CA)\s*[–-]\s*", "", ex)
        text = (title + " " + ex).lower().replace(f"({M['districtLabel'].lower()})", "")
        lang = "vi" if re.search(r"Dân Biểu|[ạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ]", title) else \
               "es" if re.search(r"\b(El Representante|Representante|Congresista|Ley|para|los|las)\b", title) else "en"
        # Primary topic from the title when it matches anything (excerpts mention side issues); the rest from title + excerpt
        first = [t for t, rx in TOPICS if re.search(rx, title.lower())][:1]
        topics = first + [t for t, rx in TOPICS if re.search(rx, text) and t not in first]
        kind = next((k for k, rx in KINDS if re.search(rx, title.lower())), "Statement")
        out.append({"date": datetime.strptime(date, "%B %d, %Y").strftime("%Y-%m-%d"),
                    "title": title, "ex": ex[:260], "u": BASE + href,
                    "topics": topics or ["Other"], "kind": kind, "lang": lang})
    print(f"page {page}: {len(rows)} rows, {new} new")
    if not new:
        break
    page += 1

out.sort(key=lambda x: x["date"], reverse=True)
with open(os.path.join(ROOT, "data/statements.json"), "w") as f:
    f.write("[\n" + ",\n".join(json.dumps(x, ensure_ascii=False) for x in out) + "\n]\n")
print(len(out), "statements,", out[-1]["date"], "to", out[0]["date"])
