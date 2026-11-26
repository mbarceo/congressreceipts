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
                         the Clerk's member file ("check": "clerk-committees", House) or from the senate.gov committee
                         membership XML files ("check": "senate-committees", Senate: every committee and subcommittee
                         named in "must" must list the senator, matched by last name and state); PDFs read by hand
                         are recorded with what was read
Statuses: verified | partial | failed | negative-finding. Run after extract_claims.py, verify_bills.py and
verify_computed.py.

Re-check window (data/verify_policy.json, "recheckDays", 15): a claim that needs a live page (a source page, committee
files, a bill's text) is NOT fetched again when its "key" (hash of the claim's text, links, quote and required terms,
plus CHECKER_VERSION) is unchanged, its last status was "verified" and its last check is under recheckDays old; the
earlier result is kept with its original "checked" date. Failed, partial and changed claims are always re-checked, and
claims checked against local data (roll calls, releases already held, recomputed figures) are re-checked every run.
Bump CHECKER_VERSION whenever a check is tightened so no old result survives it.
Usage: python3 -I scripts/verify_all.py [--fresh] [--max-fetch N]
  --fresh        ignore previous results and re-check everything
  --max-fetch N  of the claims due for a re-check, re-fetch only the N oldest this run (the rest keep their earlier result)
"""
import hashlib, html, json, os, re, subprocess, sys, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, ROOT

J = lambda p: json.load(open(os.path.join(ROOT, p)))
claims, votes, stm, full = J("data/claims.json"), J("data/votes.json"), J("data/statements.json"), J("data/statements_full.json")
bills, computed = J("data/bill_checks.json"), J("data/computed_checks.json")
by = {f'{v["y"]}-{v["n"]:03d}': v for v in votes}
from votes_common import url_to_id, is_vote_url, OWN_NAME
stm_u = {s["u"]: s for s in stm}
SRC = os.path.join(ROOT, "data/sources"); os.makedirs(SRC, exist_ok=True)
idx_path = os.path.join(SRC, "index.json"); idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
PRIMARY = ("clerk.house.gov", "senate.gov", "rivas.house.gov", "govinfo.gov", "congress.gov", "fec.gov", "sos.ca.gov", "cadem.org",
           "house.gov", "senate.ca.gov", "luzforcongress.com", "web.archive.org/web/20241031093755/https://www.luzforcongress.com",
           re.sub(r"^https?://(www\.)?", "", M["site"]).rstrip("/"))
# The member's own press releases: the configured list path, plus the folders the fetched releases actually live in
# (a senate.gov list at /newsroom/press-releases/ can link to releases under /news/press-releases/).
SITE = M["site"].rstrip("/")
REL_PREFIXES = tuple({SITE + M["pressPath"].rstrip("/") + "/"} | {s["u"].rstrip("/").rsplit("/", 1)[0] + "/" for s in stm if s["u"].startswith(SITE)})
is_release = lambda u: u.startswith(REL_PREFIXES)
today = date.today().isoformat()

CHECKER_VERSION = 1   # bump when any check below is tightened or changed, so earlier "verified" results are not reused
_pol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "verify_policy.json")
RECHECK_DAYS = (json.load(open(_pol)).get("recheckDays", 15) if os.path.exists(_pol) else 15)
FRESH = "--fresh" in sys.argv
MAX_FETCH = int(sys.argv[sys.argv.index("--max-fetch") + 1]) if "--max-fetch" in sys.argv else None
_vp = os.path.join(ROOT, "data/verification.json")
prev = json.load(open(_vp)) if os.path.exists(_vp) and not FRESH else {}

def claim_key(c):
    """Hash of everything a result depends on in the claim itself (not on local data), plus the checker version."""
    body = json.dumps({k: c.get(k) for k in ("text", "url", "urls", "quote", "must", "check", "manual")}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(f"{CHECKER_VERSION}|{body}".encode()).hexdigest()[:16]

def age_days(rec):
    try: return (date.today() - date.fromisoformat(rec.get("checked", ""))).days
    except ValueError: return 10**6

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
    """Roll ids for every official roll-call URL (House Clerk or senate.gov) among a claim's sources."""
    return [i for i in (url_to_id(u) for u in urls) if i]

def check_votes(c, ids):
    issues, ev = [], []
    rolls = [by.get(i) for i in ids]
    if None in rolls: return ["roll call not in the official vote data"], ""
    m = re.search(r"\b(?:Voted|voted) (Yea|Nay)\b|Recorded as (Not Voting|Present)", c["text"])
    if m and len(rolls) == 1:
        said = m.group(1) or m.group(2)
        if rolls[0]["member"] != said: issues.append(f"claim says {said}, Clerk record shows {rolls[0]['member']}")
    pairs = set()
    for r in rolls: pairs |= {(r["yea"], r["nay"]), (r["dY"], r["dN"]), (r["rY"], r["rN"]), (r.get("pY", r["dY"]), r.get("pN", r["dN"]))} | ({(r["cY"], r["cN"])} if "cY" in r else set())   # cY–cN: Senate Democratic caucus
    for a, b in re.findall(r"\b(\d{1,3})–(\d{1,3})\b", c["text"]):
        if (int(a), int(b)) not in pairs and not ("." in c["text"] and PCT.search(c["text"])): issues.append(f"tally {a}–{b} not in the roll call")
    for r in rolls: ev.append(f"Roll {r['y']}-{r['n']} ({r['bill']}, {r['date']}): {M['short']} {r['member']}; total {r['yea']}–{r['nay']}; {OWN_NAME} {r.get('pY', r['dY'])}–{r.get('pN', r['dN'])}; {r['result']}")
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

