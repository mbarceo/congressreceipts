"""Classifies PAC money (corporate, trade, labor, candidate, ideological) and totals money from party
leaders' committees, from FEC data in data/fec/raw. Writes data/fec/establishment_calc.json and
data/fec/leadership.json. Usage: python3 -I scripts/build_establishment.py
"""
import collections, json, os, re
ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
RAW = os.path.join(ROOT, "data/fec/raw")
LAB = re.compile(r"AFSCME|MUNICIPAL EMPLOYEES|STATE COUNTY|GOVERNMENT EMPLOYEES|UNION|BROTHERHOOD|WORKERS|TEAMSTERS|AFL-CIO|SEIU|LABORERS|LIUNA|CARPENTERS|MACHINISTS|IAMAW|ELECTRICAL WORKERS|IBEW|FIRE ?FIGHTERS|FIREPAC|TEACHERS|NEA FUND|PILOTS|LETTER CARRIERS|POSTAL|NURSES|\bCOPE\b|PIPE TRADES|PIPEFITTERS|CONSTRUCTION TRADES|OPERATING ENGINEERS|AIR TRAFFIC|STEELWORKERS|SMART|UNITE HERE|THEATRICAL STAGE|FAA MANAGERS|POSTMASTERS|FEDERAL EMPLOYEES|TREASURY EMPLOYEES|WRITERS GUILD|SAILORS|TRANSIT UNION|TRANSPORT WORKERS|ENGINEERS POLITICAL EDUCATION|ROCKET PAC|PECG", re.I)
TRADE = re.compile(r"\bINSTITUTE\b|\bASSOC|ASSOCIATION|COUNCIL|FEDERATION OF AMERICAN|REALTORS|BANKERS|CREDIT UNIONS|GROWERS|COOPERATIVE|LEAGUE OF USA|CROP INSURERS|WHOLESALERS|ACADEMY OF|SOCIETY FOR|SOCIETY OF|COALITION PAC \(|AMERICAN HOSPITAL|BLOCKCHAIN", re.I)
# Advocacy and party groups often file as "Inc" or "Action Fund"; check these before the corporate rule
IDEO = re.compile(r"ACTION FUND|VICTORY FUND|VOTER ACTION|ENVIRONMENT AMERICA|PLANNED PARENTHOOD|\bNRDC\b|LEAGUE OF CONSERVATION|SIERRA CLUB|EMILY|BOLD PAC|LATINO VICTORY|PROGRESSIVE|DEMOCRAT|HUMANE|CLIMATE|LCV|MOVEON|COURAGE|EQUALITY", re.I)
CORP = re.compile(r"\bINC\b|\bCORP\b|CORPORATION|\bCO\b|COMPANY|\bLLC\b|\bLLP\b|BANCORP|HOLDINGS|INDUSTRIES|TECHNOLOGIES|EMPLOYEES|PBC|GROUP INC|AMAZON|GOOGLE|MICROSOFT|INTEL|BOEING|LOCKHEED|NORTHROP|RAYTHEON|RTX|GENERAL DYNAMICS|L3HARRIS|DELOITTE|KPMG|PRICEWATERHOUSE|ERNST|COMCAST|VERIZON|AT&T|T-MOBILE|WALMART|HOME DEPOT|NIKE|TOYOTA|GENERAL MOTORS|DELTA AIR|UPS|EDWARD JONES|WELLS FARGO|UBS|CVS|MCKESSON|CENCORA|ELEVANCE|CIGNA|CENTENE|MOLINA|HCA|DAVITA|AFLAC|NEW YORK LIFE|PACIFIC LIFE|NORTHWESTERN MUTUAL|SEMPRA|EDISON|NEXTERA|ANDURIL|SPACEX|SPACE EXPLORATION|ANTHROPIC|COINBASE|Y COMBINATOR|CARLYLE|TRANSDIGM|TEXTRON|HONEYWELL|CATERPILLAR|CARRIER|AKIN GUMP|NELSON MULLINS|FOLEY|PARSONS|AMENTUM|CURTISS|LEONARDO|BAE|ROLLS-ROYCE|GENERAL ATOMICS|ROCKET LAB|K2 SPACE|PUBLIX|MCDONALD|COUPANG|CHARTER COMM|COX ENTERPRISES|S&P GLOBAL|AMERICAN EXPRESS|BECTON|SOLVENTUM|EAST WEST BANCORP|WESTERN ALLIANCE|JEFFERSON BANKCORP|HIMS|CAREFIRST|HEALTH CARE SERVICE|COMMUNITY HEALTH SYSTEMS|AAR CORP|AVANTUS|ENGINEERING & SOFTWARE|AMALGAMATED SUGAR|AMERICAN CRYSTAL|MINN-DAK|MICHIGAN SUGAR|SOUTHERN MINNESOTA|WESTERN SUGAR|SUGAR CANE GROWERS|GROWTH ENERGY|ROCKET LTD", re.I)
# Law and accounting partnerships have PACs with no connected organization in FEC records, but they are business money
FIRM = re.compile(r"\bLLP\b|AKIN GUMP|DELOITTE|KPMG|ERNST & YOUNG|PRICEWATERHOUSE|FOLEY|NELSON MULLINS|HOLLAND & KNIGHT|BROWNSTEIN|SQUIRE PATTON|K&L GATES", re.I)

