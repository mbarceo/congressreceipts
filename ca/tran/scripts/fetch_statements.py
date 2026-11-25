"""Collects Rep. Derek Tran's press releases from tran.house.gov into data/statements.json.

Each entry gets a date, title, short excerpt, link, topics and kind (statement, letter, bill, ...).
Usage: python3 -I scripts/fetch_statements.py   (re-run anytime to pick up new releases)
"""
import html, json, os, re, time, urllib.request
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BASE = "https://tran.house.gov"
RAW = os.path.join(ROOT, "data/statements_raw")
os.makedirs(RAW, exist_ok=True)

TOPICS = [  # (topic, keywords) — order sets the primary topic
    ("Immigration & ICE", r"\bice\b|immigra|deport|homeland security|\bdhs\b|border|noem|\bcbp\b|national guard|laken riley|asylum|daca|h\.r\. ?(875|3486|4371|1958)\b|detention"),
    ("Foreign policy", r"israel|gaza|iran|ukraine|russia|war powers|foreign|middle east|strike|ceasefire|nato"),
    ("Vietnamese community & human rights", r"vietnam|saigon|vietnamese|human rights|\bccp\b|china|chinese|taiwan|communis|prisoner of conscience|aapi|asian american|house resolution 58|h\.res\. ?58\b|lunar new year|\btết\b|\btet\b"),
    ("Veterans & military", r"veteran|military|troop|\barmy\b|defense|ndaa|\bva\b|servicemember|september 11|9/11|armed services|national security|los alamitos|\bguard\b"),
    ("Health care & safety net", r"health|medicaid|medicare|\baca\b|affordable care|drug|insurance|\bsnap\b|social security|senior|nutrition|hunger"),
    ("Cost of living & economy", r"cost|tariff|price|housing|afford|small business|econom|\btax|inflation|gas\b|electric|jobs|wage|worker|trade|grocer|rent"),
    ("Public safety & environment", r"rideshare|environment|climate|clean air|clean water|police|law enforcement|shooting|crime|fentanyl|\bgun|firefight|wildfire|\bfire\b|safety|chemical|leak|gkn|hazard"),
    ("Rights & democracy", r"abortion|reproductive|women|ivf|lgbtq|civil rights|voting|democracy|impeach|epstein|ethic|insider trading|corruption|constitution|free speech|transparen|state of the union|doge|antisemit|islamophob|\bhate\b|political violence|protest"),
    ("Government funding", r"shutdown|appropriation|continuing resolution|funding bill|spending|budget|\bcr\b|government funding|rescission"),
    ("District & local", r"community project|grant|town hall|office hours|cerritos|garden grove|westminster|buena park|cypress|fullerton|fountain valley|la palma|artesia|norwalk|lakewood|santa ana|placentia|stanton|hawaiian gardens|seal beach|orange county|constituent|local "),
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

ROW = re.compile(r'<a href="(/media/press-releases/[^"]+)">(.*?)</a></div>.*?<div class="col-auto">\s*([A-Z][a-z]+ \d{1,2}, \d{4})\s*</div>(.*?)<hr', re.S)
out, seen, page = [], set(), 0
while True:
    path = os.path.join(RAW, f"p{page}.html")
    if os.path.exists(path) and page > 0:
        s = open(path).read()
    else:
        s = get(f"{BASE}/media/press-releases?page={page}")
        open(path, "w").write(s)
        time.sleep(1)
    rows = ROW.findall(s)
    if not rows:
        break
    new = 0
    for href, title, date, body in rows:
        if href in seen:
            continue
        seen.add(href); new += 1
        title = clean(title)
        ex = clean(body)
        ex = re.sub(r"^(Washington, D\.?C\.?|[A-Z][a-zA-Z .]+, CA)\s*[–-]\s*", "", ex)
        text = (title + " " + ex).lower().replace("(ca-45)", "")
        lang = "vi" if re.search(r"Dân Biểu|Biểu Derek|[ạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ]", title) else \
               "es" if re.search(r"\b(El Representante|Representante|Congresista|Ley|para|los|las)\b", title) else "en"
        topics = [t for t, rx in TOPICS if re.search(rx, text)]
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