SENATE_ASSIGN = "https://www.senate.gov/general/committee_assignments/assignments.htm"
def senate_committees_ok(must):
    """Senate: every committee and subcommittee named in must lists this senator in its official senate.gov membership
    XML (one file per committee, codes taken from the Senate's committee-assignments page). The XML has no bioguide
    IDs, so the senator is matched by last name and state."""
    status, page = fetch(SENATE_ASSIGN)
    if status != 200: return [f"senate.gov committee assignments page did not load (HTTP {status})"], ""
    codes = sorted(set(re.findall(r"committee_memberships_([A-Z]{4})\.(?:htm|xml)", page)))
    lasts = {norm(M["name"].split()[-1]), norm(M.get("short", ""))} - {""}
    me = lambda mem: norm(mem.findtext("name/last")) in lasts and (mem.findtext("state") or "").strip() == M["state"]
    held, unread = [], []
    for code in codes:
        st, body = fetch(f"https://www.senate.gov/general/committee_membership/committee_memberships_{code}.xml")
        try: root = ET.fromstring(body.encode("utf-8")) if st == 200 else None
        except ET.ParseError: root = None
        if root is None: unread.append(code); continue
        cm = root.find("committees")
        if cm is None: unread.append(code); continue
        for m in cm.findall("members/member"):
            if me(m): held.append(((cm.findtext("committee_name") or code).strip(), (m.findtext("position") or "").strip()))
        for sc in cm.findall("subcommittee"):
            for m in sc.findall("members/member"):
                if me(m): held.append(((sc.findtext("subcommittee_name") or "").strip(), (m.findtext("position") or "").strip()))
    if not held: return [f"{M['short']} ({M['state']}) not found in any senate.gov committee membership file"], ""
    joined = norm(" ; ".join(n for n, _ in held))
    missing = [t for t in must if norm(t) not in joined]
    ev = "Assignments in the senate.gov membership files: " + "; ".join(n + (f" ({p})" if p and p != "Member" else "") for n, p in held)
    if unread: ev += f" [files not readable: {', '.join(unread)}]"
    return ([f"not among the senator's assignments: {', '.join(missing)}"] if missing else []), ev[:1500]

out = {}
CG_BILL = re.compile(r"congress\.gov/bill/(\d+)\w\w-congress/([a-z-]+)/(\d+)")
CG_TYPE = {"senate-bill": "s", "house-bill": "hr", "senate-resolution": "sres", "house-resolution": "hres", "senate-joint-resolution": "sjres",
           "house-joint-resolution": "hjres", "senate-concurrent-resolution": "sconres", "house-concurrent-resolution": "hconres"}
def cg_key(u):
    """congress.gov bill URL -> the id used in data/bills.json: "s1477" for the 119th Congress, "118-s4991" otherwise."""
    c, t, n = CG_BILL.search(u).groups(); k = CG_TYPE.get(t, t) + n
    return k if c == "119" else f"{c}-{k}"

def needs_net(c):
    """True when checking this claim may fetch a live page. Mirrors the branch order in the loop below."""
    urls, url = c["urls"], c["url"]
    if c.get("manual"): return False
    if c.get("check") in ("clerk-committees", "senate-committees"): return True
    if clerk_ids(urls) and all(is_vote_url(u) for u in urls): return False
    if url in stm_u or is_release(url): return False
    if urls and all(CG_BILL.search(u) for u in urls): return True      # may read the bill text on govinfo
    if re.search(r"govinfo\.gov/bulkdata/BILLSTATUS/119/[a-z]+/BILLSTATUS-119([a-z]+\d+)", url): return False
    if url and not url.startswith("http"): return False
    return bool(url)

def reusable(c):
    """The earlier result for this claim, if it can stand in for a fresh check: same key, verified, and inside the window."""
    r = prev.get(c["id"])
    return r if r and r.get("key") == claim_key(c) and r.get("status") == "verified" and needs_net(c) else None

# Claims whose earlier result is reusable but older than the window are "due"; with --max-fetch only the oldest N are re-fetched.
_due = sorted((c for c in claims if reusable(c) and age_days(prev[c["id"]]) >= RECHECK_DAYS), key=lambda c: prev[c["id"]]["checked"])
_refetch = {c["id"] for c in (_due if MAX_FETCH is None else _due[:MAX_FETCH])}
reused = 0

