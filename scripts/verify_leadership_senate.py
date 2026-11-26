#!/usr/bin/env python3
"""Check each Senate source link: does the page load, does it name the senator, and does every
quoted phrase in our summary appear word for word in the page text?

Polite by design (Congress Receipts rules):
  - one request at a time, SLEEP seconds apart, each URL fetched once (pages cached in data/raw_pages)
  - stops using a host at its first 403 or 429; no retries, no header tricks
  - skips sites that can't be read by a script (x.com)
Run with:  python3 -I scripts/verify_leadership_senate.py   (see docs/leadership.md)
Output:    data/leadership/verification_senate.csv
"""
import csv
import hashlib
import html
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "leadership" / "senate_positions.csv"
OUT = ROOT / "data" / "leadership" / "verification_senate.csv"
CACHE = ROOT / "data" / "raw" / "leadership_pages"   # data/raw is git-ignored
SLEEP = 3.0
TIMEOUT = 20
MAX_BYTES = 4_000_000
UA = "Mozilla/5.0 (compatible; SourceChecker/1.0; one request at a time)"
SKIP_HOSTS = {"x.com", "twitter.com"}
LAST = {"Catherine Cortez Masto": "Cortez Masto", "Lisa Blunt Rochester": "Blunt Rochester",
        "Chris Van Hollen": "Van Hollen"}


def norm(s):
    s = html.unescape(s)
    s = (s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
          .replace("–", "-").replace("—", "-").replace("\xa0", " "))
    return re.sub(r"\s+", " ", s).strip()


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def page_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return norm(raw)


def quotes_in(summary):
    out = []
    for q in re.findall(r'"([^"]+)"', summary):
        q = norm(q).strip(" .,;:!?")
        if len(q) >= 8:
            out.append(q)
    return out


def fetch(url):
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")
    if key.exists():
        return 200, key.read_text(encoding="utf-8", errors="replace"), True
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(MAX_BYTES)
            text = body.decode(r.headers.get_content_charset() or "utf-8", errors="replace")
            key.write_text(text, encoding="utf-8")
            return r.status, text, False
    except urllib.error.HTTPError as e:
        return e.code, "", False
    except Exception as e:  # network, timeout, ssl
        return f"error:{type(e).__name__}", "", False


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    # Hosts that returned 403/429 stay blocked for 24 hours across runs: no retries, no workarounds.
    block_file = ROOT / "data" / "raw" / "leadership_blocked_hosts.txt"
    blocked = set()
    if block_file.exists():
        for line in block_file.read_text().splitlines():
            host, _, ts = line.partition(" ")
            if host and ts and time.time() - float(ts) < 24 * 3600:
                blocked.add(host)
    pages = {}  # url -> (status, normalized text)
    results = []
    first_fetch = True

    for r in rows:
        url = r["source_url"]
        res = {"name": r["name"], "url": url, "http": "", "quotes_total": 0, "quotes_found": 0,
               "missing_quotes": "", "name_found": "", "result": "", "note": ""}
        if not url:
            res["result"] = "no_url"
            results.append(res)
            continue
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if host in SKIP_HOSTS:
            res["result"] = "skipped_unreadable_site"
            results.append(res)
            continue
        if host in blocked and not (CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")).exists():
            res["result"] = "skipped_host_blocked"
            results.append(res)
            continue

        if url not in pages:
            cached = (CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")).exists()
            if not cached and not first_fetch:
                time.sleep(SLEEP)
            status, raw, was_cached = fetch(url)
            first_fetch = False if not was_cached else first_fetch
            if status in (403, 429):
                blocked.add(host)
                with block_file.open("a") as bf:
                    bf.write(f"{host} {time.time()}\n")
                print(f"BLOCKED {status} at {host}: not using this host again", flush=True)
            pages[url] = (status, page_text(raw) if raw else "")
            print(f"{status}  {url[:100]}", flush=True)
        status, text = pages[url]
        res["http"] = status
        if status != 200 or not text:
            res["result"] = "blocked" if status in (403, 429) else "fetch_failed"
            results.append(res)
            continue

        ntext = text
        qs = quotes_in(r["stance_summary"])
        found = [q for q in qs if q in ntext]
        res["quotes_total"] = len(qs)
        res["quotes_found"] = len(found)
        res["missing_quotes"] = " | ".join(q for q in qs if q not in ntext)
        last = LAST.get(r["name"], r["name"].split()[-1])
        ftext = fold(ntext)
        res["name_found"] = "yes" if fold(last) in ftext else "no"
        # Stronger than "name appears": the name sits within 300 characters of the race itself.
        near = any(re.search(re.escape(race), ftext[max(0, m.start() - 300): m.end() + 300])
                   for m in re.finditer(re.escape(fold(last)), ftext)
                   for race in ("schumer", "van hollen"))
        res["note"] = "name_near_race" if near else ""
        if qs and len(found) == len(qs):
            res["result"] = "quote_verified"
        elif qs:
            res["result"] = "quote_not_on_page"
        elif near:
            res["result"] = "name_near_race"
        elif res["name_found"] == "yes":
            res["result"] = "name_found_only"
        else:
            res["result"] = "name_not_on_page"
        results.append(res)

    fields = ["name", "url", "http", "quotes_total", "quotes_found", "missing_quotes", "name_found", "result", "note"]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    from collections import Counter
    print("\nsummary:", dict(Counter(x["result"] for x in results)))
    print("blocked hosts:", sorted(blocked))


if __name__ == "__main__":
    main()
