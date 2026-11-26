"""Collects the member's press releases from their official site into data/statements.json.

Each entry gets a date, title, short excerpt, link, topics and kind (statement, letter, bill, ...).
Usage: python3 -I scripts/fetch_statements.py [--max-pages N]   (re-run anytime to pick up new releases)

List-page layouts (tracker.config.json member.pressLayout; "auto" or missing = detect from the first page):
  house-evo       house.gov Drupal "evo" theme: one <div class="views-row"> per release, ?page=N (0-based)
  wp-jetengine    WordPress + JetEngine listing grid (e.g. padilla.senate.gov): one jet-listing-grid__item per
                  release; pages are ?jsf=jet-engine:<query-id>&pagenum=N (1-based; the first page has no query)
  wp-elementor    WordPress + Elementor loop grid (e.g. schiff.senate.gov): one e-loop-item per release;
                  pages are <pressPath><N>/ (taken from the page's own "next page" link)
Another CMS: add a parse_* function, a pager rule and a detect() rule. Each parser must cut the page into one
block per release and read title, date and excerpt from that block only.
Page 0 is always re-fetched; later pages are cached in data/statements_raw/. --max-pages caps a run (senators
can have 1,000-2,000 releases); without it every list page is read.
"""
import urllib.error, html, json, os, re, time, urllib.request
from datetime import datetime
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC, need

ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
BASE = M["site"].rstrip("/")
RAW = os.path.join(ROOT, "data/statements_raw")
os.makedirs(RAW, exist_ok=True)
MAX_PAGES = int(sys.argv[sys.argv.index("--max-pages") + 1]) if "--max-pages" in sys.argv else None
SENATE = M.get("chamber", "house").lower() == "senate"