def fec_type(r):
    """The FEC's own classification of the giving committee, when the row carries it. More reliable than
    names: unions and advocacy groups often file as "Inc." or "Employees", and trade groups carry company names."""
    co = r.get("contributor") or {}
    org, ct = co.get("organization_type_full"), co.get("committee_type_full") or ""
    n = r.get("contributor_name") or ""
    if org == "Corporation": return "corporate"
    if org == "Corporation w/o capital stock": return "corporate" if re.search(r"INSURANCE|MUTUAL", n, re.I) else "trade"
    if not org and FIRM.search(n): return "corporate"
    if org == "Labor Organization": return "labor"
    if org in ("Trade Association", "Membership Organization", "Cooperative"): return "trade"
    if ct in ("House", "Senate", "Presidential"): return "candidate"
    if ct.startswith(("PAC", "Hybrid PAC", "Super PAC")): return "ideological"   # no connected company, union or trade group
    return None

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, FEC

# Party leaders whose committees' money is totalled. Read from tracker.config.json, fec.leaders.<chamber> (or a plain
# list in fec.leaders). Each leader: {"name", "role", "ids": [FEC committee IDs], "rx": name regex, "numKey"}.
# A row counts when its contributor_id is in "ids"; rows with no contributor_id fall back to "rx" on the name.
# (If a leader has no "ids", "rx" alone decides, which is how the House defaults have always matched.)
CHAMBER = M.get("chamber", "house").lower()
_LC = FEC.get("leaders")
LCONF = (_LC.get(CHAMBER) if isinstance(_LC, dict) else {"list": _LC}) if _LC else None
if not LCONF or not LCONF.get("list"):
    raise SystemExit(f"Set fec.leaders.{CHAMBER} in tracker.config.json (see the template for House and Senate defaults).")
LEADERS = {l["name"]: l for l in LCONF["list"]}
CYCLES = [str(c) for c in FEC["cycles"]]

rx_only = collections.defaultdict(set)   # committees matched by name but not listed in "ids": printed so they get checked
def leader_hit(w, l, r, n):
    if r.get("contributor_id") and r.get("contributor_id") in l.get("ids", ()):
        return True
    if l.get("rx") and re.search(l["rx"], n, re.I):
        if l.get("ids"): rx_only[w].add(f"{n} ({r.get('contributor_id') or 'no ID'})")
        return True
    return False

calc, lead = {}, {w: {**{"y" + c: 0 for c in CYCLES}, "committees": set()} for w in LEADERS}
for c in CYCLES:
    rows = json.load(open(os.path.join(RAW, f"committee_contribs_{c}.json")))
    cat, corp = collections.Counter(), set()
    for r in rows:
        if r.get("memo_code") == "X": continue
        a = r.get("contribution_receipt_amount") or 0; n = r.get("contributor_name") or ""; ln = r.get("line_number")
        # Some PAC contributions (mostly after the 2024 election) were filed as "other receipts" (line 15, type 15K)
        if ln == "15" and r.get("receipt_type") == "15K": ln = "11C"
        for w, l in LEADERS.items():
            if ln in ("11C", "12", "11B") and leader_hit(w, l, r, n):
                lead[w]["y" + c] += a; lead[w]["committees"].add(n.title())
        if ln != "11C": continue
        # Order: unmistakable union or advocacy names first (the FEC files some unions, e.g. the NEA fund,
        # as corporations), then the FEC's own type, then the remaining name rules.
        k = "labor" if LAB.search(n) else "ideological" if IDEO.search(n) else fec_type(r)
        if not k:   # no FEC typing on this row: fall back to name rules
            if LAB.search(n): k = "labor"
            elif r.get("entity_type") == "CCM" or re.search(r"FOR CONGRESS|FOR SENATE|FOR [A-Z]+$|CONGRESSIONAL CAMPAIGN", n): k = "candidate"
            elif IDEO.search(n): k = "ideological"
            elif TRADE.search(n): k = "trade"
            elif CORP.search(n): k = "corporate"
            else: k = "ideological"
        if k == "corporate": corp.add(n)
        cat[k] += a
    calc[c] = {"cat": {k: round(v) for k, v in cat.items()}, "ncorp": len(corp), "corporatePACs": sorted(corp)}
