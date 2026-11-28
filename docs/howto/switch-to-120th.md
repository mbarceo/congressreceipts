# Switching Find your rep to the 120th Congress (January 2027)

**Short answer:** it is a small, one-day job, not a large rework, but it cannot be done by one flag today. `build_directory.py` is hard-wired to the 119th Congress, and a few things need hand work. Find your rep keeps showing 119th seats, with a banner saying so, until the 120th Congress is sworn in on **January 3, 2027**.

## Why we wait

Members who lost or retired are still the legal representatives until January 3, and several states (for example California, with new maps) change districts. Showing 120th seats now would point a ZIP code at someone who is not yet their representative.

## What changes

| Piece | Today (119th) | At the switch |
|---|---|---|
| `data/directory.json` | House Clerk `MemberData.xml` (seats now) plus senators from the newest Senate roll-call XML | Same sources, rebuilt after the Clerk publishes the new roster and the first 2027 Senate roll call exists. Mostly automatic. |
| `data/zips.json` | Census ZCTA-to-**119th**-district file (`tab20_cd11920_zcta520_natl.txt`, column `GEOID_CD119_20`) | Needs a ZIP-to-120th-district file. We have not confirmed that Census has published a 120th-district ZIP file yet; check before the switch. This is the one input we do not control. |
| ZIP lookup in `find.html` | Reads the two JSON files | No code change. |
| Home cards, attendance, leaders | Built from `members.json` and the directory | Rebuild with the hub scripts after the directory. |
| Tracker headers | `tracker.config.json` `congress`, `district`, `districtLabel` | Per member, when sworn in (Senate switches for Moore, Letlow, Hern, Barr, Hageman and Pappas too: `chamber`, `seat`, `voteId`). |
| Banner in `find.html` | Says 119th | Remove it in the same PR. |

## Is one `--congress 120` rebuild enough?

For the directory and ZIP lookup, nearly. `build_directory.py` now takes `--congress N` (default 119) and `--zcta-url`:

```bash
python3 -I scripts/build_directory.py --congress 120
```

It reads the Census ZIP file `tab20_cd12020_zcta520_natl.txt` (column `GEOID_CD120_20`), the Clerk's `MemberData.xml`, and the newest Senate roll call in `data/rollcalls/senate/120/`. **Checked 2026-11-28: Census has not published this file.** The `rel2020/cd-sld/` folder lists only 118th and 119th ZIP files, and the guessed 120th URL returns 404. Re-check the folder before the switch and pass `--zcta-url` if the file appears under a different name. If it never appears, the fallback is to compute ZIP-to-district from the 120th boundaries that `fetch_geo.py` already pulls from TIGERweb (the layer trackers use for new-district maps); that would be a new script.

## Fallback if Census never publishes a 120th ZIP file

Only needed if the `rel2020/cd-sld/` folder still has no 120th file in late December.

**The script exists:** `scripts/build_zips_from_tiger.py` (stdlib only; needs `tigerweb.geo.census.gov`, allowed in the cloud environment since 2026-11-28; throttled two seconds per request; raw tiles cached in git-ignored `data/geo/raw/zips/`).

```bash
python3 -I scripts/build_zips_from_tiger.py --changed --congress 120          # dry run: lists changed states and how many ZIP rows differ
python3 -I scripts/build_zips_from_tiger.py --changed --congress 120 --write  # replaces those rows in data/zips.json
python3 -I scripts/build_zips_from_tiger.py --validate UT --congress 119      # accuracy check against the committed 119th rows
```

**What it does.**
1. Finds states whose districts changed by comparing each district's land area in the 119th and 120th TIGERweb layers. On 2026-11-28 that flagged AL, CA, FL, IL, LA, MO, NC, OH, SC, TN, TX and UT. Some may be tiny boundary corrections rather than new maps; recomputing them is harmless.
2. Keeps every ZIP row for the other states.
3. For each changed state, downloads district shapes and ZIP areas, samples a grid of points inside each ZIP area, and lists a district when at least 0.2% of the points fall in it (and always the district with the most).
4. A ZIP that also touches an unchanged state keeps that state's seats.

**How accurate.** Checked against the committed 119th rows for Utah: 300 of 304 ZIPs match (98.7%). The four misses each omit a thin sliver district that the Census file lists. The method never invented a district in that test. Treat the result as a stand-in: the page already says a ZIP can cross district lines, and the Census file replaces it as soon as it exists. Only Utah has been validated; run `--validate` on one more changed state before publishing, and do not publish computed rows if agreement is clearly worse.

Record in `data/directory.json` `sources.zips` that the changed states' rows are computed from TIGERweb, not the Census relationship file.

**Effort.** Script done. A full `--changed` run is a few hours of throttled requests (Texas and California are the big ones); run it on Marilyn's Mac or in the cloud, one state at a time.

## What cannot be prepared before January 3

- The Clerk's member list and first 2027 Senate roll call do not exist until the new members are sworn in, so the final directory cannot be built early.
- The six House members who won Senate seats switch chamber, seat and `voteId` only when sworn in.
- Each tracker's `district`, `chamber` and `voteId` changes go in per-member PRs after that.

## Roll-out

Merging to `main` publishes, so the roll-out is the merge of one small PR: directory rebuild, hub rebuild, banner removed. Prepare the branch with the steps above on January 3 (or just before, if the Clerk list is already live), then Marilyn merges.

## Mismatch we already have on purpose

Some trackers show the district a member **won for 2027**, which differs from the 119th seat Find your rep lists:

- **Linda Sánchez**: tracker says CA-41 (2027 map); in the 119th she holds CA-38.
- **Ken Calvert**: tracker says he won the redrawn CA-40; the 119th directory lists him in CA-41.

Both are accurate for their own date. The banner on Find your rep explains the difference; the tracker headers should say "2027 district" wording when edited next.

```mermaid
flowchart LR
  A[Jan 3, 2027 sworn in] --> B[Add --congress option, point ZIPs at 120th file]
  B --> C[build_directory.py]
  C --> D[Hub rebuild: home, attendance, leaders]
  D --> E[Remove banner in find.html]
  A --> F[Per member: config district/chamber/voteId]
  F --> G[./tr member run_checks, publish.py]
```

Order and effort: steps B to E are one small shared-files PR (about half a day, mostly waiting on the ZIP file). Step F is a few minutes per member and goes in one PR per member as usual.
