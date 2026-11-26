#!/usr/bin/env python3
"""Check each House source link: does the page load, does it name the member near "Jeffries" or "Speaker",
and does every quoted phrase in our note appear word for word?

Polite by design (Congress Receipts rules), same as verify_senate_quotes.py:
  one request at a time, SLEEP seconds apart, each URL fetched once (cached in data/raw_pages),
  a host that returns 403 or 429 is skipped for 24 hours (data/raw/leadership_blocked_hosts.txt), no retries or workarounds,
  sites that scripts can't read (x.com) are skipped.
Run:  python3 -I scripts/verify_leadership_house.py   (see docs/leadership.md)
Out:  data/leadership/verification_house.csv
"""
import csv, hashlib, html, re, time, unicodedata, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "leadership" / "house_receipts.csv"
OUT = ROOT / "data" / "leadership" / "verification_house.csv"
CACHE = ROOT / "data" / "raw" / "leadership_pages"   # data/raw is git-ignored
BLOCKS = ROOT / "data" / "raw" / "leadership_blocked_hosts.txt"
SLEEP, TIMEOUT, MAX_BYTES = 3.0, 20, 4_000_000
UA = "Mozilla/5.0 (compatible; SourceChecker/1.0; one request at a time)"
SKIP_HOSTS = {"x.com", "twitter.com"}
LAST = {"Frederick Haynes III": "Haynes", "Darializa Avila Chevalier": "Avila Chevalier",
        "Angela Gonzales-Torres": "Gonzales-Torres", "Teresa Benitez-Thompson": "Benitez-Thompson",
        "Katy Padilla Stout": "Padilla Stout", "Sarah Trone Garriott": "Trone Garriott",
        "Marni von Wilpert": "von Wilpert", "Alexandria Ocasio-Cortez": "Ocasio-Cortez"}


def norm(s):
    s = html.unescape(s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("\xa0", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def page_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", raw)
    return norm(re.sub(r"(?s)<[^>]+>", " ", raw))


def quotes_in(note):
    qs = re.findall(r'"([^"]{12,})"', note) + re.findall(r"(?:^|[\s(])'([A-Z][^']{14,})'(?=[\s.,;:)]|$)", note)
    return [norm(q).strip(" .,;:!?") for q in qs]


def fetch(url):
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")
    if key.exists():
        return 200, key.read_text(encoding="utf-8", errors="replace"), True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            text = r.read(MAX_BYTES).decode(r.headers.get_content_charset() or "utf-8", errors="replace")
            key.write_text(text, encoding="utf-8")
            return r.status, text, False
    except urllib.error.HTTPError as e:
        return e.code, "", False
    except Exception as e:
        return f"error:{type(e).__name__}", "", False


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    blocked = set()
    if BLOCKS.exists():
        for line in BLOCKS.read_text().splitlines():
            h, _, ts = line.partition(" ")
            if h and ts and time.time() - float(ts) < 24 * 3600:
                blocked.add(h)
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    pages, out, fetched_any = {}, [], False
    for r in rows:
        url, name = r["source_url"], r["name"]
        res = {"name": name, "url": url, "http": "", "quotes_total": 0, "quotes_found": 0, "missing_quotes": "",
               "name_found": "", "near_jeffries": "", "result": ""}
        if not url:
            res["result"] = "no_url"; out.append(res); continue
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if host in SKIP_HOSTS:
            res["result"] = "skipped_unreadable_site"; out.append(res); continue
        if host in blocked and not (CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")).exists():
            res["result"] = "skipped_host_blocked"; out.append(res); continue
        if url not in pages:
            cached = (CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")).exists()
            if not cached and fetched_any:
                time.sleep(SLEEP)
            status, raw, was_cached = fetch(url)
            if not was_cached:
                fetched_any = True
            if status in (403, 429):
                blocked.add(host)
                with BLOCKS.open("a") as bf:
                    bf.write(f"{host} {time.time()}\n")
                print(f"BLOCKED {status} at {host}: not using this host again", flush=True)
            pages[url] = (status, page_text(raw) if raw else "")
            print(f"{status}  {url[:100]}", flush=True)
        status, text = pages[url]
        res["http"] = status
        if status != 200 or not text:
            res["result"] = "blocked" if status in (403, 429) else "fetch_failed"; out.append(res); continue
        qs = quotes_in(r["note"])
        found = [q for q in qs if q in text]
        res["quotes_total"], res["quotes_found"] = len(qs), len(found)
        res["missing_quotes"] = " | ".join(q for q in qs if q not in text)
        last = LAST.get(name, name.split()[-1])
        ft = fold(text)
        res["name_found"] = "yes" if fold(last) in ft else "no"
        near = any(re.search(r"jeffries|speaker", ft[max(0, m.start() - 300): m.end() + 300])
                   for m in re.finditer(re.escape(fold(last)), ft))
        res["near_jeffries"] = "yes" if near else "no"
        if qs and len(found) == len(qs):
            res["result"] = "quote_verified"
        elif qs:
            res["result"] = "quote_not_on_page"
        elif near:
            res["result"] = "name_near_jeffries"
        elif res["name_found"] == "yes":
            res["result"] = "name_found_only"
        else:
            res["result"] = "name_not_on_page"
        out.append(res)
    fields = list(out[0].keys())
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    from collections import Counter
    print("\nsummary:", dict(Counter(x["result"] for x in out)))
    print("blocked hosts:", sorted(blocked))


if __name__ == "__main__":
    main()
