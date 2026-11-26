#!/usr/bin/env python3
"""Scaffolds a new tracker folder from this template for one member of Congress.

Copies the template, writes tracker.config.json with the member's identity and display fields (the pages read
them at runtime through site.js), bakes the member into the data skeletons, and prints the next steps (runs `git init` only outside this repo). Refuses to write into an existing non-empty folder.

Usage (from the repo root; the skeletons come from template/, the pages from site/ via scripts/publish.py):
  python3 -I scripts/new_tracker.py --name "Alex Padilla" --chamber senate --state CA --bioguide P000145 \
      --vote-id S413 --pronouns he --out ca/padilla
  python3 -I scripts/new_tracker.py --name "Luz Rivas" --chamber house --state CA --district 29 --bioguide R000620 \
      --pronouns she --area "San Fernando Valley" --out ca/rivas
(--out outside the repo also works and runs `git init` there.)

Display fields written to member (site.js derives anything missing): name, first, last, short, honorific, title,
pronouns {subj, obj, poss}, chamber, voteId, state, stateName, district, districtLabel, seatLabel, area, portrait,
site, domain, pressPath, campaignSite, congress, inOfficeSince. Curated page text (facts, committees, caucuses,
offices, handles, district map labels, Money-page notes, events text) goes in the "profile" block.
"""
import argparse, copy, json, os, re, shutil, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, "template")   # tracker.config.json and the data/ skeletons; the pages come from site/ via publish.py
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut",
          "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
          "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
          "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
          "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
          "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
          "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
          "DC": "District of Columbia", "PR": "Puerto Rico", "GU": "Guam", "VI": "U.S. Virgin Islands", "AS": "American Samoa", "MP": "Northern Mariana Islands"}
STATE_FIPS = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13",
              "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24", "MA": "25",
              "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36",
              "NC": "37", "ND": "38", "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48",
              "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56", "PR": "72"}
PRONOUNS = {"he": ("he", "him", "his"), "she": ("she", "her", "her"), "they": ("they", "them", "their")}
# Party leader per chamber: alignment peer, Establishment comparisons, Money page's leader box (build_fec.py)
LEADERS = {
    "house": {"leader": {"name": "Hakeem Jeffries", "voteId": "J000294", "title": "House Democratic leader"},
              "peer": {"id": "J000294", "name": "Hakeem Jeffries", "dist": "NY-8", "group": "Party leadership"},
              "rx": "JEFFRIES|JEFF PAC", "ids": []},
    "senate": {"leader": {"name": "Chuck Schumer", "voteId": "S270", "title": "Senate Democratic leader"},
               "peer": {"id": "S270", "name": "Chuck Schumer", "dist": "NY", "group": "Party leadership"},
               "rx": "SCHUMER|^IMPACT$", "ids": ["C00346312", "C00348607"]},
}
SKIP = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc", ".git", "new_tracker.py")


def ordinal(n):
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def poss(s):
    return s + "'" if s.lower().endswith("s") else s + "'s"


def member_fields(a):
    senate = a.chamber == "senate"
    parts = a.name.split()
    first, last = parts[0], parts[-1]
    short = a.short or last
    honorific = a.honorific or ("Sen." if senate else "Rep.")
    st = a.state.upper()
    state_name = STATES.get(st, st)
    subj, obj, ps = PRONOUNS[a.pronouns]
    slug = re.sub(r"[^a-z]", "", last.lower())
    site = (a.site or (f"https://www.{slug}.senate.gov" if senate else f"https://{slug}.house.gov")).rstrip("/")
    m = {"name": a.name, "first": first, "last": last, "short": short, "honorific": honorific, "title": f"{honorific} {a.name}",
         "pronouns": {"subj": subj, "obj": obj, "poss": ps},
         "bioguide": a.bioguide, "voteId": a.vote_id or (a.bioguide if not senate else "TODO: Senate LIS id, e.g. S413 (lis_member_id in any senate.gov vote XML)"),
         "party": a.party, "state": st, "stateName": state_name, "chamber": a.chamber}
    if senate:
        m.update({"districtLabel": st, "seatLabel": state_name, "area": a.area or state_name})
    else:
        d = str(a.district).upper().lstrip("0") or "0"
        at_large = d in ("0", "AL")
        m.update({"district": "AL" if at_large else d, "districtLabel": f"{st}-{'AL' if at_large else d}",
                  "seatLabel": f"{state_name}'s at-large district" if at_large else f"{state_name}'s {ordinal(d)} District",
                  "geoid": STATE_FIPS.get(st, "TODO") + ("00" if at_large else d.zfill(2)),
                  "area": a.area or f"{st}-{'AL' if at_large else d}"})
    m.update({"congress": a.congress, "inOfficeSince": a.since or "TODO: YYYY-MM-DD sworn in (current service)",
              "site": site, "domain": re.sub(r"^https?://(www\.)?", "", site).split("/")[0],
              "pressPath": a.press_path or ("/newsroom/press-releases" if senate else "/media/press-releases"),
              "pressLayout": "auto",
              "campaignSite": a.campaign_site or "", "portrait": "assets/portrait.jpg", "committees": []})
    return m


