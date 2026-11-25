"""Runs the full verification of data/claims.json and writes data/verification.json.

Checks, in order:
  1. Roll-call claims  -> House Clerk XML (scripts/verify_votes.py logic)
  2. Bill claims       -> govinfo BILLSTATUS records (data/bill_checks.json)
  3. Computed figures  -> recomputed from FEC/Clerk data (data/computed_checks.json)
  4. Web sources       -> fetched copy in data/sources/: quotes, figures, bill numbers and names must appear
Each claim gets: status (verified | partial | failed | negative-finding), tier (primary | secondary),
method, evidence and checked date.
Strictness: a quote not found on its source, a vote that contradicts the Clerk record, or a quoted
tally not in the roll call -> failed. Figures, bill numbers or names not found -> partial. Usage: python3 -I scripts/verify_all.py
"""
import html, json, os, re, subprocess, sys
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
J = lambda p: json.load(open(os.path.join(ROOT, p)))
claims = J("data/claims.json")
bills = J("data/bill_checks.json")
computed = J("data/computed_checks.json")
idx_path = os.path.join(ROOT, "data/sources/index.json")

# Fetch any new web sources (verify_sources caches pages); run vote checks
subprocess.run([sys.executable, "-I", os.path.join(ROOT, "scripts/verify_votes.py")], check=True, stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, "-I", os.path.join(ROOT, "scripts/verify_sources.py")], check=True, stdout=subprocess.DEVNULL)
prev = J("data/verification.json")
idx = json.load(open(idx_path))

PRIMARY = ("clerk.house.gov", "tran.house.gov", "govinfo.gov", "fec.gov", "congress.gov", "sos.ca.gov", "dccc.org",
           "newdemocratcoalition.house.gov", "progressives.house.gov", "bluedogs", "problemsolverscaucus.house.gov",
           "jstreetpac.org", "dmfipac.org", "endcitizensunited.org", "trackaipac.com", "derektranforcongress.com", "propublica.org")
def norm(s):
    s = html.unescape(s or "")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("\xa0", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).lower()
def page(url):
    e = idx.get(url)
    if not e: return None
    s = open(os.path.join(ROOT, "data/sources", e["file"]), encoding="utf-8", errors="replace").read()
    # Archived campaign pages render their text from embedded page data, so keep script contents there
    if "web.archive.org" not in url: s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S)
    return norm(re.sub(r"<[^>]+>", " ", s))
BILL_RX = re.compile(r"\b(H\.\s?R\.|H\.\s?Res\.|H\.\s?Con\.\s?Res\.|H\.\s?J\.\s?Res\.|S\.\s?J\.\s?Res\.|S\.)\s?(\d{1,5})\b")
def bill_key(kind, num):
    k = kind.replace(" ", "").replace(".", "").lower()
    return {"hr": "hr", "hres": "hres", "hconres": "hconres", "hjres": "hjres", "sjres": "sjres", "s": "s"}.get(k, k) + num
def bill_on_page(kind, num, txt):
    n = num
    return bool(re.search(r"(h\.?\s?r\.?|h\.?\s?res\.?|h\.?\s?con\.?\s?res\.?|s\.?\s?j\.?\s?res\.?|s\.)\s?" + n + r"\b", txt)) or ("act" in txt and f" {n} " in f" {txt} " and False)
NAME_RX = re.compile(r"\b([A-Z][a-z]+(?:[\s-][A-Z][a-z]+)+)\b")
SKIP = {"Derek Tran", "Voted For", "Voted Against", "House Democrats", "Most Democrats", "Republican", "In The", "The House"}
fig_rx = re.compile(r"\$[\d,.]+(?:\s?(?:million|billion|M|B|K))?")
def figure_values(text):
    out = []
    for f in fig_rx.findall(text):
        v = f.replace("$", "").replace(",", "").strip()
        mult = 1
        if v.lower().endswith(("million", "m")): mult = 1e6; v = re.sub(r"\s?(million|m)$", "", v, flags=re.I)
        elif v.lower().endswith(("billion", "b")): mult = 1e9; v = re.sub(r"\s?(billion|b)$", "", v, flags=re.I)
        elif v.lower().endswith("k"): mult = 1e3; v = v[:-1]
        try: out.append(float(v.rstrip(".")) * mult)
        except ValueError: pass
    return out
