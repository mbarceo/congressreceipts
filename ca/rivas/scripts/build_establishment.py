"""Classifies PAC money (corporate, trade, labor, candidate, ideological) and totals money from party
leaders' committees, from FEC data in data/fec/raw. Writes data/fec/establishment_calc.json and
data/fec/leadership.json. Usage: python3 -I scripts/build_establishment.py
"""
import collections, json, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = os.path.join(ROOT, "data/fec/raw")
LAB = re.compile(r"AFSCME|MUNICIPAL EMPLOYEES|STATE COUNTY|GOVERNMENT EMPLOYEES|UNION|BROTHERHOOD|WORKERS|TEAMSTERS|AFL-CIO|SEIU|LABORERS|LIUNA|CARPENTERS|MACHINISTS|IAMAW|ELECTRICAL WORKERS|IBEW|FIRE ?FIGHTERS|FIREPAC|TEACHERS|NEA FUND|PILOTS|LETTER CARRIERS|POSTAL|NURSES|\bCOPE\b|PIPE TRADES|PIPEFITTERS|CONSTRUCTION TRADES|OPERATING ENGINEERS|AIR TRAFFIC|STEELWORKERS|SMART|UNITE HERE|THEATRICAL STAGE|FAA MANAGERS|POSTMASTERS|FEDERAL EMPLOYEES|TREASURY EMPLOYEES|WRITERS GUILD|SAILORS|TRANSIT UNION|TRANSPORT WORKERS|ENGINEERS POLITICAL EDUCATION|ROCKET PAC|PECG", re.I)
TRADE = re.compile(r"\bINSTITUTE\b|\bASSOC|ASSOCIATION|COUNCIL|FEDERATION OF AMERICAN|REALTORS|BANKERS|CREDIT UNIONS|GROWERS|COOPERATIVE|LEAGUE OF USA|CROP INSURERS|WHOLESALERS|ACADEMY OF|SOCIETY FOR|SOCIETY OF|COALITION PAC \(|AMERICAN HOSPITAL|BLOCKCHAIN", re.I)
# Advocacy and party groups often file as "Inc" or "Action Fund"; check these before the corporate rule
IDEO = re.compile(r"ACTION FUND|VICTORY FUND|VOTER ACTION|ENVIRONMENT AMERICA|PLANNED PARENTHOOD|\bNRDC\b|LEAGUE OF CONSERVATION|SIERRA CLUB|EMILY|BOLD PAC|LATINO VICTORY|PROGRESSIVE|DEMOCRAT|HUMANE|CLIMATE|LCV|MOVEON|COURAGE|EQUALITY", re.I)
CORP = re.compile(r"\bINC\b|\bCORP\b|CORPORATION|\bCO\b|COMPANY|\bLLC\b|\bLLP\b|BANCORP|HOLDINGS|INDUSTRIES|TECHNOLOGIES|EMPLOYEES|PBC|GROUP INC|AMAZON|GOOGLE|MICROSOFT|INTEL|BOEING|LOCKHEED|NORTHROP|RAYTHEON|RTX|GENERAL DYNAMICS|L3HARRIS|DELOITTE|KPMG|PRICEWATERHOUSE|ERNST|COMCAST|VERIZON|AT&T|T-MOBILE|WALMART|HOME DEPOT|NIKE|TOYOTA|GENERAL MOTORS|DELTA AIR|UPS|EDWARD JONES|WELLS FARGO|UBS|CVS|MCKESSON|CENCORA|ELEVANCE|CIGNA|CENTENE|MOLINA|HCA|DAVITA|AFLAC|NEW YORK LIFE|PACIFIC LIFE|NORTHWESTERN MUTUAL|SEMPRA|EDISON|NEXTERA|ANDURIL|SPACEX|SPACE EXPLORATION|ANTHROPIC|COINBASE|Y COMBINATOR|CARLYLE|TRANSDIGM|TEXTRON|HONEYWELL|CATERPILLAR|CARRIER|AKIN GUMP|NELSON MULLINS|FOLEY|PARSONS|AMENTUM|CURTISS|LEONARDO|BAE|ROLLS-ROYCE|GENERAL ATOMICS|ROCKET LAB|K2 SPACE|PUBLIX|MCDONALD|COUPANG|CHARTER COMM|COX ENTERPRISES|S&P GLOBAL|AMERICAN EXPRESS|BECTON|SOLVENTUM|EAST WEST BANCORP|WESTERN ALLIANCE|JEFFERSON BANKCORP|HIMS|CAREFIRST|HEALTH CARE SERVICE|COMMUNITY HEALTH SYSTEMS|AAR CORP|AVANTUS|ENGINEERING & SOFTWARE|AMALGAMATED SUGAR|AMERICAN CRYSTAL|MINN-DAK|MICHIGAN SUGAR|SOUTHERN MINNESOTA|WESTERN SUGAR|SUGAR CANE GROWERS|GROWTH ENERGY|ROCKET LTD", re.I)
LEADERS = {"Hakeem Jeffries": r"JEFFRIES|JEFF PAC", "Nancy Pelosi": r"PELOSI|PAC TO THE FUTURE",
           "Katherine Clark": r"KATHERINE CLARK|CLARK FRONTLINE|FAIR SHOT PAC|FIGHT FOR A DEMOCRATIC MAJORITY",
           "Pete Aguilar": r"AGUILAR|CA LUV PAC|CALIFORNIA LEADERSHIP UNITED|PROGRESSIVE MAJORITY PAC",
           "Steny Hoyer": r"HOYER|AMERIPAC|SAVING AMERICAN DEMOCRACY", "DCCC": r"^DCCC|DEMOCRATIC CONGRESSIONAL CAMPAIGN"}
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

