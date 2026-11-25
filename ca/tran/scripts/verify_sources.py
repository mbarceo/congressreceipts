"""Fetches every non-Clerk source cited in data/claims.json, saves a dated copy in data/sources/,
and checks that quoted words and key figures in each claim appear on the source page.

Statuses: verified (quotes/figures found), partial (page loads, some figures not found on page),
failed (a quoted passage is not on the cited page(s)), unreachable, no-source.
Pages on web.archive.org are matched with <script> contents kept (archived campaign sites render
their text from embedded page data); tags are still stripped. Usage: python3 -I scripts/verify_sources.py
"""
import hashlib, html, json, os, re, time, urllib.request
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data/sources"); os.makedirs(SRC, exist_ok=True)
claims = json.load(open(os.path.join(ROOT, "data/claims.json")))
vpath = os.path.join(ROOT, "data/verification.json")
ver = json.load(open(vpath)) if os.path.exists(vpath) else {}
index_path = os.path.join(SRC, "index.json")
index = json.load(open(index_path)) if os.path.exists(index_path) else {}

def norm(s):
    s = html.unescape(s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).lower()

def fetch(url):
    key = hashlib.sha1(url.encode()).hexdigest()[:16]
    p = os.path.join(SRC, key + ".html")
    if url in index and os.path.exists(p):
        return index[url]["status"], open(p, encoding="utf-8", errors="replace").read()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) civic-research"})
        r = urllib.request.urlopen(req, timeout=30)
        body = r.read().decode("utf-8", "replace"); status = r.status
    except urllib.error.HTTPError as e:
        body, status = "", e.code
    except Exception as e:
        # Some news sites cut off Python's download; retry with curl
        import subprocess
        r2 = subprocess.run(["curl", "-s", "-L", "-A", "Mozilla/5.0", "--max-time", "40", "-w", "%{http_code}", url], capture_output=True)
        out = r2.stdout.decode("utf-8", "replace")
        body, status = (out[:-3], int(out[-3:])) if out[-3:].isdigit() else ("", str(e)[:60])
    open(p, "w", encoding="utf-8").write(body)
    index[url] = {"file": key + ".html", "status": status, "fetched": date.today().isoformat()}
    time.sleep(0.8)
    return status, body

def page_text(url, body):
    if "web.archive.org" not in url:
        body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S)
    return norm(re.sub(r"<[^>]+>", " ", body))

def quote_on_page(q, txt):
    # Every part of the quote (split at ellipses) must appear verbatim, not just its opening words
    parts = [norm(p).strip(" .,;:") for p in re.split(r"\.\.\.|…|\[[^\]]*\]", q)]
    def found(p):
        if p in txt: return True
        # Pages that cut long text off ("...the palestinian territori... more"): accept a 40+ char prefix shown truncated
        return any(p[:k] + "..." in txt for k in range(len(p) - 1, 39, -1))
    return all(found(p) for p in parts if len(p) >= 4)

CLERK = re.compile(r"clerk\.house\.gov/Votes/")

def quotes_in(c):
    qs = []
    if c.get("quote"): qs.append(c["quote"])
    qs += re.findall(r"[“\"]([^”\"]{12,})[”\"]", c["text"])
    return [q.strip(" .,") for q in qs]

def figures_in(text):
    return list(dict.fromkeys(re.findall(r"\$[\d,.]+(?:\s?(?:million|billion|M|B))?|\b\d{1,3}(?:,\d{3})+\b", text)))

stats = {}
for c in claims:
    if any(CLERK.search(u or "") for u in [c.get("url")] + (c.get("urls") or [])):
        # Roll-call claims are checked by verify_votes.py / verify_all.py. Still fetch any other pages they cite,
        # so verify_all can find the quoted words there (the Clerk record holds no quotes).
        for u in (c.get("urls") or []):
            if u and u.startswith("http") and not CLERK.search(u): fetch(u)
        continue
    url = c.get("url")
    if not url:
        ver[c["id"]] = {"status": "no-source", "method": "none", "detail": None, "issues": ["no source link on the claim"]}
        stats["no-source"] = stats.get("no-source", 0) + 1; continue
    if not url.startswith("http"):
        ver[c["id"]] = {"status": "computed", "method": "Computed from FEC or House Clerk data on this site", "detail": url, "issues": []}
        stats["computed"] = stats.get("computed", 0) + 1; continue
    status, body = fetch(url)
    issues = []
    if status != 200 or len(body) < 50:
        st = "unreachable"; issues.append(f"HTTP {status}")
    else:
        txt = page_text(url, body)
        for u in (c.get("urls") or []):  # extra sources cited for the same claim
            if u != url and u.startswith("http"):
                s2, b2 = fetch(u)
                if s2 == 200: txt += " " + page_text(u, b2)
        missing_q = [q for q in quotes_in(c) if not quote_on_page(q, txt)]
        if missing_q: issues += [f'quote not found on page: "{q[:70]}"' for q in missing_q]
        figs = [f for f in figures_in(c["text"]) if norm(f).replace("$", "") not in txt]
        if figs: issues.append("figures not found on page: " + ", ".join(figs))
        if "tran.house.gov" in url:
            m = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2}, (20\d\d)", txt)
            if m and c.get("date") and c["date"][:4].isdigit() and c["date"][:4] != m.group(2):
                issues.append(f"release dated {m.group(0)}, claim dated {c['date']}")
        st = "verified" if not issues else ("failed" if missing_q else "partial")
    ver[c["id"]] = {"status": st, "method": "Fetched source page and matched quotes and figures", "detail": url, "issues": issues}
    stats[st] = stats.get(st, 0) + 1
json.dump(index, open(index_path, "w"), indent=1)
json.dump(ver, open(vpath, "w"), indent=1)
print(stats)
for c in claims:
    v = ver.get(c["id"], {})
    if v.get("status") not in ("verified", "computed"):
        print(v.get("status"), "|", c["id"], "|", c["text"][:90], "|", c.get("url"), "|", "; ".join(v.get("issues", []))[:160])