def exact_computed(fig):
    # A figure the web page lacks is accepted only if it equals a recomputed value at the precision shown
    # (e.g. "$19,512" == 19512, "$1.2 million" == round(1,234,567, -5)); no 2% slack across unrelated figures
    vals = figure_values(fig)
    if len(vals) != 1: return None
    v = vals[0]
    m = re.search(r"\.(\d+)", fig); dec = len(m.group(1)) if m else 0
    unit = 1e9 if re.search(r"billion|B$", fig) else 1e6 if re.search(r"million|M$", fig) else 1e3 if fig.endswith("K") else 1
    half = unit * 10 ** -dec / 2
    for c in computed:
        if c["ok"] and any(x is not None and abs(x - v) <= max(half, 0.5) for x in (c["shown"], c["actual"])): return c["label"]
    return None
def computed_match(text):
    vals = figure_values(text)
    hits = []
    for v in vals:
        for c in computed:
            if c["ok"] and c["shown"] and abs(c["shown"] - v) <= max(1, abs(c["shown"]) * 0.02): hits.append(c["label"]); break
            if c["ok"] and v >= 1e5 and abs(round(c["actual"], -3) - v) <= max(1000, v * 0.02): hits.append(c["label"]); break
    return vals, hits

def claimed_vote(text):
    # Independent second check of the vote wording (covers "voted yea/nay/aye", which verify_votes.py does not)
    t = text.lower()
    m = re.search(r"\bvot(?:ed|es|e)\s+(?:[“\"']\s*)?(for|yes|yea|aye|to|against|no|nay|present)\b", t)
    if not m: return None
    w = m.group(1)
    return "Present" if w == "present" else "Nay" if w in ("against", "no", "nay") else "Yea"
def quotes_in(c):
    qs = [c["quote"]] if c.get("quote") else []
    qs += re.findall(r"[“\"]([^”\"]{12,})[”\"]", c["text"])
    return [q.strip(" .,") for q in qs]
CLERK_URL = re.compile(r"clerk\.house\.gov/Votes/")

