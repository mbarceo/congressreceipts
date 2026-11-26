"""Chamber-agnostic roll-call loader shared by every vote-related script.

House: House Clerk XML in data/rollcalls/house/<congress>/<year>-roll<NNN>.xml, members keyed by bioguide ID (name-id).
Senate: senate.gov XML in data/rollcalls/senate/<congress>/senate-<year>-<NNNNN>.xml, members keyed by LIS member ID (e.g. S413).

Each roll comes back in one shape, so the build and verify scripts never need to know the chamber:
  {"id": "2025-006", "y": 2025, "n": 6, "date": "2025-01-07", "bill": "H R 29", "q": "On Passage",
   "desc": "...", "type": "...", "result": "Passed", "votes": {member_id: "Yea"|"Nay"|"Present"|"Not Voting"|...},
   "party": {member_id: "D"|"R"|"I"}, "url": official page for the roll call}
Roll ids are "<year>-<3-digit number>" in both chambers (Senate numbers restart each session, i.e. each year).
"""
import glob, os, re
import xml.etree.ElementTree as ET
from datetime import datetime
from config import CFG, M, ROOT, rollcalls_dir

CHAMBER = M.get("chamber", "house").lower()
CONGRESS = int(M.get("congress", 119))
MY_ID = M.get("voteId") or M["bioguide"]          # bioguide for the House, LIS id for the Senate
# The member's own party ("R" or "D"): party unity, "most of the party" tallies and break-with-party checks use it.
OWN = "R" if str(M.get("party", "Democrat")).upper().startswith("R") else "D"
OWN_NAME = "Republicans" if OWN == "R" else "Democrats"
LEADER = CFG.get("leader") or ({"name": "Chuck Schumer", "voteId": "S270"} if CHAMBER == "senate"
                               else {"name": "Hakeem Jeffries", "voteId": "J000294"})

# Caucus rule for party-unity math. Roll-call files list independents as party "I" (Senate: Sanders S313, King S363),
# but both caucus with the Democrats, so for the Democratic majority side (dSide), party unity, the unity ranking and
# "contested" votes they count as Democrats. Official tallies (dY/dN/rY/rN) still follow the party letter in the file.
# Set "caucusWith": {member_id: "D"|"R"} in tracker.config.json; {} turns the rule off. Senate default: Sanders and King.
CAUCUS = CFG.get("caucusWith", {"S313": "D", "S363": "D"} if CHAMBER == "senate" else {})
def caucus(r, k):
    """The caucus a member votes with on roll r: the caucusWith entry if any, else the party letter in the file."""
    return CAUCUS.get(k) or r["party"].get(k)

def unity_min_votes(side_rolls):
    """Fewest party-side Yea/Nay votes a member needs to be ranked for party unity (keeps out members who served briefly).
    tracker.config.json "unityMinVotes" overrides. House default 200 (of ~600+ roll calls a year). Senate default: half
    of the roll calls on which the Democratic caucus took a side, so a senator appointed or departing mid-Congress with
    under half the votes is left out of the ranking instead of being ranked on a small sample."""
    if CFG.get("unityMinVotes"): return int(CFG["unityMinVotes"])
    return 200 if CHAMBER == "house" else (side_rolls + 1) // 2

def norm_vote(x):
    x = (x or "").strip()
    return {"Aye": "Yea", "No": "Nay", "Guilty": "Yea", "Not Guilty": "Nay"}.get(x, x)

def vote_url(y, n):
    if CHAMBER == "senate":
        session = y - (2023 + 2 * (CONGRESS - 118)) + 1     # 119th: 2025 = session 1, 2026 = session 2
        return f"https://www.senate.gov/legislative/LIS/roll_call_votes/vote{CONGRESS}{session}/vote_{CONGRESS}_{session}_{n:05d}.htm"
    return f"https://clerk.house.gov/Votes/{y}{n:03d}"

VOTE_URL_RX = re.compile(r"clerk\.house\.gov/Votes/(\d{4})(\d{1,4})$|senate\.gov/legislative/LIS/roll_call_votes/vote(\d{3})(\d)/vote_\d{3}_\d_(\d{5})\.htm$")
def is_vote_url(u): return bool(VOTE_URL_RX.search(u or ""))
def url_to_id(u):
    """Roll id ("2025-006") for an official roll-call URL in either chamber, else None."""
    m = VOTE_URL_RX.search(u or "")
    if not m: return None
    if m.group(1): return f"{m.group(1)}-{int(m.group(2)):03d}"
    congress, session, n = int(m.group(3)), int(m.group(4)), int(m.group(5))
    return f"{2023 + 2 * (congress - 118) + session - 1}-{n:03d}"

