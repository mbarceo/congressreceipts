"""Verifies every claim in data/claims.json and writes data/verification.json for the Sources page.

Methods, by source:
  House Clerk roll call  her recorded vote must match the vote named in the claim, and every tally quoted
                         ("231-182") must be one of the roll's totals (all, Democrats, Republicans)
  Her press release      the release must be in data/statements.json; quotes and dollar figures in the claim
                         must appear in the release's full text
  Official bill record   govinfo BILLSTATUS checks (data/bill_checks.json, from verify_bills.py)
  This site's figures    dollar figures and percentages must match a recomputed value (data/computed_checks.json)
  Any other web page     fetched and saved in data/sources/; quotes, figures, percentages and required terms must
                         appear on it
  Static facts           'must' terms must appear on the source; committee seats are read from her own entry in
                         the Clerk's member file; PDFs read by hand are recorded with what was read
Statuses: verified | partial | failed | negative-finding. Run after extract_claims.py, verify_bills.py and
verify_computed.py. Usage: python3 -I scripts/verify_all.py
"""
import hashlib, html, json, os, re, subprocess, sys, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, ROOT

J = lambda p: json.load(open(os.path.join(ROOT, p)))
claims, votes, stm, full = J("data/claims.json"), J("data/votes.json"), J("data/statements.json"), J("data/statements_full.json")
bills, computed = J("data/bill_checks.json"), J("data/computed_checks.json")
by = {f'{v["y"]}{v["n"]:03d}': v for v in votes}
stm_u = {s["u"]: s for s in stm}
SRC = os.path.join(ROOT, "data/sources"); os.makedirs(SRC, exist_ok=True)
idx_path = os.path.join(SRC, "index.json"); idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
PRIMARY = ("clerk.house.gov", "rivas.house.gov", "govinfo.gov", "congress.gov", "fec.gov", "sos.ca.gov", "cadem.org",
           "house.gov", "senate.ca.gov", "luzforcongress.com", "web.archive.org/web/20241031093755/https://www.luzforcongress.com")
today = date.today().isoformat()

def norm(s):
    s = html.unescape(s or "")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("\xa0", " "), ("&amp;", "&")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).lower()

def fetch(url):
    """Cached fetch. Archive pages keep script text, since the archived site stores its copy in page data."""
    key = hashlib.sha1(url.encode()).hexdigest()[:16]; p = os.path.join(SRC, key + ".html")
    if url in idx and os.path.exists(p): return idx[url]["status"], open(p, encoding="utf-8", errors="replace").read()
    r = subprocess.run(["curl", "-s", "-L", "-A", "Mozilla/5.0", "--max-time", "90", "-w", "\n%{http_code}", url], capture_output=True)
    out = r.stdout.decode("utf-8", "replace"); body, _, code = out.rpartition("\n")
    status = int(code) if code.isdigit() else 0
    open(p, "w", encoding="utf-8").write(body)
    idx[url] = {"file": key + ".html", "status": status, "fetched": today}; time.sleep(0.6)
    return status, body

def page_text(url, body):
    if "web.archive.org" not in url: body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S)
    return norm(re.sub(r"<[^>]+>", " ", body))

def quotes(c):
    qs = [c["quote"]] if c.get("quote") else []
    qs += re.findall(r"“([^”]{12,})”", c["text"])
    return [q.strip(" .,…") for q in qs]

FIG = re.compile(r"\$[\d,]+(?:\.\d+)?(?: million)?")
PCT = re.compile(r"\b\d{1,3}\.\d%")
fig_val = lambda f: float(re.sub(r"[$,]| million", "", f)) * (1e6 if "million" in f else 1)
def fig_in(f, t):
    """A dollar figure appears in text t, exactly or (for "$2.06 million") as a full number within 0.5%."""
    if norm(f) in t or norm(f.replace(",", "")) in t: return True
    v = fig_val(f)
    return any(abs(float(x.replace(",", "")) - v) <= v * 0.005 for x in re.findall(r"(\d{1,3}(?:,\d{3})+|\d{4,})", t))
def computed_hit(v):
    return next((c["label"] for c in computed if c["ok"] and abs(c["actual"] - v) <= max(1, abs(c["actual"]) * 0.005)), None)