json.dump(calc, open(os.path.join(ROOT, "data/fec/establishment_calc.json"), "w"), indent=1)
json.dump({w: {**{"y" + c: round(v["y" + c]) for c in CYCLES}, "committees": sorted(v["committees"])} for w, v in lead.items()},
          open(os.path.join(ROOT, "data/fec/leadership.json"), "w"), indent=1)
print({c: calc[c]["cat"] for c in calc}, {w: tuple(v["y" + c] for c in CYCLES) for w, v in lead.items()})
for w, names in rx_only.items():
    print(f"CHECK: counted for {w} by name only (add the ID to fec.leaders if it is really theirs):", "; ".join(sorted(names)))

# ---- Establishment page data: computed numbers + hand-curated, sourced items (data/establishment_items.json) ----
# Every number in an item's text comes from {placeholders} filled here, so the page can't drift from the data.
from votes_common import load_rolls, MY_ID, LEADER
ME, JEF = MY_ID, LEADER["voteId"]
both, diffs = 0, []
for r in load_rolls():
    a, b = r["votes"].get(ME), r["votes"].get(JEF)
    if a in ("Yea", "Nay") and b in ("Yea", "Nay"):
        both += 1
        if a != b:
            diffs.append({"id": r["id"], "date": r["date"], "bill": r["bill"], "q": r["q"], "title": r["desc"] or r.get("amend", ""),
                          "me": a, "jeffries": b, "url": r["url"]})
usd = lambda x: f"${round(x):,}"
al = json.load(open(os.path.join(ROOT, "data/alignment.json"))); peer = {p["name"]: p for p in al["peers"]}
L = json.load(open(os.path.join(ROOT, "data/fec/leadership.json")))
yy = lambda c: c[2:]
pc = lambda name, k="contested": (peer.get(name) or {}).get(k)   # a comparison peer's figure, None if not in this tracker
nums = {**{"lead" + yy(c): usd(sum(v["y" + c] for v in L.values())) for c in CYCLES},
        # a leader with "numKey" (House: the DCCC as "dccc"; Senate: the DSCC as "dscc") gets its all-cycle total as {numKey}
        **{l["numKey"]: usd(sum(L[w]["y" + c] for c in CYCLES)) for w, l in LEADERS.items() if l.get("numKey")},
        **{"corp" + yy(c): usd(calc[c]["cat"].get("corporate", 0)) for c in CYCLES},
        **{"ncorp" + yy(c): calc[c]["ncorp"] for c in CYCLES},
        "jeffAgree": f"{(both - len(diffs)) / both * 100:.1f}" if both else None, "both": both, "ndiff": len(diffs),
        "leaderName": LEADER["name"], "unity": al["memberUnity"], "rank": al["memberRank"], "tied": al.get("memberTied", 0), "dems": al["dems"], "contested": al["contested"],
        # How the splits break down, so summaries can say which way they go without typing counts:
        # {splitNoBills} No on legislation the leader backed, {splitYesBills} Yes on legislation the leader opposed,
        # {splitYesNoms}/{splitNoNoms} the same for Senate nominations (bill numbers starting "PN")
        **{f"split{v}{k}": sum(1 for d in diffs if d["me"] == ("Yea" if v == "Yes" else "Nay") and d["bill"].startswith("PN") == (k == "Noms"))
           for v in ("Yes", "No") for k in ("Bills", "Noms")},
        "jeffC": pc(LEADER["name"]), "gottC": pc("Josh Gottheimer"), "aocC": pc("Alexandria Ocasio-Cortez")}
items = json.load(open(os.path.join(ROOT, "data/establishment_items.json")))
fill = lambda s: s.format(**nums)
out = {"question": items["question"], "headline": items["headline"], "summary": fill(items["summary"]), "why": fill(items["why"]),
       "tiles": [[fill(a), fill(b)] for a, b in items["tiles"]],
       "signs": {k: [{**s, "text": fill(s["text"])} for s in v] for k, v in items["signs"].items()},
       "timeline": sorted(({**e, "text": fill(e["text"])} for e in items["timeline"]), key=lambda e: e["d"], reverse=True),
       "left": [{**e, "text": fill(e["text"])} for e in items["left"]],
       "leaders": [{"name": w, "role": items.get("roles", {}).get(w) or LEADERS.get(w, {}).get("role", ""), **v} for w, v in L.items()],
       "categories": {c: calc[c]["cat"] for c in calc}, "corporatePACs": {c: calc[c]["corporatePACs"] for c in calc},
       "jeffriesDiffs": diffs, "nums": nums,
       # Labels for establishment.html, so the page shows whatever cycles and leaders the config lists
       "cycles": [{"id": c, "label": FEC.get("cycleLabels", {}).get(c, c)} for c in CYCLES],
       "leaderSection": {"title": LCONF.get("title", "Party leaders"), "note": LCONF.get("note", "")}}
json.dump(out, open(os.path.join(ROOT, "data/establishment.json"), "w"), indent=1, ensure_ascii=False)
print("establishment.json:", out["headline"], "|", nums)