for c in claims:
    urls, url = c["urls"], c["url"]
    old = reusable(c)
    if old and c["id"] not in _refetch:
        out[c["id"]] = old; reused += 1   # same claim, verified, inside the window (or beyond --max-fetch): keep the earlier result and its date
        continue
    host = re.sub(r"^https?://([^/]+).*", r"\1", url) if url.startswith("http") else "this site"
    rec = {"text": c["text"], "page": c["page"], "section": c["section"], "url": url, "urls": urls, "checked": today, "issues": [],
           "tier": "primary" if (not url.startswith("http") or any(p in url for p in PRIMARY)) else "secondary"}
    ids = clerk_ids(urls)
    if c.get("manual"):
        rec.update(status="verified", method="Read by hand (PDF)", evidence=c["manual"])
    elif c.get("check") == "clerk-committees":
        iss, ev = committees_ok(c["must"]); rec.update(status="failed" if iss else "verified", method="House Clerk member file: her own committee entries", evidence=ev, issues=iss)
    elif c.get("check") == "senate-committees":
        iss, ev = senate_committees_ok(c["must"]); rec.update(status="failed" if iss else "verified", method="senate.gov committee membership files: the senator's own entries", evidence=ev, issues=iss)
    elif ids and all(is_vote_url(u) for u in urls):
        iss, ev = check_votes(c, ids); rec.update(status="failed" if iss else "verified", method="Official roll-call record", evidence=ev, issues=iss)
    elif url in stm_u or is_release(url):
        iss = []
        for u in [x for x in urls if is_release(x)]:
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
    elif urls and all(CG_BILL.search(u) for u in urls):
        # congress.gov refuses automated reads (HTTP 403), so bill links are checked against govinfo's BILLSTATUS
        # record for the same bill (data/bill_checks.json, from verify_bills.py): the bill must be listed in
        # data/bills.json, its sponsor/cosponsor role must match the claim's verb, and any Act it names must be in a title.
        iss, ev = [], []
        for u in urls:
            k = cg_key(u); b = bills.get(k) or bills.get("119-" + k)
            if not b: iss.append(f"{k} not in data/bills.json, so its role isn't checked"); continue
            if not b.get("ok"): iss.append(f"{k}: {b.get('issue')}")
            said = "sponsor" if re.match(r"\s*Sponsored", c["text"]) else "cosponsor" if re.match(r"\s*Cosponsored", c["text"]) else None
            if said and b.get("role") != said: iss.append(f"claim says {said}, bills.json records {b.get('role')} for {k}")
            ev.append(f"{k}: {b.get('title')} ({b.get('role')})")
        titles = norm(" ".join((bills.get(cg_key(u)) or bills.get("119-" + cg_key(u)) or {}).get("title") or "" for u in urls))
        for act in re.findall(r"\bthe ((?:[A-Z][\w’'.-]*\s+)+?(?:Act|Resolution)(?: of \d{4})?)", c["text"]):
            if norm(act) in titles: continue
            # A named act can be a section of the bill (the Stop Militarizing Law Enforcement Act inside the George Floyd
            # Justice in Policing Act): look for it in the bill's official text on govinfo.
            found = False
            for u in urls[:1]:
                cg, typ, num = CG_BILL.search(u).groups()
                st, body = fetch(f"https://www.govinfo.gov/link/bills/{cg}/{CG_TYPE.get(typ, typ)}/{num}?link-type=html")
                if st == 200 and norm(act) in norm(html.unescape(re.sub(r"<[^>]+>", " ", body))): found = True; ev.append(f'"{act}" found in the bill text (govinfo)')
            if not found: iss.append(f'"{act}" not in the official title or text')
        rec.update(status="failed" if iss else "verified", method="govinfo BILLSTATUS for each congress.gov bill link (role and title)",
                   evidence="; ".join(ev), issues=iss)
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
        for u in [x for x in urls if x.startswith("http") and not is_vote_url(x)]:
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
        if ids and not [x for x in urls if x.startswith("http") and not is_vote_url(x)]:
            loaded = True   # roll calls plus links to this site's own computed sections
            vals = [float(p.rstrip("%")) for p in PCT.findall(c["text"])] + [fig_val(f) for f in FIG.findall(c["text"])]
            miss = [v for v in vals if v and not computed_hit(v)]
            if miss: iss.append("not matched to a recomputed figure: " + ", ".join(map(str, miss)))
        else:
            loaded = bool(texts)
        rec.update(status="failed" if not loaded or any(i.startswith(("claim says", "quote not found", "tally")) for i in iss) else ("partial" if iss else "verified"),
                   method="Fetched source page; matched quotes, figures and required terms" + (" and House Clerk roll call" if ids else ""), evidence=url, issues=iss)
    rec["key"] = claim_key(c)
    out[c["id"]] = rec

json.dump(idx, open(idx_path, "w"), indent=1)
json.dump(out, open(os.path.join(ROOT, "data/verification.json"), "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(f"reused {reused} earlier results (recheck window {RECHECK_DAYS} days); re-checked {len(out) - reused}")
print(dict(Counter(r["status"] for r in out.values())), "| primary:", sum(r["tier"] == "primary" for r in out.values()), "secondary:", sum(r["tier"] == "secondary" for r in out.values()))
for k, r in out.items():
    if r["status"] in ("failed", "partial"): print(r["status"].upper(), "|", k, "|", r["text"][:90], "|", "; ".join(r["issues"])[:200])
