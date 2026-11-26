"""Builds data/trump_positions.json: House roll calls where the White House stated a position, selected by one rule.

The selection does not depend on any member or party. It is shared by every tracker, which then reads each member's
own vote from data/votes.json (see build_trump.py).

RULE
  Examined: every House roll call of this Congress whose question is a final disposition of a measure
    ("On Passage", "On Agreeing to the Resolution" for a joint or concurrent resolution, "On Motion to Concur in the
    Senate Amendment", "On Motion to Suspend the Rules and Pass") on a bill that has a White House statement of
    administration policy (SAP) in https://www.whitehouse.gov/omb/statements-of-administration-policy/.
    Amendments, motions to recommit or table, previous-question votes and House simple resolutions are not examined.
  Counted: the SAP's first sentence on the measure says the Administration "supports" or "opposes" its passage,
    enactment, adoption or the measure itself. Support means Trump wanted a Yea; opposition means a Nay.
  Skipped, with a reason listed in the output: the statement supports only the "goals" or "intent"; objects only to
    specific sections; or states no position on passage. Nothing is skipped for any other reason.
  Where a bill has more than one SAP (House passage, then a Senate amendment), the one for the matching stage is used:
    "Senate Amendment" statements for concurrence votes, the others otherwise. If that still leaves two statements the
    roll is skipped as ambiguous.

Method: the SAP index page and each PDF are downloaded once, three seconds apart, into data/sap_raw/ (not committed).
PDF text is extracted with `pdftotext` if installed, else with the macOS PDFKit helper below (scripts/pdf_text.swift).
Usage: python3 -I scripts/build_trump_positions.py [--member ca/calvert]   (the member only supplies votes.json)
"""
import json, os, re, subprocess, sys, time, urllib.parse, urllib.request, html as htmllib
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
RAW = os.path.join(REPO, "data/sap_raw"); os.makedirs(RAW, exist_ok=True)
INDEX = "https://www.whitehouse.gov/omb/statements-of-administration-policy/"
UA = {"User-Agent": "Mozilla/5.0"}
member = sys.argv[sys.argv.index("--member") + 1] if "--member" in sys.argv else "ca/calvert"
votes = json.load(open(os.path.join(REPO, member, "data/votes.json")))

_last = [0.0]
def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest): return
    wait = 3 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)                      # one request at a time, three seconds apart
    p = urllib.parse.urlsplit(url); url = urllib.parse.urlunsplit((p.scheme, p.netloc, urllib.parse.quote(p.path), p.query, ""))
    open(dest, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()); _last[0] = time.time()

def pdf_text(path):
    try:
        t = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
        if t.strip(): return re.sub(r"\s+", " ", t)
    except FileNotFoundError: pass
    sw, exe = os.path.join(HERE, "pdf_text.swift"), os.path.join(RAW, "pdf_text")
    if not os.path.exists(exe): subprocess.run(["swiftc", "-O", sw, "-o", exe], check=True, capture_output=True)
    return re.sub(r"\s+", " ", subprocess.run([exe, path], capture_output=True, text=True).stdout)

