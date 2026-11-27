#!/usr/bin/env python3
"""Build data/leadership_senate.json (the Senate tab of leadership.html) from data/leadership/senate_positions.csv.

Counts are computed here, never typed by hand. Run after editing senate_positions.csv or re-running
verify_leadership_senate.py.   Usage: python3 -I scripts/build_leadership_senate.py
See docs/leadership.md.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "leadership" / "senate_positions.csv"
OUT = ROOT / "data" / "leadership_senate.json"

AS_OF = "2026-11-26"
VOTE_DATE = "2026-12-01"
VOTES_TO_WIN = 28
ELIGIBLE_VOTERS = 55

GROUPS = ["schumer", "van_hollen", "against_schumer", "undecided", "no_statement", "ineligible"]
RECEIPTS = {"primary", "news", "list", "stale", "none"}

# The tracker files every Van Hollen backer under "opposed to Schumer" but names Van Hollen
# in its Backing column. Troy Jackson is the exception: the tracker still shows "no pick".
TRACKER_NO_PICK = {"Troy Jackson"}

GROUP_TO_CODES = {
    "schumer": {"S"},
    "van_hollen": {"V"},
    "against_schumer": {"A"},
    "undecided": {"U"},
    "no_statement": {"U"},
    "ineligible": {"U"},
}
WIKI_OK = {
    "schumer": {"S"},
    "van_hollen": {"V"},
    "against_schumer": {"A"},
    "undecided": {"U", "unknown"},
    "no_statement": {"unknown", "U"},
    "ineligible": {"none"},
}


def agreement(row):
    group = row["group"]
    if row["is_candidate"] == "yes":
        return {"tracker": "candidate", "wikipedia": "candidate"}
    t = row["t"]
    if group == "van_hollen" and row["name"] not in TRACKER_NO_PICK:
        t = "V"
    t_ok = t in GROUP_TO_CODES[group]
    w = row["w"]
    w_ok = (w in WIKI_OK[group]) if w else None
    return {
        "tracker": "agrees" if t_ok else "differs",
        "wikipedia": None if w is None or w == "" else ("agrees" if w_ok else "differs"),
    }



def load_manual(race):
    """Links a person opened and read by hand (the checker could not). Matched by name AND the source_url
    the row has now, so changing a source drops the confirmation. Columns: race,name,source_url,confirmed_by,confirmed_on,note."""
    f = ROOT / "data" / "leadership" / "manual_confirmations.csv"
    if not f.exists():
        return {}
    with f.open(encoding="utf-8") as fh:
        return {r["name"]: r for r in csv.DictReader(fh) if r["race"] == race and r["confirmed_on"].strip()}

def main():
    with SRC.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    errors = []
    members = []
    for r in rows:
        if r["group"] not in GROUPS:
            errors.append(f"{r['name']}: bad group {r['group']}")
        if r["receipt"] not in RECEIPTS:
            errors.append(f"{r['name']}: bad receipt {r['receipt']}")
        if r["receipt"] in ("primary", "news", "list", "stale") and not r["source_url"]:
            errors.append(f"{r['name']}: receipt {r['receipt']} but no source_url")
        if r["source_url"] and not r["source_date"]:
            errors.append(f"{r['name']}: source_url but no source_date")
        note = r["note"]
        disputed = note.startswith("DISPUTED")
        if disputed:
            note = note.split(":", 1)[1].strip() if ":" in note else note
            note = note[:1].upper() + note[1:]
        members.append({
            "name": r["name"],
            "state": r["state"],
            "role": r["role"],
            "group": r["group"],
            "is_candidate": r["is_candidate"] == "yes",
            "summary": r["stance_summary"],
            "source_url": r["source_url"],
            "source_outlet": r["source_outlet"],
            "source_date": r["source_date"],
            "receipt": r["receipt"],
            "note": note,
            "disputed": disputed,
            "agreement": agreement(r),
        })

    # Attach the script check from verify_senate_quotes.py, if it has been run.
    vfile = ROOT / "data" / "leadership" / "verification_senate.csv"
    manual = load_manual("senate")
    checks = {}
    if vfile.exists():
        with vfile.open(encoding="utf-8") as f:
            checks = {c["name"]: c for c in csv.DictReader(f)}
    for m in members:
        c = checks.get(m["name"])
        m["check"] = c["result"] if c else "not_run"
        m["quotes_found"] = int(c["quotes_found"] or 0) if c else 0
        m["quotes_total"] = int(c["quotes_total"] or 0) if c else 0
        mc = manual.get(m["name"])
        m["manual_confirmed_on"] = mc["confirmed_on"] if mc and mc["source_url"] == m["source_url"] else ""

    names = [m["name"] for m in members]
    dupes = [n for n, c in Counter(names).items() if c > 1]
    if dupes:
        errors.append(f"duplicate names: {dupes}")

    counts = Counter(m["group"] for m in members)
    voters = sum(c for g, c in counts.items() if g != "ineligible")
    if voters != ELIGIBLE_VOTERS:
        errors.append(f"eligible voters computed {voters}, expected {ELIGIBLE_VOTERS}")

    schumer_senators = sum(1 for m in members if m["group"] == "schumer" and not m["is_candidate"])
    vh_senators = sum(1 for m in members if m["group"] == "van_hollen" and not m["is_candidate"])

    if errors:
        print("ERRORS:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    data = {
        "as_of": AS_OF,
        "vote_date": VOTE_DATE,
        "votes_to_win": VOTES_TO_WIN,
        "eligible_voters": ELIGIBLE_VOTERS,
        "counts": {g: counts.get(g, 0) for g in GROUPS},
        "schumer_total": schumer_senators + 1,
        "van_hollen_total": vh_senators + 1,
        "schumer_senators": schumer_senators,
        "van_hollen_senators": vh_senators,
        "checks_run": "2026-11-26" if checks else None,
        "check_counts": dict(Counter(m["check"] for m in members)),
        "members": members,
    }

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"members: {len(members)}  eligible voters: {voters}")
    print("counts:", data["counts"])
    print(f"Schumer {data['schumer_total']} (incl. himself)  Van Hollen {data['van_hollen_total']} (incl. himself)")
    print("disputed:", [m["name"] for m in members if m["disputed"]])
    stale = [m["name"] for m in members if m["receipt"] == "stale"]
    none = [m["name"] for m in members if m["receipt"] == "none"]
    print("stale receipts:", stale)
    print("no receipt:", none)
    diff = [(m["name"], m["agreement"]) for m in members
            if "differs" in (m["agreement"]["tracker"], m["agreement"]["wikipedia"])]
    print("rows that differ from tracker or Wikipedia:")
    for n, a in diff:
        print("  ", n, a)


if __name__ == "__main__":
    main()