def _house(path):
    t = ET.parse(path).getroot(); m = t.find("vote-metadata")
    g = lambda k: (m.findtext(k) or "").strip()
    y, n = int(os.path.basename(path)[:4]), int(g("rollcall-num"))
    votes, party = {}, {}
    for rv in t.iter("recorded-vote"):
        leg = rv.find("legislator")
        votes[leg.get("name-id")] = norm_vote(rv.findtext("vote")); party[leg.get("name-id")] = leg.get("party")
    try: date = datetime.strptime(g("action-date"), "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError: date = g("action-date")
    return {"id": f"{y}-{n:03d}", "y": y, "n": n, "date": date, "bill": re.sub(r"\s+", " ", g("legis-num")), "q": g("vote-question"),
            "desc": g("vote-desc"), "amend": g("amendment-author"), "type": g("vote-type"), "result": g("vote-result"),
            "votes": votes, "party": party, "url": vote_url(y, n)}

def _senate(path):
    t = ET.parse(path).getroot()
    g = lambda k: re.sub(r"\s+", " ", t.findtext(k) or "").strip()
    y, n = int(g("congress_year")), int(g("vote_number"))
    votes, party = {}, {}
    for mem in t.iter("member"):     # the Vice President's tie-breaking vote (<tie_breaker>) is not a member vote
        i = mem.findtext("lis_member_id"); votes[i] = norm_vote(mem.findtext("vote_cast")); party[i] = (mem.findtext("party") or "").strip()
    try: date = datetime.strptime(re.sub(r",\s+\d{1,2}:\d{2}\s*[AP]M", "", g("vote_date")), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError: date = g("vote_date")
    # Amendment votes leave <document_name> empty; the measure being amended is in <amendment_to_document_number>.
    bill = g("document/document_name") or g("amendment/amendment_to_document_number")
    # vote_title ("Motion to Proceed to S. 9", "Cornyn Amdt. No. 14") rarely says what the measure does;
    # vote_document_text carries the bill title or the amendment's purpose, so add it when it is new information.
    desc, ctx = g("vote_title"), g("vote_document_text")
    # Nominations repeat the nominee ("X to be judge" / "X, of Missouri, to be judge"): skip when its lead is already there.
    lead = ctx.split(",")[0].strip().lower() if ctx else ""
    if ctx and ctx.lower() not in desc.lower() and not ctx.startswith("No Statement of Purpose") and not (len(lead) > 6 and lead in desc.lower()):
        desc = f"{desc}: {ctx}" if desc else ctx
    amend = g("amendment/amendment_number")
    return {"id": f"{y}-{n:03d}", "y": y, "n": n, "date": date, "bill": bill, "q": g("question") or g("vote_question_text"),
            "desc": desc, "amend": amend, "type": g("majority_requirement"), "result": g("vote_result"), "votes": votes, "party": party, "url": vote_url(y, n)}

def load_rolls():
    pat = "senate-*.xml" if CHAMBER == "senate" else "*-roll*.xml"
    parse = _senate if CHAMBER == "senate" else _house
    rolls = [parse(p) for p in sorted(glob.glob(os.path.join(rollcalls_dir(CHAMBER), pat)))]
    rolls.sort(key=lambda r: (r["y"], r["n"]))
    return rolls

def party_side(r, party="D", by_caucus=False):
    """The majority side ("Yea"/"Nay"/None on a tie) of a party's Yea/Nay votes, and the tallies.
    by_caucus=False counts the party letter in the file (official tallies); True counts the caucus (see CAUCUS)."""
    who = (lambda k: caucus(r, k)) if by_caucus else r["party"].get
    y = sum(1 for k, v in r["votes"].items() if who(k) == party and v == "Yea")
    n = sum(1 for k, v in r["votes"].items() if who(k) == party and v == "Nay")
    return ("Yea" if y > n else "Nay" if n > y else None), y, n

# Wording for curated text about one or more roll calls the member voted the same way on, so card, stance and
# promise text never types a vote or a tally. vs: rows of data/votes.json. Placeholders:
#   {vote} Yea/Nay/...   {Vote} "Voted for" / "Voted against" / "Voted “Present” on" / "Did not vote on"
#   {yea} {nay} {dY} {dN} {rY} {rN} (first roll)   {DemMaj}/{demMaj} "Most Democrats voted no (9–187)" (Democrats' Yea–Nay)
#   {dcount} "9–187"   {dside} no/yes   {dopposed} opposed/supported/split on   {dall} "opposed by most Democrats" (every roll)
#   {brk_phrase} "breaking with most Democrats" / "voting with most Democrats"   {dsame} Democrats who voted as the member did
#   {n} rolls   {yeaCount} {nayCount}
VOTE_PHRASE = {"Yea": "Voted for", "Nay": "Voted against", "Present": "Voted “Present” on", "Not Voting": "Did not vote on"}
def own_side(v):
    """Majority side of the member's own party on a votes.json row (pSide; older files only have dSide)."""
    return v.get("pSide", v.get("dSide"))
def breaks_party(v):
    return v["member"] in ("Yea", "Nay") and own_side(v) in ("Yea", "Nay") and v["member"] != own_side(v)
def roll_phrases(vs):
    v0 = vs[0]; vote = v0["member"]
    pY, pN = v0.get("pY", v0["dY"]), v0.get("pN", v0["dN"])      # own party's Yea-Nay (Democrats for older files)
    pword = "no" if pN > pY else "yes" if pY > pN else None
    word = "no" if v0["dN"] > v0["dY"] else "yes" if v0["dY"] > v0["dN"] else None
    phrase = f"Most Democrats voted {word}" if word else "Democrats split"
    pphrase = f"Most {OWN_NAME} voted {pword}" if pword else f"{OWN_NAME} split"
    ctx = {"vote": vote if len({v["member"] for v in vs}) == 1 else None, "Vote": VOTE_PHRASE.get(vote, f"Recorded as {vote} on"),
           "yea": v0["yea"], "nay": v0["nay"], "dY": v0["dY"], "dN": v0["dN"], "rY": v0["rY"], "rN": v0["rN"],
           "cY": v0.get("cY", v0["dY"]), "cN": v0.get("cN", v0["dN"]),
           "DemMaj": f"{phrase} ({v0['dY']}–{v0['dN']})", "demMaj": f"{phrase[0].lower() + phrase[1:]} ({v0['dY']}–{v0['dN']})", "dcount": f"{v0['dY']}–{v0['dN']}",
           "pY": pY, "pN": pN, "OwnMaj": f"{pphrase} ({pY}–{pN})", "ownMaj": f"{pphrase[0].lower() + pphrase[1:]} ({pY}–{pN})", "owncount": f"{pY}–{pN}",
           "ownside": pword or "evenly", "ownopposed": {"no": "opposed", "yes": "supported"}.get(pword, "split on"),
           "ownsame": pY if vote == "Yea" else pN if vote == "Nay" else None, "party": OWN_NAME,
           "dside": word or "evenly", "dopposed": {"no": "opposed", "yes": "supported"}.get(word, "split on"),
           "brk_phrase": f"breaking with most {OWN_NAME}" if all(breaks_party(v) for v in vs) else f"voting with most {OWN_NAME}",
           "dsame": v0["dY"] if vote == "Yea" else v0["dN"] if vote == "Nay" else None,
           "n": len(vs), "yeaCount": sum(v["member"] == "Yea" for v in vs), "nayCount": sum(v["member"] == "Nay" for v in vs)}
    if all(v.get("dSide") == "Nay" for v in vs): ctx["dall"] = "opposed by most Democrats"
    elif all(v.get("dSide") == "Yea" for v in vs): ctx["dall"] = "backed by most Democrats"
    if all(own_side(v) == "Nay" for v in vs): ctx["ownall"] = f"opposed by most {OWN_NAME}"
    elif all(own_side(v) == "Yea" for v in vs): ctx["ownall"] = f"backed by most {OWN_NAME}"
    return ctx

def fill_text(t, ctx, where, problems):
    """Fills {placeholders} in curated text; a placeholder with no value is a build problem, never left in the page."""
    def rep(m):
        k = m.group(1)
        if ctx.get(k) is None: problems.append(f"{where}: no value for {{{k}}}"); return m.group(0)
        return str(ctx[k])
    return re.sub(r"\{(\w+)\}", rep, t)