calc, lead = {}, {w: {"y2024": 0, "y2026": 0, "committees": set()} for w in LEADERS}
for c in ("2024", "2026"):
    rows = json.load(open(os.path.join(RAW, f"committee_contribs_{c}.json")))
    cat, corp = collections.Counter(), set()
    for r in rows:
        if r.get("memo_code") == "X": continue
        a = r.get("contribution_receipt_amount") or 0; n = r.get("contributor_name") or ""; ln = r.get("line_number")
        # Some PAC contributions (mostly after the 2024 election) were filed as "other receipts" (line 15, type 15K)
        if ln == "15" and r.get("receipt_type") == "15K": ln = "11C"
        for w, rx in LEADERS.items():
            if re.search(rx, n, re.I) and ln in ("11C", "12", "11B"):
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
json.dump({w: {"y2024": round(v["y2024"]), "y2026": round(v["y2026"]), "committees": sorted(v["committees"])} for w, v in lead.items()},
          open(os.path.join(ROOT, "data/fec/leadership.json"), "w"), indent=1)
print({c: calc[c]["cat"] for c in calc}, {w: (v["y2024"], v["y2026"]) for w, v in lead.items()})

# ---- Establishment page data: computed numbers + hand-curated, sourced items (data/establishment_items.json) ----
# Every number in an item's text comes from {placeholders} filled here, so the page can't drift from the data.
import glob, sys
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M
ME, JEF = M["bioguide"], "J000294"
both, diffs = 0, []
for p in sorted(glob.glob(os.path.join(ROOT, "data/raw/*-roll*.xml"))):
    t = ET.parse(p).getroot(); m = t.find("vote-metadata"); v = {}
    for rv in t.iter("recorded-vote"):
        x = (rv.findtext("vote") or "").strip(); v[rv.find("legislator").get("name-id")] = {"Aye": "Yea", "No": "Nay"}.get(x, x)
    a, b = v.get(ME), v.get(JEF)
    if a in ("Yea", "Nay") and b in ("Yea", "Nay"):
        both += 1
        if a != b:
            y, n = os.path.basename(p)[:4], int(m.findtext("rollcall-num"))
            diffs.append({"id": f"{y}-{n:03d}", "date": (m.findtext("action-date") or "").strip(), "bill": (m.findtext("legis-num") or "").strip(),
                          "q": (m.findtext("vote-question") or "").strip(), "title": (m.findtext("vote-desc") or m.findtext("amendment-author") or "").strip(),
                          "me": a, "jeffries": b, "url": f"https://clerk.house.gov/Votes/{y}{n:03d}"})
usd = lambda x: f"${round(x):,}"
al = json.load(open(os.path.join(ROOT, "data/alignment.json"))); peer = {p["name"]: p for p in al["peers"]}
L = json.load(open(os.path.join(ROOT, "data/fec/leadership.json")))
nums = {"lead24": usd(sum(v["y2024"] for v in L.values())), "lead26": usd(sum(v["y2026"] for v in L.values())),
        "dccc": usd(L["DCCC"]["y2024"] + L["DCCC"]["y2026"]),
        "corp24": usd(calc["2024"]["cat"].get("corporate", 0)), "corp26": usd(calc["2026"]["cat"].get("corporate", 0)),
        "ncorp24": calc["2024"]["ncorp"], "ncorp26": calc["2026"]["ncorp"],
        "jeffAgree": f"{(both - len(diffs)) / both * 100:.1f}", "both": both, "ndiff": len(diffs),
        "unity": al["memberUnity"], "rank": al["memberRank"], "tied": al.get("memberTied", 0), "dems": al["dems"], "contested": al["contested"],
        "jeffC": peer["Hakeem Jeffries"]["contested"], "gottC": peer["Josh Gottheimer"]["contested"], "aocC": peer["Alexandria Ocasio-Cortez"]["contested"]}
items = json.load(open(os.path.join(ROOT, "data/establishment_items.json")))
fill = lambda s: s.format(**nums)
out = {"question": items["question"], "headline": items["headline"], "summary": fill(items["summary"]), "why": fill(items["why"]),
       "tiles": [[fill(a), fill(b)] for a, b in items["tiles"]],
       "signs": {k: [{**s, "text": fill(s["text"])} for s in v] for k, v in items["signs"].items()},
       "timeline": sorted(({**e, "text": fill(e["text"])} for e in items["timeline"]), key=lambda e: e["d"], reverse=True),
       "left": [{**e, "text": fill(e["text"])} for e in items["left"]],
       "leaders": [{"name": w, "role": items["roles"].get(w, ""), **v} for w, v in L.items()],
       "categories": {c: calc[c]["cat"] for c in calc}, "corporatePACs": {c: calc[c]["corporatePACs"] for c in calc},
       "jeffriesDiffs": diffs, "nums": nums}
json.dump(out, open(os.path.join(ROOT, "data/establishment.json"), "w"), indent=1, ensure_ascii=False)
print("establishment.json:", out["headline"], "|", nums)
