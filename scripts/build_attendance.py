"""Builds data/attendance.json for the hub page: missed votes and public events for every member in hub.config.json.

For each member it reads two independent sources and refuses to build if they disagree:
  1. the tracker's own data/votes.json (what the tracker shows), and
  2. the official roll-call XML in the tracker's data/raw (House Clerk or senate.gov), counted fresh here.
Chamber context (median missed rate, how many members missed fewer) is computed from the same official XML over
every member who was eligible for at least 80% of the roll calls, so partial-term members don't skew it. Ties count:
"missed fewer" is a strict comparison. Events come from the tracker's data/events.json (or data/townhalls.json in
older trackers) and keep their source links. Portraits and links point into each member's folder.
Usage: python3 -I scripts/build_attendance.py
"""
import collections, glob, json, os, re, shutil, statistics, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo; the hub is its home page
CFG = json.load(open(os.path.join(ROOT, "members.json")))
CFG.setdefault("title", "Congress Receipts: Who Shows Up")
problems = []

def vote_url(chamber, y, n):
    if chamber == "senate":
        session = y - 2025 + 1           # 119th Congress: 2025 is session 1
        return f"https://www.senate.gov/legislative/LIS/roll_call_votes/vote119{session}/vote_119_{session}_{n:05d}.htm"
    return f"https://clerk.house.gov/Votes/{y}{n:03d}"

def official_counts(chamber, raw):
    """Votes cast and missed per member id, from the official XML files."""
    cast, missed, files = collections.Counter(), collections.Counter(), 0
    pat = "senate-*.xml" if chamber == "senate" else "*-roll*.xml"
    for f in sorted(glob.glob(os.path.join(raw, pat))):
        r = ET.parse(f).getroot(); files += 1
        if chamber == "senate":
            rows = ((m.findtext("lis_member_id"), m.findtext("vote_cast")) for m in r.iter("member"))
        else:
            rows = ((rv.find("legislator").get("name-id"), rv.findtext("vote")) for rv in r.iter("recorded-vote"))
        for mid, v in rows:
            cast[mid] += 1; missed[mid] += (v == "Not Voting")
    return cast, missed, files

VOTE_RX = re.compile(r"clerk\.house\.gov/Votes/(\d{4})(\d{1,4})\b|senate\.gov/legislative/LIS/roll_call_votes/vote1\d\d(\d)/vote_1\d\d_\d_(\d{5})")

def roll_id(u):
    m = VOTE_RX.search(u or "")
    if not m: return None
    if m.group(1): return f"{m.group(1)}-{int(m.group(2)):03d}"
    return f"{2024 + int(m.group(3))}-{int(m.group(4)):03d}"     # 119th Congress: session 1 = 2025

def critical_rolls(path):
    """The votes a tracker treats as critical: every official roll call its Stances page and evidence cards cite,
    with the issue it is filed under. Reads data/stances.json and data/cards.json, and the STANCES list inside
    stances.html for older trackers (Derek Tran's)."""
    picks = {}
    add = lambda u, topic: (lambda i: i and picks.setdefault(i, topic))(roll_id(u))
    sp = os.path.join(path, "data/stances.json")
    if os.path.exists(sp):
        st = json.load(open(sp))
        for iss in st.get("issues", []):
            for r in iss.get("rolls", []): add(r.get("url") or (vote_url_from_id(r["id"]) if r.get("id") else ""), iss["name"])
            for it in iss.get("items", []):   # curated record items (dated actions, some of them roll calls)
                for u in [it.get("u")] + list(it.get("more") or []) + list(it.get("also") or []): add(u if isinstance(u, str) else (u or {}).get("u"), iss["name"])
        for it in st.get("israel", {}).get("items", []): add(it.get("u"), "Israel and Palestine")
    cp = os.path.join(path, "data/cards.json")
    if os.path.exists(cp):
        for c in json.load(open(cp)).get("cards", []):
            for it in c.get("items", []):
                for u in [it.get("u")] + list(it.get("more") or []): add(u, CARD_TOPIC.get(c.get("key"), c.get("eb") or c.get("q", "")))
    hp = os.path.join(path, "stances.html")
    if not os.path.exists(sp) and os.path.exists(hp):
        for t, u in re.findall(r'\{t:"([^"]+)"[^\n]*?u:"([^"]+)"', open(hp).read()): add(u, t)
    return picks

# Card types under the same issue names every tracker uses (older cards carry only their question)
CARD_TOPIC = {"ice": "Immigration and ICE", "police": "Public safety", "corporate": "Money and business", "palestine": "Israel and Palestine"}
vote_url_from_id = lambda i: f"https://clerk.house.gov/Votes/{i[:4]}{int(i[5:]):03d}"

