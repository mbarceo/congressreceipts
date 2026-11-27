#!/usr/bin/env python3
"""Build data/leadership_house.json for the House Speaker tab of leadership.html.

Inputs:  data/leadership/whip_tracker_snapshot.json  (names, districts and the tracker's position for each)
         data/leadership/house_receipts.csv          (source row for each name)
         data/leadership/verification_house.csv      (result of verify_leadership_house.py)
Output:  data/leadership_house.json      Usage: python3 -I scripts/build_leadership_house.py   (see docs/leadership.md)

Rules
- A member counts toward a position only if a source we found shows it. Names the tracker lists but where no
  statement of their own was found are counted separately ("tracker only").
- Where newer reports differ from the tracker (last checked Nov 20), the newer report decides and the tile says so.
- Summaries are written for readers and avoid gendered pronouns (positions come from official bios, never names).
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "data" / "leadership" / "whip_tracker_snapshot.json"
REC = ROOT / "data" / "leadership" / "house_receipts.csv"
OUT = ROOT / "data"

TRACKER_GROUPS = {"declared_for": "backs", "leaning_for": "leaning", "undecided": "undecided", "opposed": "opposed"}

# Newer reports put these members in a different position than the tracker (last checked Nov 20).
OVERRIDE = {n: "backs" for n in ["Daniel Biss", "Christina Bohannan", "Lindsay James", "Jake Johnson",
                                   "Eileen Laubacher", "Adelita Grijalva", "Pramila Jayapal"]}

SUMMARY = {
    # Opposed
    "Darializa Avila Chevalier": "Voted no at the Nov 18 caucus vote and signed a joint statement citing Medicare for All and Gaza.",
    "Angela Gonzales-Torres": "Says the answer is no for now; reported among the 11 no votes.",
    "Adam Hamawy": "Voted no at the Nov 18 caucus vote and signed the joint statement.",
    "Frederick Haynes III": "Signed the joint statement but missed the caucus vote while ill; the office says the intended vote was no.",
    "Melat Kiros": "Voted no at the caucus vote and signed the joint statement. Earlier said the vote was up in the air.",
    "Don Leonard": "Withholding support until demands are met, including ending support for Israel and the Iran war.",
    "Donavan McKinney": "Voted no at the caucus vote; says talks with Jeffries are encouraging and hopes to support in January.",
    "Chris Rabb": "Voted no at the caucus vote; reportedly hopes to support Jeffries in January.",
    "Claire Valdez": "Voted no at the caucus vote to force an open debate; praised Jeffries' Medicare push.",
    # Leaning
    "Jim Himes": "Publicly says Jeffries will win the gavel; no pledge found.",
    # Newer reports say these back Jeffries
    "Daniel Biss": "Said in a Nov 18 post that Biss supported Jeffries at the caucus vote, with conditions.",
    "Christina Bohannan": "Reported backing Jeffries at the caucus vote, with the other Iowa Democrats.",
    "Lindsay James": "Reported backing Jeffries at the caucus vote, with the other Iowa Democrats.",
    "Jake Johnson": "Said after meeting Jeffries that Johnson will vote for Jeffries.",
    "Eileen Laubacher": "Voted yes at the caucus vote, per the Colorado roll call; earlier declined to say.",
    "Adelita Grijalva": "Reported as having voted for Jeffries; says Jeffries is the only candidate.",
    "Pramila Jayapal": "Voted for Jeffries at the caucus vote, with conditions on Medicare for All and immigration.",
    # Undecided
    "Paul Barringer": "Says conversations come first before deciding.",
    "Victoria Broderick": "Not saying yes or no; has set conditions for Jeffries.",
    "Zach Dembo": "Undecided; says bipartisanship will matter and would not back a candidate seen as overly partisan.",
    "Sam Forstag": "Not committing either way.",
    "Patty Garcia": "Says the vote will be united with the progressive caucus.",
    "Chuck Hubbard": "Says nothing against Jeffries but wants to talk first.",
    "Cyril Jefferson": "Wants to meet Jeffries first but can't think of anyone better for the job.",
    "Analilia Mejia": "Declined to commit in spring 2026; no newer statement found.",
    "Richard Ojeda": "Still having conversations and listening.",
    "Delia Ramirez": "Wants leadership to make it easy to vote for the only candidate; pressing for a floor vote on the Block the Bombs Act.",
    "Randy Villegas": "Wants assurances, including a floor vote on Medicare for All, before backing anyone.",
    "Fred Wellman": "Says the decision isn't made and does not intend to be a rubber stamp.",
    "LaKesha Womack": "Named among the North Carolina holdouts who met Jeffries.",
}

DISPUTE = {
    "Daniel Biss": "The whip tracker lists Biss undecided. A Nov 18 post says Biss supported Jeffries at the caucus vote.",
    "Christina Bohannan": "The whip tracker lists Bohannan undecided. CBS2 Iowa reports Bohannan backs Jeffries.",
    "Lindsay James": "The whip tracker lists James undecided. CBS2 Iowa reports James backs Jeffries.",
    "Jake Johnson": "The whip tracker lists Johnson undecided. Axios reports Johnson said Johnson will vote for Jeffries after meeting Jeffries.",
    "Eileen Laubacher": "The whip tracker lists Laubacher undecided. KDVR's roll call shows a yes vote at the caucus.",
    "Adelita Grijalva": "The whip tracker lists Grijalva undecided. Reports describe Grijalva as having voted for Jeffries.",
    "Pramila Jayapal": "The whip tracker lists Jayapal as leaning. Reports say Jayapal voted for Jeffries, with conditions.",
    "Donavan McKinney": "Voted no at the caucus vote but says talks with Jeffries are encouraging and hopes to support in January.",
    "Chris Rabb": "Voted no at the caucus vote but reportedly hopes to support Jeffries in January.",
    "Frederick Haynes III": "Not among the 11 no votes because of an illness, but signed the joint statement of opposition.",
    "Don Leonard": "Leonard alleges threats from unnamed senior Democrats; the claim is unverified. Reports differ on whether Leonard voted no at the caucus vote.",
}


def dist(entry):
    m = re.search(r"\(([^)]+)\)\s*$", entry)
    return m.group(1) if m else ""


def base(entry):
    return re.sub(r"\s*\([^)]*\)\s*$", "", entry).strip()


def date_text(raw):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", raw or "")
    if m:
        return raw
    m = re.match(r"(\d{4})-(\d{2})", raw or "")
    return f"{m.group(1)}-{m.group(2)}" if m else ""



def load_manual(race):
    """Links a person opened and read by hand (the checker could not). Matched by name AND the source_url
    the row has now, so changing a source drops the confirmation. Columns: race,name,source_url,confirmed_by,confirmed_on,note."""
    f = ROOT / "data" / "leadership" / "manual_confirmations.csv"
    if not f.exists():
        return {}
    with f.open(encoding="utf-8") as fh:
        return {r["name"]: r for r in csv.DictReader(fh) if r["race"] == race and r["confirmed_on"].strip()}

def main():
    snap = json.loads(SNAP.read_text(encoding="utf-8"))["house_speaker"]
    tracker = {}
    for key, grp in TRACKER_GROUPS.items():
        for e in snap[key]:
            tracker[base(e)] = (grp, dist(e))

    with REC.open(encoding="utf-8") as f:
        recs = {r["name"]: r for r in csv.DictReader(f)}

    vfile = ROOT / "data" / "leadership" / "verification_house.csv"
    manual = load_manual("house")
    checks = {}
    if vfile.exists():
        with vfile.open(encoding="utf-8") as f:
            checks = {c["name"]: c["result"] for c in csv.DictReader(f)}
    members, errors = [], []
    for name, (tgroup, district) in tracker.items():
        if name == "Hakeem Jeffries":
            continue  # the candidate
        r = recs.get(name)
        if not r:
            errors.append(f"no receipt row for {name}")
            continue
        status = r["status"]
        tracker_only = status.startswith("not_found")
        if status.startswith("verified_primary"):
            receipt = "primary"
        elif status.startswith("verified_news_stale"):
            receipt = "stale"
        elif tracker_only:
            receipt = "none"
        else:
            receipt = "news"
        group = OVERRIDE.get(name, tgroup)
        if tracker_only:
            summary = {"backs": "Listed by the whip tracker as backing Jeffries; no statement of their own found.",
                       "leaning": "Listed by the whip tracker as leaning toward Jeffries; no statement found.",
                       "undecided": "Listed by the whip tracker as undecided; no statement found."}.get(group, "")
        else:
            summary = SUMMARY.get(name) or ("Own statement backing Jeffries for Speaker." if receipt == "primary" and group == "backs"
                                            else "Backs Jeffries for Speaker.")
        members.append({
            "name": name, "district": district, "group": group, "tracker_group": tgroup,
            "tracker_only": tracker_only, "summary": summary,
            "source_url": "" if tracker_only else r["source_url"],
            "source_outlet": "" if tracker_only else r["source_outlet"],
            "source_date": "" if tracker_only else date_text(r["source_date"]),
            "receipt": receipt,
            "disputed": name in DISPUTE, "dispute_note": DISPUTE.get(name, ""),
            "differs_from_tracker": group != tgroup,
            "check": "none_to_check" if tracker_only else checks.get(name, "not_run"),
            "manual_confirmed_on": "" if tracker_only or name not in manual or manual[name]["source_url"] != r["source_url"] else manual[name]["confirmed_on"],
        })

    if errors:
        raise SystemExit("ERRORS: " + "; ".join(errors))

    order = {"backs": 0, "leaning": 1, "undecided": 2, "opposed": 3}
    members.sort(key=lambda m: (order[m["group"]], m["tracker_only"], m["name"].split()[-1]))

    counts = {g: {"sourced": sum(1 for m in members if m["group"] == g and not m["tracker_only"]),
                  "tracker_only": sum(1 for m in members if m["group"] == g and m["tracker_only"])} for g in order}
    data = {
        "as_of": "2026-11-26",
        "tracker_last_checked": "2026-11-20",
        "caucus": {"date": "2026-11-18", "yes": 251, "no": 11,
                   "source_url": "https://time.com/article/2026/11/18/hakeem-jeffries-picked-by-democrats-first-black-speaker-of-the-house/",
                   "source_outlet": "TIME"},
        "floor_vote": "2027-01-03",
        "no_public_position": snap["no_public_position_count"],
        "counts": counts,
        "check_counts": dict(Counter(m["check"] for m in members)),
        "checks_run": "2026-11-26" if checks else None,
        "members": members,
    }
    (OUT / "leadership_house.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print("members:", len(members), "| no public position:", data["no_public_position"])
    for g in order:
        print(f"  {g}: {counts[g]['sourced']} sourced + {counts[g]['tracker_only']} tracker-only")
    print("differs from tracker:", [m["name"] for m in members if m["differs_from_tracker"]])
    print("disputed:", len([m for m in members if m["disputed"]]))
    pron = re.compile(r"\b(he|she|his|her|hers|him|himself|herself)\b", re.I)
    for m in members:
        for k in ("summary", "dispute_note"):
            t = re.sub(r'"[^"]*"', "", m[k])
            if pron.search(t):
                print("PRONOUN:", m["name"], k, "|", m[k])


if __name__ == "__main__":
    main()