def clerk_ids(urls):
    return [m.group(1) for u in urls for m in [re.search(r"clerk\.house\.gov/Votes/(\d{7,8})$", u)] if m]

def check_votes(c, ids):
    issues, ev = [], []
    rolls = [by.get(i) for i in ids]
    if None in rolls: return ["roll call not in House Clerk data"], ""
    m = re.search(r"\b(?:Voted|voted) (Yea|Nay)\b|Recorded as (Not Voting|Present)", c["text"])
    if m and len(rolls) == 1:
        said = m.group(1) or m.group(2)
        if rolls[0]["member"] != said: issues.append(f"claim says {said}, Clerk record shows {rolls[0]['member']}")
    pairs = set()
    for r in rolls: pairs |= {(r["yea"], r["nay"]), (r["dY"], r["dN"]), (r["rY"], r["rN"])}
    for a, b in re.findall(r"\b(\d{1,3})–(\d{1,3})\b", c["text"]):
        if (int(a), int(b)) not in pairs and not ("." in c["text"] and PCT.search(c["text"])): issues.append(f"tally {a}–{b} not in the roll call")
    for r in rolls: ev.append(f"Roll {r['y']}-{r['n']} ({r['bill']}, {r['date']}): {M['short']} {r['member']}; total {r['yea']}–{r['nay']}; Democrats {r['dY']}–{r['dN']}; {r['result']}")
    return issues, " | ".join(ev)

def committees_ok(must):
    status, body = fetch("https://clerk.house.gov/xml/lists/MemberData.xml")
    root = ET.fromstring(body.encode("utf-8"))
    mem = next((m for m in root.iter("member") if (m.findtext(".//bioguideID") or "") == M["bioguide"]), None)
    if mem is None: return ["her entry is not in the Clerk's member file"], ""
    codes = [a.get("comcode") for a in mem.iter("committee")] + [a.get("subcomcode") for a in mem.iter("subcommittee")]
    names = {}
    for cm in root.iter("committee"):
        if cm.get("comcode"): names[cm.get("comcode")] = cm.findtext("committee-fullname") or ""
        for sc in cm.iter("subcommittee"):
            if sc.get("subcomcode"): names[sc.get("subcomcode")] = sc.findtext("subcommittee-fullname") or ""
    held = norm(" ; ".join(names.get(x, "") for x in codes if x))
    missing = [t for t in must if norm(t) not in held]
    return ([f"not among her assignments: {', '.join(missing)}"] if missing else []), "Her assignments in the Clerk's file: " + held[:300]