chambers = {}
out = []
for m in (x for x in CFG["members"] if x.get("live", True)):
    path = os.path.join(ROOT, m["path"])
    m["url"] = m["path"] + "/"   # relative, so it works on congressreceipts.org and in a local preview
    votes = json.load(open(os.path.join(path, "data/votes.json")))
    key = "member" if "member" in votes[0] else next(k for k in votes[0] if k not in
          {"y", "n", "date", "bill", "q", "desc", "type", "result", "yea", "nay", "dY", "dN", "rY", "rN", "iY", "iN", "cY", "cN", "dSide", "rSide", "url", "title"})
    mine = [v for v in votes if v[key] == "Not Voting"]
    cast, missed, nfiles = official_counts(m["chamber"], os.path.join(path, "data/raw"))
    if cast[m["voteId"]] != len(votes) or missed[m["voteId"]] != len(mine):
        problems.append(f"{m['name']}: tracker shows {len(mine)} missed of {len(votes)}, official XML has {missed[m['voteId']]} of {cast[m['voteId']]}")
    full = max(cast.values())
    rates = {k: missed[k] / cast[k] for k in cast if cast[k] >= 0.8 * full}
    rate = len(mine) / len(votes)
    ch = chambers.setdefault(m["chamber"], {"rolls": full, "members": len(rates), "median": round(statistics.median(rates.values()) * 100, 1),
                                             "through": max(v["date"] for v in votes)})
    if full != ch["rolls"]:
        problems.append(f"{m['name']}: {full} roll calls, but another {m['chamber']} tracker has {ch['rolls']}; refetch the older tracker's votes")
    # Events: newer trackers keep data/events.json; Derek Tran's older tracker keeps data/townhalls.json
    ev = []
    for f in ("data/events.json", "data/townhalls.json"):
        p = os.path.join(path, f)
        if os.path.exists(p):
            d = json.load(open(p)); ev = d.get("events", []) if isinstance(d, dict) else d; break
    stm = {}
    sp = os.path.join(path, "data/statements.json")
    if os.path.exists(sp): stm = {s["u"]: s for s in json.load(open(sp))}
    events = []
    for e in ev:
        src = e.get("source") or e.get("u")
        if not src and e.get("stmt"):
            hits = [u for u in stm if e["stmt"] in u]
            src = hits[0] if len(hits) == 1 else None
        if not src: problems.append(f"{m['name']}: event {e.get('date')} has no source"); continue
        t = e.get("type") or ("Town hall" if re.search(r"town hall", e.get("title", ""), re.I) else "Event")
        events.append({"date": e["date"], "type": t, "title": e.get("title", ""), "city": e.get("city", ""), "role": e.get("role", ""),
                       "approx": e.get("approx", ""), "source": src})
    events.sort(key=lambda e: e["date"], reverse=True)
    if not os.path.exists(os.path.join(path, m["portrait"])): problems.append(f"{m['name']}: no portrait at {m['path']}/{m['portrait']}")
    # Critical votes: how the member voted on each one the tracker cites, against the Democratic majority's side
    by = {f'{v["y"]}-{v["n"]:03d}': v for v in votes}
    crit = []
    for rid, topic in critical_rolls(path).items():
        v = by.get(rid)
        if not v: problems.append(f"{m['name']}: critical roll {rid} not in votes.json"); continue
        me, side = v[key], v.get("dSide", "")
        status = ("missed" if me == "Not Voting" else "present" if me == "Present"
                  else "broke" if side in ("Yea", "Nay") and me != side else "with")
        crit.append({"id": rid, "date": v["date"], "topic": topic, "bill": v.get("bill", ""), "desc": (v.get("desc") or v.get("title") or "")[:200],
                     "q": v.get("q", ""), "vote": me, "dSide": side, "status": status, "result": v.get("result", ""),
                     "url": v.get("url") or vote_url(m["chamber"], v["y"], v["n"])})
    crit.sort(key=lambda c: c["date"])
    out.append({"name": m["name"], "critical": crit, "party": m["party"], "seat": m["seat"], "chamber": m["chamber"], "url": m["url"], "portrait": f"{m['path']}/{m['portrait']}",
                "rolls": len(votes), "missed": len(mine), "present": sum(1 for v in votes if v[key] == "Present"),
                "rate": round(rate * 100, 1), "fewer": sum(1 for r in rates.values() if r < rate),
                "missedVotes": [{"date": v["date"], "bill": v.get("bill", ""), "q": v.get("q", ""), "desc": (v.get("desc") or v.get("title") or "")[:180],
                                 "url": v.get("url") or vote_url(m["chamber"], v["y"], v["n"])} for v in sorted(mine, key=lambda v: v["date"], reverse=True)],
                # Town halls with constituents: "town hall" in the type or title, not a national TV broadcast (Derek Tran's CNN one)
                "townHalls": sum(1 for e in events if re.search(r"town hall", e["type"] + " " + e["title"], re.I) and not re.search(r"televised|broadcast", e["type"], re.I)),
                "eventsResearched": m.get("eventsResearched", True),
                "events": events})
if problems: raise SystemExit("Not built:\n  " + "\n  ".join(problems))
json.dump({"title": CFG["title"], "chambers": chambers, "members": out}, open(os.path.join(ROOT, "data/attendance.json"), "w"), indent=1, ensure_ascii=False)
for x in out:
    c = chambers[x["chamber"]]
    print(f'{x["name"]:14} {x["seat"]:7} missed {x["missed"]:3}/{x["rolls"]} ({x["rate"]}%), median {c["median"]}%, {x["fewer"]} of {c["members"]} missed fewer; '
          f'{x["townHalls"]} town halls, {len(x["events"])} events')
