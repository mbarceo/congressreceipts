#!/usr/bin/env python3
"""Walk through the leadership source links a script could not read, so a person can confirm them by hand.

For each link the checkers could not read (see verification_house.csv / verification_senate.csv) this opens the
page in your default browser, waits, shows what we claim, and asks: y = I opened it and it supports the claim,
n = it does not, s = skip for now, q = quit. Only "y" is recorded, in data/leadership/manual_confirmations.csv
(race,name,source_url,confirmed_by,confirmed_on,note). Every answer is also kept in
data/raw/leadership_review_log.csv (git-ignored).

Polite by design (CLAUDE.md "Go slow"): one link at a time, DELAY seconds between opens, and only YOU read the page.
Nothing is fetched by this script. Rows already confirmed for the same link are skipped.
Run:  python3 -I scripts/review_leadership_links.py [house|senate] [--delay 5]
Then re-run the builds:  python3 -I scripts/build_leadership_house.py && python3 -I scripts/build_leadership_senate.py
"""
import csv, datetime, subprocess, sys, time, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LD = ROOT / "data" / "leadership"
MANUAL = LD / "manual_confirmations.csv"
LOG = ROOT / "data" / "raw" / "leadership_review_log.csv"
FIELDS = ["race", "name", "source_url", "confirmed_by", "confirmed_on", "note"]
NEEDS_HUMAN = {"skipped_host_blocked", "blocked", "skipped_unreadable_site", "fetch_failed",
               "quote_not_on_page", "name_found_only", "name_not_on_page"}
CLAIM = {"house": ("house_receipts.csv", "note"), "senate": ("senate_positions.csv", "stance_summary")}


def read(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    delay = 5.0
    if "--delay" in sys.argv:
        delay = max(3.0, float(sys.argv[sys.argv.index("--delay") + 1]))
        args = [a for a in args if a != str(sys.argv[sys.argv.index("--delay") + 1])]
    races = [a for a in args if a in CLAIM] or ["house", "senate"]
    who = input("Your name for the record (confirmed_by): ").strip() or "maintainer"
    done = {(r["race"], r["name"], r["source_url"]) for r in read(MANUAL) if r["confirmed_on"].strip()}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    new_log = not LOG.exists()
    today = datetime.date.today().isoformat()
    queue = []
    for race in races:
        src, col = CLAIM[race]
        claims = {r["name"]: r for r in read(LD / src)}
        for v in read(LD / f"verification_{race}.csv"):
            if v["result"] in NEEDS_HUMAN and v["url"] and (race, v["name"], v["url"]) not in done:
                queue.append((race, v["name"], v["url"], v["result"], (claims.get(v["name"], {}).get(col) or "")))
    print(f"\n{len(queue)} links to review. Press q any time; run again to pick up where you stopped.\n")
    for i, (race, name, url, result, claim) in enumerate(queue, 1):
        print(f"[{i}/{len(queue)}] {race.upper()}  {name}  ({result})\n  {url}\n  We claim: {claim[:300]}")
        webbrowser.open(url)
        time.sleep(delay)
        while True:
            a = input("  Does the page support this, with a date? [y]es / [n]o / [s]kip / [q]uit: ").strip().lower()[:1]
            if a in ("y", "n", "s", "q"):
                break
        if a == "q":
            break
        with LOG.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_log:
                w.writerow(["at", "race", "name", "url", "answer"]); new_log = False
            w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), race, name, url, a])
        if a == "y":
            note = input("  Optional note (press Enter to skip): ").strip()
            fresh = not MANUAL.exists() or not MANUAL.read_text().strip()
            with MANUAL.open("a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                if fresh:
                    w.writeheader()
                w.writerow({"race": race, "name": name, "source_url": url, "confirmed_by": who,
                            "confirmed_on": today, "note": note})
            print("  recorded.\n")
        else:
            print()
    print("Done. Now re-run the two build scripts (see top of this file) and tell Claude which rows were 'n'.")


if __name__ == "__main__":
    main()