LOCAL = (CFG.get("statements") or {}).get("localTerms") or ""
TOPICS = [  # (topic, keywords) — order sets the primary topic
    ("Immigration & ICE", r"\bice\b|immigra|deport|homeland security|\bdhs\b|border|noem|\bcbp\b|national guard|laken riley|asylum|daca|detention"),
    ("Foreign policy", r"israel|gaza|iran|ukraine|russia|war powers|foreign|middle east|strike|ceasefire|\bnato\b"),
    ("Science, education & technology", r"\bstem\b|education|science|school|student|research|technology|\bai\b|artificial intelligence|computer|nasa|\bnsf\b|engineer|manufactur|csun|college|universit"),
    ("Transportation & infrastructure", r"transit|\bmetro\b|sepulveda|bus stop|transportation|infrastructure|bridge|water bill|post office|sidewalk|pedestrian|airport|whiteman|\bfaa\b|telecommunication"),
    ("Veterans & military", r"veteran|military|troop|\barmy\b|defense|ndaa|\bva\b|servicemember|september 11|9/11|armed services|national security|los alamitos|\bguard\b"),
    ("Health care & safety net", r"health|medicaid|medicare|\baca\b|affordable care|drug|insurance|\bsnap\b|social security|senior|nutrition|hunger"),
    ("Cost of living & economy", r"\bcost(?!a\b)|tariff|price|housing|afford|small business|econom|\btax|inflation|\bgas\b|electric|jobs|wage|worker|trade|grocer|\brent"),
    ("Public safety & environment", r"suspicious|envelope|disaster|rideshare|environment|climate|clean air|clean water|police|law enforcement|shooting|crime|fentanyl|\bgun|firefight|wildfire|\bfire\b|safety|chemical|leak|gkn|hazard"),
    ("Rights & democracy", r"oath|censure|disapproval|resignation|oversight duties|mciver|cesar chavez|abortion|reproductive|women|ivf|lgbtq|civil rights|voting|democracy|impeach|epstein|ethic|insider trading|corruption|constitution|free speech|transparen|state of the union|doge|antisemit|islamophob|\bhate\b|political violence|protest"),
    ("Government funding", r"shutdown|appropriation|continuing resolution|funding bill|spending|budget|\bcr\b|government funding|rescission"),
    ("District & local", r"community project|grant|town hall|office hours|constituent" + ("|" + LOCAL if LOCAL else "")),
]
# Senators: statewide and Senate-floor subjects the House rules above miss. These only widen existing topics (the
# site's topic list stays the same for every member) and apply to senators only, so House output is unchanged.
SENATE_EXTRA = {
    "Immigration & ICE": r"refugee|\bvisas?\b|migrant|undocumented|citizenship|naturaliz|green card|\btps\b|temporary protected status|unaccompanied",
    "Foreign policy": r"china|chinese|taiwan|venezuela|cuba\b|mexico|canada|armenia|azerbaijan|sudan|syria|lebanon|west bank|netanyahu|hamas|hostage|holocaust|genocide|atrocit|sanction|ambassador|state department|international|humanitarian|transnational|adversar|\bwar\b",
    "Science, education & technology": r"broadband|internet|online|social media|big tech|\btech\b|cyber|privacy|innovation|\bspace\b|semiconductor|teacher|child care|childcare|\bfcc\b|broadcast|spectrum|weather|forecast|archives|smithsonian|data center|disinformation",
    "Transportation & infrastructure": r"high-speed rail|\brail|highway|\broads?\b|roadless|\bports?\b|freight|aviation|water infrastructure|water supply|water resources|water security|water rights|drinking water|\bdams?\b|levee|landline|permitting",
    "Veterans & military": r"pentagon|\bnavy\b|air force|marine corps|\buss\b|military base|\bbase\b|intelligence|service members|nuclear weapon",
    "Health care & safety net": r"mental health|hospital|patient|maternal|disabilit|cancer|vaccine|opioid|overdose|substance use|food assistance|\bwic\b|medical|\bcdc\b|\bfda\b|pharmac|family leave|paid leave",
    "Cost of living & economy": r"farm|agricultur|crop|grower|ranch|wine|labor\b|union|minimum wage|consumer|\bbank|financial|federal reserve|\bloans?\b|credit|homeless|homeowner|film|entertainment|tourism|industry|prediction market|\bcftc\b|\bsec\b|crypto|meme coin|insurer|business|commerce|merger|acquisition|antitrust|federal employees|federal workforce|pay cut",
    "Public safety & environment": r"drought|flood|storm|earthquake|landslide|smoke|emergency|\bfema\b|recovery|public lands|\blands?\b|national park|national monument|scenic trail|forest|wilderness|conservation|ecolog|restoration|wildlife|\bfish|wetland|ocean|coast|offshore|drilling|\boil\b|fossil fuel|pollution|toxic|waste|recycl|emission|clean energy|renewable|solar|\bwind\b|\bepa\b|\bnoaa\b|interior|endangered|invasive|pest\b|violence|terror|extremis|january 6|assault weapon",
    "Rights & democracy": r"election|voter|ballot|\bfec\b|judicia|judge|nominee|nomination|confirmation|supreme court|scotus|\bcourts?\b|justice|attorney general|\bdoj\b|\bfbi\b|subpoena|investigat|inquiry|probe|accountab|inspector general|whistleblower|pardon|clemency|weaponiz|abuse|rule of law|freedom of|press freedom|first amendment|civil liberties|surveillance|\bfisa\b|tribal|tribe|band of|sovereignty|latino|hispanic|asian american|black history|juneteenth|heritage month|history month|equal|discriminat|minority serving|lgbt|pride|stock trading|campaign finance|super ?pac|dark money|filibuster|pay-to-play|slush fund|self-deal|conflict of interest|emoluments|amicus|\bvote by mail|vote-by-mail|right to vote|redistricting|insurrection act|power grab|executive order|special counsel|white house",
    "Government funding": r"federal funds|federal funding|\bfunding\b|debt ceiling|reconciliation|appropriat",
}
if SENATE:
    TOPICS = [(t, rx + "|" + SENATE_EXTRA[t] if t in SENATE_EXTRA else rx) for t, rx in TOPICS]
KINDS = [
    ("Funding", r"secures|delivers|\$[\d.,]+|million|awarded|grant"),
    ("Bill", r"introduc|legislation|\bbill\b|\bact\b|cosponsor|passage|passes|signed into law"),
    ("Letter", r"letter|urges|urging|demand|calls on|presses|asks"),
    ("Vote", r"\bvote|votes|voted|opposes .* (bill|package|plan)"),
    ("Event", r"town hall|visit|hosts|tour|meets|joins .* (rally|event|press conference)|celebrat|honors|recogniz|commemorat"),
    ("Statement", r"statement|responds|reacts|releases"),
]