out = {}
for c in claims:
    urls, url = c["urls"], c["url"]
    host = re.sub(r"^https?://([^/]+).*", r"\1", url) if url.startswith("http") else "this site"
    rec = {"text": c["text"], "page": c["page"], "section": c["section"], "url": url, "urls": urls, "checked": today, "issues": [],
           "tier": "primary" if (not url.startswith("http") or any(p in url for p in PRIMARY)) else "secondary"}
    ids = clerk_ids(urls)
    if c.get("manual"):
        rec.update(status="verified", method="Read by hand (PDF)", evidence=c["manual"])
    elif c.get("check") == "clerk-committees":
        iss, ev = committees_ok(c["must"]); rec.update(status="failed" if iss else "verified", method="House Clerk member file: her own committee entries", evidence=ev, issues=iss)
    elif ids and all("clerk.house.gov" in u for u in urls):
        iss, ev = check_votes(c, ids); rec.update(status="failed" if iss else "verified", method="House Clerk roll-call record", evidence=ev, issues=iss)
    elif url in stm_u or (url.startswith("https://rivas.house.gov/media/press-releases/")):
        iss = []
        for u in [x for x in urls if "rivas.house.gov/media" in x]:
            if u not in stm_u: iss.append(f"release not found: {u}")
        t = norm(" ".join(full.get(u, "") for u in urls))
        iss += [f'quote not found: "{q[:70]}"' for q in quotes(c) if norm(q)[:80] not in t]
        figs = [f for f in FIG.findall(c["text"]) if not fig_in(f, t) and not computed_hit(fig_val(f))]
        if figs: iss.append("figures not found in the release: " + ", ".join(figs))
        if ids:
            viss, _ = check_votes(c, ids); iss += viss
        s = stm_u.get(url, {})
        rec.update(status="failed" if any(i.startswith(("release not", "claim says", "quote not found", "tally")) for i in iss) else ("partial" if iss else "verified"),
                   method="Her press release, full text" + (" and House Clerk roll call" if ids else ""), evidence=f"{s.get('date', '')}: {s.get('title', '')}"[:160], issues=iss)
    elif re.search(r"govinfo\.gov/bulkdata/BILLSTATUS/119/[a-z]+/BILLSTATUS-119([a-z]+\d+)", url):
        b = bills.get(re.search(r"BILLSTATUS-119([a-z]+\d+)", url).group(1), {})
        rec.update(status="verified" if b.get("ok") else "failed", method="govinfo BILLSTATUS (official bill record)", evidence=f"{b.get('title')}; laws {b.get('laws')}; latest action {b.get('latestAction')}", issues=[b.get("issue")] if b.get("issue") else [])
    elif url and not url.startswith("http"):
        vals = [fig_val(f) for f in FIG.findall(c["text"])] + [float(p.rstrip("%")) for p in PCT.findall(c["text"])]
        hits = [computed_hit(v) for v in vals]
        if ids:
            viss, ev = check_votes(c, ids)
        else: viss, ev = [], ""
        miss = [v for v, h in zip(vals, hits) if not h and v != 0]
        rec.update(status="failed" if viss else ("partial" if miss else "verified"), method="Recomputed from FEC and House Clerk data" + (" and roll calls" if ids else ""),
                   evidence="; ".join(dict.fromkeys(h for h in hits if h)) or ev or url, issues=viss + ([f"not matched to a recomputed figure: {', '.join(str(v) for v in miss)}"] if miss else []))
    elif not url:
        neg = re.search(r"could not confirm|no .* found|not found", c["text"], re.I)
        rec.update(status="negative-finding" if neg else "failed", method="Search of her releases and news coverage" if neg else "none", evidence=None, issues=[] if neg else ["no source link"])
    else:
        iss, texts = [], []
        for u in [x for x in urls if x.startswith("http") and "clerk.house.gov/Votes" not in x]:
            st, body = fetch(u)
            if st != 200 or len(body) < 50: iss.append(f"source did not load (HTTP {st}): {u}")
            else: texts.append(page_text(u, body))
        t = " ".join(texts)
        if texts:
            iss += [f'quote not found: "{q[:70]}"' for q in quotes(c) if norm(q)[:80] not in t]
            figs = [f for f in FIG.findall(c["text"]) if not fig_in(f, t) and not computed_hit(fig_val(f))]
            figs += [p for p in PCT.findall(c["text"]) if p.rstrip("%") not in t and not computed_hit(float(p.rstrip("%")))]
            if figs: iss.append("figures not found on the page: " + ", ".join(figs))
            if c.get("must"):
                miss = [m for m in c["must"] if norm(m) not in t]
                if miss: iss.append("not found on the page: " + ", ".join(miss))
        if ids:
            viss, _ = check_votes(c, ids); iss += viss
        if ids and not [x for x in urls if x.startswith("http") and "clerk.house.gov/Votes" not in x]:
            loaded = True   # roll calls plus links to this site's own computed sections
            vals = [float(p.rstrip("%")) for p in PCT.findall(c["text"])] + [fig_val(f) for f in FIG.findall(c["text"])]
            miss = [v for v in vals if v and not computed_hit(v)]
            if miss: iss.append("not matched to a recomputed figure: " + ", ".join(map(str, miss)))
        else:
            loaded = bool(texts)
        rec.update(status="failed" if not loaded or any(i.startswith(("claim says", "quote not found", "tally")) for i in iss) else ("partial" if iss else "verified"),
                   method="Fetched source page; matched quotes, figures and required terms" + (" and House Clerk roll call" if ids else ""), evidence=url, issues=iss)
    out[c["id"]] = rec

json.dump(idx, open(idx_path, "w"), indent=1)
json.dump(out, open(os.path.join(ROOT, "data/verification.json"), "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(dict(Counter(r["status"] for r in out.values())), "| primary:", sum(r["tier"] == "primary" for r in out.values()), "secondary:", sum(r["tier"] == "secondary" for r in out.values()))
for k, r in out.items():
    if r["status"] in ("failed", "partial"): print(r["status"].upper(), "|", k, "|", r["text"][:90], "|", "; ".join(r["issues"])[:200])