def tokens(m, chamber):
    """The subset of site.js display values used in page titles, descriptions, README and SCAFFOLD."""
    senate = chamber == "senate"
    return {"name": m["name"], "short": m["short"], "title": m["title"], "shortPoss": poss(m["short"]),
            "seatShort": m["stateName"] if senate else m["districtLabel"],
            "siteName": f"{m['short']} Senate Tracker" if senate else f"{m['districtLabel']} {m['short']} Tracker", "seatLabel": m["seatLabel"], "stateName": m["stateName"],
            "districtLabel": m["districtLabel"], "chamberName": "Senate" if senate else "House", "domain": m["domain"],
            "subj": m["pronouns"]["subj"], "poss": m["pronouns"]["poss"], "obj": m["pronouns"]["obj"],
            "voteId": m["voteId"], "bioguide": m["bioguide"],
            "ownPartyPl": "Republicans" if str(m.get("party", "")).lower().startswith("r") else "Democrats"}   # baked into meta descriptions


def fill(s, t):
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda x: str(t[x.group(1)]) if x.group(1) in t else x.group(0), s)


def build_config(tmpl, a, m):
    senate = a.chamber == "senate"
    L = LEADERS[a.chamber]
    cfg = copy.deepcopy(tmpl)
    cfg["_note"] = ("Member-specific values. Scripts read it through scripts/config.py; pages read member, leader and profile "
                    "through site.js. Fields starting with TODO must be filled before the step that needs them.")
    cfg["member"] = m
    cfg["leader"] = L["leader"]
    fec = cfg.setdefault("fec", {})
    cycles = [int(c) for c in a.cycles.split(",")] if a.cycles else [2024, 2026]
    fec.update({"candidateId": "TODO", "committeeId": "TODO", "cycles": cycles,
                "cycleLabels": {str(c): f"{c - 1}-{str(c)[2:]}" for c in cycles},
                "leadershipRx": L["rx"], "leadershipIds": L["ids"]})
    fec.setdefault("keyEnv", "FEC_API_KEY")
    # Industry-watch categories stay as a starting point; their one-line "why" was written for the template member
    for w in fec.get("watch", []):
        if re.search(r"\b(her|his|she|he|district)\b", w.get("why", ""), re.I):
            w["why"] = f"TODO: why this category matters for {m['short']}'s {'state' if senate else 'district'}."
    if senate:
        cfg["geo"] = {"_note": "Senators have no district map: fetch_geo.py and build_map.py are House-only, and index.html hides the map."}
    else:
        cfg["geo"] = {"_note": "County FIPS codes the district touches and a short code for each county (build_map.py colors by these).",
                      "countyFips": [], "counties": {}, "padLon": 0.035, "padLat": 0.03}
    cfg["statements"] = {"localTerms": "", "defaultLang": "en",
                         "_note": "localTerms: |-separated place names that mark a release as local news (lowercase)."}
    cfg["peers"] = [L["peer"]]
    cfg["_peersNote"] = ("Members to compare with on the Overview and Money pages: {id, name, dist, group}. id is the vote id "
                         "(bioguide for the House, LIS id for the Senate). Groups appear in config order; the build counts "
                         "'Party leadership', 'Centrist' and 'Progressive' in its summary.")
    cfg["profile"] = {
        "_note": ("Curated page text, rendered by the pages at runtime. Strings allow [label](url), **bold** and {{tokens}} "
                  "(e.g. {{short}}, {{poss}}). Every fact typed here also goes in data/claims_static.json with its source."),
        "lede": "", "facts": [], "factSources": [], "committees": [], "committeesNote": "", "caucuses": [],
        "promiseYear": "", "promisesIntro": "",
        "offices": [], "online": [], "onlineNote": "", "handles": [], "channelsNote": "",
        "money": {"watchIntro": "", "trackaipacNote": ""},
        "events": {"intro": "", "help": "", "ask": ""},
        "_examples": {
            "facts": [{"label": "Background", "value": "..."}, {"label": "2024 general", "value": "Won 60.1% to 39.9% over ..."}],
            "factSources": ["2024 general (certified): ... [Secretary of State](https://...)"],
            "committees": [{"name": "Judiciary Committee", "subs": [{"name": "... Subcommittee", "role": "Ranking member"}], "blurb": "What it oversees. [Source](https://...)"}],
            "caucuses": [["Congressional Progressive Caucus", "Member"]],
            "offices": [{"name": "Washington, D.C. office", "lines": ["...", "Washington, DC 20510"], "phone": "(202) 224-0000", "note": "Best for votes and legislation."}],
            "online": ["[Contact form](https://...)"],
            "handles": [{"platform": "X", "office": {"text": "@...", "url": "https://x.com/..."}, "campaign": {"text": "@...", "url": "https://x.com/..."}}],
        },
    }
    if senate:
        cfg["profile"]["state"] = {"heading": "", "intro": "", "facts": [], "note": "",
                                   "_note": "Optional statewide context shown in place of the House district map; hidden while intro and facts are empty."}
    else:
        cfg["profile"]["map"] = {"heading": "", "intro": "", "note": "", "modes": [{"key": "new", "label": "New lines"}, {"key": "old", "label": "Current lines"}],
                                 "population": None, "kinds": {}, "neighbors": [], "smallLabels": [],
                                 "_note": "modes: build_map.py writes 'new' (cd120) and 'old' (cd119). population: {mode, total, parts: [[kind, label, residents, note]], source}."}
    return cfg