def get(url):
    """senate.gov sites answer bursts of requests with 403 "Access Denied" for a while, so back off and retry.
    List pages are cached in data/statements_raw, so a run that still fails resumes where it stopped."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for wait in (60, 180, 600, None):
        try:
            return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code not in (403, 429, 500, 502, 503) or wait is None: raise
            print(f"  HTTP {e.code}; waiting {wait} s and retrying"); time.sleep(wait)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:   # slow or dropped connections
            if wait is None: raise
            print(f"  {type(e).__name__}; waiting {wait} s and retrying"); time.sleep(wait)

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()

def parse_date(s):
    s = clean(s)
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%b. %d, %Y", "%m/%d/%Y", "%m/%d/%y", "%m.%d.%y", "%Y-%m-%d"):
        try: return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError: pass
    raise SystemExit(f"Unrecognized release date {s!r}; add its format to parse_date().")

# Every parser returns [(href, title_html, date_text, excerpt_html)], one tuple per release block.

# House.gov (Drupal "evo") list pages: one <div class="views-row"> per release. Parse each row as its own
# block so a title, date and excerpt can never be stitched together from different rows.
def parse_house_evo(page_html):
    rows = []
    for blk in re.split(r'<div class="views-row', page_html)[1:]:
        a = re.search(r'<div class="h[3-5][^>]*>\s*<a href="(/media/press-releases/[^"]+)">(.*?)</a>', blk, re.S)
        d = re.search(r'<div class="col-auto">\s*([A-Z][a-z]+ \d{1,2}, \d{4})', blk)
        b = re.search(r'evo-press-release__body">(.*?)</div>', blk, re.S)
        if a and d:
            rows.append((a.group(1), a.group(2), d.group(1), b.group(1) if b else ""))
    return rows

READ_MORE = re.compile(r"^(continue reading|read more|more|learn more|read the full release)\W*$", re.I)
WP_END = r'e-load-more-anchor|class="elementor-pagination|jet-smart-filters-pagination|data-elementor-type="footer"|<footer'

def parse_wp(page_html, item_rx, excerpt_rx):
    """WordPress listing grids: one block per item wrapper. Title = the item's first link that is not a "Continue
    Reading" button or the list page itself; date = the item's <time>; excerpt = the item's excerpt widget."""
    rows, listing = [], (BASE + M["pressPath"]).rstrip("/")
    blocks = re.split(item_rx, page_html)[1:]
    if blocks: blocks[-1] = re.split(WP_END, blocks[-1])[0]     # the last item would run into pagination and footer
    for blk in blocks:
        blk = re.sub(r"<style.*?</style>|<script.*?</script>", " ", blk, flags=re.S)
        title = next(((h, t) for h, t in re.findall(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', blk, re.S)
                      if clean(t) and not READ_MORE.match(clean(t)) and h.split("?")[0].rstrip("/") != listing), None)
        d = re.search(r"<time[^>]*>(.*?)</time>", blk, re.S)
        b = re.search(excerpt_rx, blk, re.S)
        if title and d:
            rows.append((html.unescape(title[0]), title[1], d.group(1), b.group(1) if b else ""))
    return rows

def parse_wp_jetengine(page_html):
    return parse_wp(page_html, r'<div[^>]+class="[^"]*\bjet-listing-grid__item\b',
                    r'jet-listing-dynamic-field__content"\s*>(.*?)</div>')

def parse_wp_elementor(page_html):
    return parse_wp(page_html, r'<div[^>]+class="[^"]*\be-loop-item\b',
                    r'post-excerpt\.default"\s*>\s*<div class="elementor-widget-container">(.*?)</div>')

PARSERS = {"house-evo": parse_house_evo, "wp-jetengine": parse_wp_jetengine, "wp-elementor": parse_wp_elementor}

def detect(page_html):
    if 'class="views-row' in page_html and "evo-press-release" in page_html: return "house-evo"
    if "jet-listing-grid__item" in page_html: return "wp-jetengine"
    if "e-loop-item" in page_html: return "wp-elementor"
    raise SystemExit(f"Unrecognized press-release list layout at {BASE}{M['pressPath']}: add a parser to "
                     "scripts/fetch_statements.py (see its docstring) or set member.pressLayout.")

def pager(layout, page0):
    """url(n) for list page n (0 = first page) and the page count the first page reports (None if it doesn't)."""
    first = BASE + M["pressPath"]
    if layout == "house-evo":
        return (lambda n: f"{first}?page={n}"), None
    if layout == "wp-jetengine":
        q = re.search(r'jet-smart-filters-pagination[^>]*data-query-id="([^"]*)"', page0)
        n_pages = re.search(r'data-pages="(\d+)"', page0)
        sep = "&" if "?" in first else "?"
        return (lambda n: first if n == 0 else f"{first}{sep}jsf=jet-engine:{q.group(1) if q else 'default'}&pagenum={n + 1}"), \
               (int(n_pages.group(1)) if n_pages else None)
    if layout == "wp-elementor":
        nxt = re.search(r'data-next-page="([^"]+)"', page0) or re.search(r'class="page-numbers next" href="([^"]+)"', page0)
        tpl = re.sub(r"/2/?$", "/{n}/", html.unescape(nxt.group(1))) if nxt else first.rstrip("/") + "/{n}/"
        n_pages = re.search(r'data-max-page="(\d+)"', page0)
        return (lambda n: first if n == 0 else tpl.format(n=n + 1)), (int(n_pages.group(1)) if n_pages else None)
    raise SystemExit(f"Unknown member.pressLayout {layout!r}; use one of {', '.join(PARSERS)} or auto.")

layout = M.get("pressLayout") or "auto"
house_url = layout == "house-evo" or (layout == "auto" and ".house.gov" in BASE)
url = (lambda n: f"{BASE}{M['pressPath']}?page={n}") if house_url else (lambda n: f"{BASE}{M['pressPath']}")
out, seen, page, last = [], set(), 0, None
while True:
    path = os.path.join(RAW, f"p{page}.html")
    if os.path.exists(path) and page > 0:
        s = open(path).read()
    else:
        s = get(url(page))
        open(path, "w").write(s)
        time.sleep(2)
    if page == 0:
        if layout == "auto": layout = detect(s)
        if layout not in PARSERS: raise SystemExit(f"Unknown member.pressLayout {layout!r}; use one of {', '.join(PARSERS)} or auto.")
        url, last = pager(layout, s)
        if layout != "house-evo": print("layout:", layout, f"({last} list pages)" if last else "")
    rows = PARSERS[layout](s)
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
        if layout != "house-evo":   # other datelines: "WASHINGTON, D.C. —", "Los Angeles, Calif. –"
            ex = re.sub(r"^[A-Z][A-Za-z .,']{2,40}\s*[–—-]\s*", "", ex)
        text = (title + " " + ex).lower()
        if M.get("districtLabel"): text = text.replace(f"({M['districtLabel'].lower()})", "")
        text = re.sub(r"\((?:both |all )?[dri]-[a-z. ]{2,15}\)", " ", text)   # "(D-Va.)", "(R-Maine)": not topics
        lang = "vi" if re.search(r"Dân Biểu|[ạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ]", title) else \
               "es" if re.search(r"\b(El Representante|Representante|Congresista|Ley|para|los|las)\b", title) \
                       or (SENATE and re.search(r"\b(El Senador|Senador|Senadora|del|con)\b", title)) else "en"
        # Primary topic from the title when it matches anything (excerpts mention side issues); the rest from title + excerpt
        first = [t for t, rx in TOPICS if re.search(rx, title.lower())][:1]
        topics = first + [t for t, rx in TOPICS if re.search(rx, text) and t not in first]
        kind = next((k for k, rx in KINDS if re.search(rx, title.lower())), "Statement")
        out.append({"date": parse_date(date),
                    "title": title, "ex": ex[:260], "u": href if href.startswith("http") else BASE + href,
                    "topics": topics or ["Other"], "kind": kind, "lang": lang})
    print(f"page {page}: {len(rows)} rows, {new} new")
    if not new or (last and page + 1 >= last):
        break
    if MAX_PAGES and page + 1 >= MAX_PAGES:
        print(f"stopped at --max-pages {MAX_PAGES} ({last or '?'} list pages in all)"); break
    page += 1

out.sort(key=lambda x: x["date"], reverse=True)
with open(os.path.join(ROOT, "data/statements.json"), "w") as f:
    f.write("[\n" + ",\n".join(json.dumps(x, ensure_ascii=False) for x in out) + "\n]\n")
print(len(out), "statements,", out[-1]["date"], "to", out[0]["date"])