fetch(INDEX, os.path.join(RAW, "index.html"))
page = open(os.path.join(RAW, "index.html"), errors="ignore").read()
index = []
for u, label in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', page, re.S):
    index.append((re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", htmllib.unescape(label))).strip(), u))

def bill_of(title):
    m = re.match(r"\s*(H\.? ?Con\.? ?Res\.?|H\.? ?J\.? ?Res\.?|S\.? ?J\.? ?Res\.?|S\.? ?Con\.? ?Res\.?|H\.? ?Res\.?|S\.? ?Res\.?|H\.? ?R\.?|S\.?)\s*(\d+)", title.replace("–", "-"), re.I)
    if not m: return None
    p = {"HCONRES": "H CON RES", "HJRES": "H J RES", "SJRES": "S J RES", "SCONRES": "S CON RES", "HRES": "H RES", "SRES": "S RES", "HR": "H R", "S": "S"}.get(re.sub(r"[.\s]", "", m.group(1)).upper())
    return f"{p} {m.group(2)}" if p else None
by = {}
for title, u in index:
    b = bill_of(title)
    if b: by.setdefault(b, []).append((title, u))

FINAL = re.compile(r"^(On Passage|On Agreeing to the Resolution|On Motion to Concur in the Senate Amendment|On Motion to Suspend the Rules and Pass|On Concurring)", re.I)
def examined(v):
    return v["bill"] in by and bool(FINAL.search(v["q"])) and not v["bill"].startswith(("H RES", "S RES"))

SENT_SPLIT = re.compile(r"(?<!\bS)(?<!\bH)(?<!\bJ)(?<!\bCon)(?<!\bRes)(?<!\bNo)\. (?=[A-Z][a-z])")   # not after "H.", "S.", "Con.", "Res."
OBJECT = re.compile(r"\s+(the immediate |immediate |House |the )?(passage|enactment|adoption)|\s+(H\.|S\.)|\s+(this |the )?(bill|Act|resolution|legislation|joint resolution)\b(?![’\']s)|\s+the resolution entitled", re.I)
def sentences(t):
    """Sentences of the statement after its title line. Some statements are scanned images with stray characters
    ("suppo1is"); those are read as "supports"."""
    i = t.find("STATEMENT OF ADMINISTRATION POLICY"); t = t[i:] if i >= 0 else t
    t = re.sub(r"\bsuppo\d?i?s\b", "supports", t)
    for sent in SENT_SPLIT.split(t):
        m = re.search(r"([Tt]he (?:Trump-Vance |Trump )?Administration|President Trump)", sent)
        if m: yield sent[m.start():].strip() + ("" if sent.rstrip().endswith(".") else ".")

def find_position(t):
    """(sentence, direction or None, reason). The first sentence whose verb ("supports"/"opposes") has the measure itself as
    its object counts. If there is none, the first sentence that mentions the Administration's view says why it is skipped."""
    first = None
    for sent in sentences(t):
        s = sent[:420]
        if first is None and re.search(r"\b(supports?|opposes?|appreciates?|acknowledges?|looks forward|welcomes|objects?|seeks|encouraged)\b", s, re.I): first = sent
        if re.search(r"supports? (?:only )?the (goals?|intent|spirit|objectives?)\b(?! of (?:section|sections|provisions?))", s, re.I): return sent, None, "supports a goal or intent behind the measure or part of it; states no position on passage"
        if re.search(r"\b(supports?|opposes?)\b[^.]{0,30}\b(sections?|provisions?)\b", s, re.I): continue
        for m in re.finditer(r"\b(strongly )?(supports?|opposes?)\b", s, re.I):
            if OBJECT.match(s[m.end():m.end() + 70]): return sent, ("support" if m.group(2).lower().startswith("support") else "oppose"), None
    if first and re.search(r"\b(supports?|opposes?)\b[^.]{0,30}\b(sections?|provisions?)\b", first, re.I): return first, None, "objects only to specific sections or provisions; no overall position on passage"
    return first, None, "states no position on passage"

counted, skipped, n_exam = [], [], 0
for v in votes:
    if not examined(v): continue
    n_exam += 1
    rid = f'{v["y"]}-{v["n"]:03d}'; cands = by[v["bill"]]
    concur = "concur" in v["q"].lower()
    stage = [c for c in cands if bool(re.search(r"senate amendment|amendment to", c[0], re.I)) == concur] or cands
    entry = {"roll": rid, "bill": v["bill"], "title": (v["desc"] or v["q"])[:120], "question": v["q"]}
    reads = []
    for title, u in stage:
        dest = os.path.join(RAW, u.rsplit("/", 1)[1])
        try: fetch(u, dest)
        except Exception as e:
            reads.append((title, u, None, None, f"statement could not be downloaded ({e})")); continue
        sent, pos, why = find_position(pdf_text(dest)); reads.append((title, u, sent, pos, why))
    dirs = {r[3] for r in reads}
    if len(dirs) != 1:      # several statements for one stage must all say the same thing, or the roll is skipped
        skipped.append({**entry, "reason": "statements for this stage disagree or one states no position", "url": reads[0][1]}); continue
    title, u, sent, pos, why = reads[0]
    if not pos: skipped.append({**entry, "reason": why, "url": u, "sentence": (sent or "")[:300]}); continue
    q = sent if len(sent) <= 320 else sent[:320].rsplit(" ", 1)[0]
    counted.append({**entry, "trump": "Yea" if pos == "support" else "Nay", "url": u, "statement": title, "quote": q, "truncated": q != sent})
counted.sort(key=lambda r: r["roll"]); skipped.sort(key=lambda r: r["roll"])
out = {"_note": "Built by scripts/build_trump_positions.py; the rule is in that file's docstring and on every Allegiance page. Shared by every member.",
       "sapIndex": INDEX, "examined": n_exam, "counted": counted, "skipped": skipped}
json.dump(out, open(os.path.join(REPO, "data/trump_positions.json"), "w"), indent=1, ensure_ascii=False)
print(f"examined {n_exam}; counted {len(counted)} ({sum(r['trump']=='Nay' for r in counted)} where Trump wanted a Nay); skipped {len(skipped)}")
for s in skipped: print("  skipped", s["roll"], s["bill"], "|", s["reason"])