def main():
    ap = argparse.ArgumentParser(description="Scaffold a new legislator tracker from the template.")
    ap.add_argument("--name", required=True, help='Full name as displayed, e.g. "Alex Padilla"')
    ap.add_argument("--chamber", required=True, choices=["house", "senate"])
    ap.add_argument("--state", required=True, help="Two-letter state code, e.g. CA")
    ap.add_argument("--district", help="House district number (AL or 0 for at-large); House only")
    ap.add_argument("--bioguide", required=True, help="Bioguide ID, e.g. P000145")
    ap.add_argument("--vote-id", help="Senate LIS member id (e.g. S413); House defaults to the bioguide")
    ap.add_argument("--pronouns", required=True, choices=sorted(PRONOUNS), help="Pronouns used in page copy")
    ap.add_argument("--out", required=True, help="New folder to create")
    ap.add_argument("--party", default="Democrat")
    ap.add_argument("--short", help="Short name used in copy (default: last name)")
    ap.add_argument("--honorific", help='Default "Rep." or "Sen."')
    ap.add_argument("--area", help='Place phrase for voters, e.g. "San Fernando Valley" (default: district label or state name)')
    ap.add_argument("--site", help="Official site (default guessed: https://<last>.house.gov or https://www.<last>.senate.gov)")
    ap.add_argument("--press-path", help="Press-release list path on the official site")
    ap.add_argument("--campaign-site")
    ap.add_argument("--since", help="Sworn in for current service, YYYY-MM-DD")
    ap.add_argument("--congress", type=int, default=119)
    ap.add_argument("--cycles", help="FEC cycles, comma-separated even years (resolve_fec.py can rewrite them), default 2024,2026")
    a = ap.parse_args()

    a.state = a.state.upper()
    if a.state not in STATES: ap.error(f"unknown state code {a.state}")
    if a.chamber == "house" and not a.district: ap.error("--district is required for the House")
    if a.chamber == "senate" and a.district: ap.error("--district is House only")
    if not re.fullmatch(r"[A-Z]\d{6}", a.bioguide): ap.error("--bioguide looks wrong (expected a letter and 6 digits, e.g. P000145)")
    out = os.path.abspath(os.path.expanduser(a.out))
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        sys.exit(f"Refusing to write into {out}: it exists and is not empty.")

    shutil.copytree(TEMPLATE, out, ignore=SKIP, dirs_exist_ok=True)
    os.makedirs(os.path.join(out, "data", "fec"), exist_ok=True)
    m = member_fields(a)
    tmpl = json.load(open(os.path.join(TEMPLATE, "tracker.config.json")))
    cfg = build_config(tmpl, a, m)
    with open(os.path.join(out, "tracker.config.json"), "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False); f.write("\n")

    # Bake titles/descriptions (for link previews) and fill the docs; the pages fill the rest at runtime from the config
    t = tokens(m, a.chamber)
    head_rx = re.compile(r"(<title>.*?</title>|<meta name=\"description\" content=\"[^\"]*\">)", re.S)
    for fn in os.listdir(out):
        p = os.path.join(out, fn)
        if fn.endswith(".html"):
            s = open(p, encoding="utf-8").read()
            open(p, "w", encoding="utf-8").write(head_rx.sub(lambda x: fill(x.group(0), t), s))
        elif fn in ("README.md", "SCAFFOLD.md"):
            s = open(p, encoding="utf-8").read()
            open(p, "w", encoding="utf-8").write(fill(s, t))
    os.makedirs(os.path.join(out, "assets"), exist_ok=True)

    in_repo = os.path.commonpath([out, REPO]) == REPO       # a member folder inside this repo must not get its own .git
    if in_repo:
        git = "inside this repo: no git init (commit it with the rest of the repo)"
    else:
        try:
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=out, check=True)
            git = "git init -b main done"
        except (OSError, subprocess.CalledProcessError) as e:
            git = f"git init failed ({e}); run `git init -b main` yourself"

    senate = a.chamber == "senate"
    q = lambda s: f'"{s}"' if " " in s else s
    rel = os.path.relpath(out, REPO)
    run = (lambda s: f"./tr {rel} {s}") if in_repo else (lambda s: f"python3 -I scripts/{s}.py")
    steps = [
        *([f"Add {rel} to members.json (format \"shared\", chamber, voteId, portrait \"assets/portrait.jpg\") with \"live\": false, so nothing publishes; remove the flag once run_checks passes."] if in_repo else [f"cd {q(out)}"]),
        "Check tracker.config.json: member.site/pressPath (guessed), inOfficeSince, committees, peers; fill the profile block as you research.",
        "Portrait (always): " + run("fetch_portrait") + ", then open assets/portrait.jpg to confirm it is the current official photo.",
        ("Votes: " + (run("fetch_votes_senate") if senate else (f"./tr {rel} fetch_votes" if in_repo else "./scripts/fetch_votes.sh"))
         + " && " + run("build_votes") + " && " + run("build_alignment")),
        "Statements: " + run("fetch_statements") + " (add a row parser if the press page layout is new), then " + run("fetch_statement_bodies"),
        "Money: " + run("resolve_fec") + ", then " + run("fetch_fec") + " and " + run("build_fec") + "; then " + run("fetch_trackaipac")
        + (" (six-year term: resolve_fec writes every cycle of the current term)" if senate else ""),
        *([] if senate else ["District map: set geo.countyFips/counties, then " + run("fetch_geo") + " && " + run("build_map")]),
        "Curate data/stance_picks.json, card_picks.json, promises.json, establishment_items.json, events.json, claims_static.json",
        "Rebuild: build_stances -> build_promises -> build_establishment -> build_cards -> build_overview; then " + run("run_checks"),
        ("Publish the pages: python3 -I scripts/publish.py " + rel + " (one member only), then preview with python3 -m http.server 8000"
         if in_repo else "Preview: python3 -m http.server 8000, open http://localhost:8000"),
    ]
    print(f"Created {out} for {m['title']} ({t['seatShort']}). {git}.")
    if senate and m["voteId"].startswith("TODO"): print("Warning: --vote-id not given; set member.voteId (Senate LIS id) before fetching votes.")
    print("Next steps:")
    for i, s in enumerate(steps, 1): print(f"  {i}. {s}")


if __name__ == "__main__":
    main()