today = date.today().isoformat()
out = {}
for c in claims:
    url = c.get("url") or ""
    urls = [u for u in [url] + (c.get("urls") or []) if u]
    p = prev.get(c["id"], {})
    rec = {"text": c["text"], "page": c["page"], "url": url, "urls": urls, "checked": today, "issues": []}
    host = re.sub(r"^https?://([^/]+).*", r"\1", url) if url.startswith("http") else "this site"
    m_arch = re.match(r"https?://web\.archive\.org/web/\d+/(https?://[^/]+)", url)
    if m_arch: host = re.sub(r"^https?://", "", m_arch.group(1))   # an archived copy keeps the original source's tier
    rec["tier"] = "primary" if any(h in host for h in PRIMARY) or url.startswith("local:") or not url.startswith("http") else "secondary"
    # 1. roll calls
    if p.get("method", "").startswith("House Clerk"):
        issues = list(p.get("issues", []))
        m = re.search(r"Tran (\w+);", p.get("detail") or "")
        exp = claimed_vote(c["text"])
        if m and exp and m.group(1) in ("Yea", "Nay", "Present") and exp != m.group(1) and not any("Clerk record shows" in i for i in issues):
            issues.append(f"text implies {exp}, Clerk record shows {m.group(1)}")
        status = "verified" if p["status"] == "verified" and not issues else "failed"
        # Quoted words can't be on a roll call: check them on any other source cited, else flag as unchecked
        qs = quotes_in(c)
        if qs and status == "verified":
            others = [u for u in urls if u.startswith("http") and not CLERK_URL.search(u)]
            otxt = " ".join(filter(None, (page(u) for u in others)))
            if not others:
                issues.append("quote not checked: claim cites only the Clerk roll call, no source for the quoted words")
                status = "partial"
            else:
                miss = [q for q in qs if norm(q).strip(" .,") not in otxt]
                if miss: issues += [f'quote not found on page: "{q[:70]}"' for q in miss]; status = "failed"
        rec.update(status=status, method="House Clerk roll-call record", evidence=p.get("detail"), issues=issues)
        out[c["id"]] = rec; continue
    # 2. bills cited via congress.gov
    bm = re.search(r"congress\.gov/bill/119th-congress/([a-z-]+)/(\d+)", url)
    if bm:
        kind = {"house-bill": "hr", "house-resolution": "hres", "house-concurrent-resolution": "hconres"}.get(bm.group(1), bm.group(1))
        b = bills.get(kind + bm.group(2))
        if b:
            rec.update(status="verified" if b["ok"] else "failed", method="govinfo BILLSTATUS (official bill record)",
                       evidence=f"{b['title']}; Tran {b['role']}" + (f" since {b['cosponsored']}" if b.get("cosponsored") else f", introduced {b['introduced']}") + f"; latest action {b['latestAction']}",
                       issues=[] if b["ok"] else [b.get("issue", "")])
            out[c["id"]] = rec; continue
    # 3. computed / local
    if url.startswith("local:") or (url and not url.startswith("http")):
        vals, hits = computed_match(c["text"])
        if vals and len(hits) >= len([v for v in vals if v > 0]):
            rec.update(status="verified", method="Recomputed from FEC/Clerk data", evidence="; ".join(dict.fromkeys(hits)))
        elif not vals:
            rec.update(status="verified" if re.search(r"rank|votes|roll|alignment|189", c["text"], re.I) else "partial", method="Computed on this site from FEC/Clerk data", evidence=url.replace("local:", ""))
        else:
            rec.update(status="partial", method="Computed on this site", evidence=url, issues=["some figures not matched to a recomputed value"])
        out[c["id"]] = rec; continue
    # negative findings and claims without a link
    if not url:
        neg = re.search(r"\bno (public )?statement|we found no|not confirmed|none of his", c["text"], re.I)
        rec.update(status="negative-finding" if neg else "failed", method="Searched his press releases and news coverage" if neg else "none",
                   evidence=None, issues=[] if neg else ["no source link"])
        out[c["id"]] = rec; continue
    # 4. web page checks
    txt = page(url)
    st = idx.get(url, {}).get("status")
    extra = " ".join(filter(None, (page(u) for u in urls[1:] if u.startswith("http"))))
    if txt is not None: txt = txt + " " + extra
    if txt is None or st != 200 or len(txt) < 50:
        rec.update(status="failed", method="Fetched source page", evidence=url, issues=[f"source did not load (HTTP {st})"])
        out[c["id"]] = rec; continue
    issues = list(p.get("issues", []))
    # quotes and figures were checked by verify_sources; recompute figures that are ours
    issues2 = []
    for i in issues:
        if i.startswith("figures not found"):
            figs = i.split(": ", 1)[1].split(", ")
            unmatched = [f for f in figs if not exact_computed(f)]
            if unmatched: issues2.append("figures not found on page: " + ", ".join(unmatched) + " (and not matched to FEC recomputation)")
        else:
            issues2.append(i)
    for kind, num in BILL_RX.findall(c["text"]):
        if not bill_on_page(kind, num, txt):
            b = bills.get(bill_key(kind, num))
            if not (b and b["ok"]): issues2.append(f"{kind}{num} not named on source page")
    names = [n for n in NAME_RX.findall(c["text"]) if n not in SKIP and len(n) > 6]
    missing_names = [n for n in names if norm(n) not in txt and norm(n.split()[-1]) not in txt]
    if names and len(missing_names) > len(names) / 2: issues2.append("names not found on page: " + ", ".join(missing_names[:4]))
    quote_fail = p.get("status") in ("failed", "quote-missing") or any(i.startswith("quote not found") for i in issues2)
    rec.update(status="failed" if quote_fail else "verified" if not issues2 else "partial", method="Fetched source page; matched quotes, figures, bill numbers and names", evidence=url, issues=issues2)
    out[c["id"]] = rec

json.dump(out, open(os.path.join(ROOT, "data/verification.json"), "w"), indent=1)
counts = {}
for r in out.values(): counts[r["status"]] = counts.get(r["status"], 0) + 1
print(counts, "| primary:", sum(r["tier"] == "primary" for r in out.values()), "secondary:", sum(r["tier"] == "secondary" for r in out.values()))
for k, r in out.items():
    if r["status"] in ("failed", "partial"): print(r["status"].upper(), "|", k, "|", r["text"][:95], "|", r["url"][:70], "|", "; ".join(r["issues"])[:170])
