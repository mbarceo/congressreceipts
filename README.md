# Congress Receipts

Nonpartisan, fully sourced accountability trackers for members of Congress, at **https://congressreceipts.org**.
Every claim links to its source, and every vote, tally, quote and dollar figure is checked against the official record.

## Layout

```
index.html, data/attendance.json   the home page ("Who shows up": attendance, critical votes, town halls)
members.json                       every member: folder, chamber, vote id, format
site/                              shared pages, site.js, site.css (edit here, never in a member folder)
scripts/                           shared build and verification scripts (one copy for every member)
tr                                 runs a shared script for one member: ./tr ca/padilla build_votes
ca/<member>/                       one member: tracker.config.json, data/, assets/, and the published pages
```

A member's URL is its folder: `congressreceipts.org/ca/padilla/`.

## Common tasks

- Rebuild one member: `./tr ca/padilla build_votes` (then build_alignment, build_stances, build_promises,
  build_establishment, build_cards, build_overview), then `./tr ca/padilla run_checks`.
- Publish the shared pages to every member after editing `site/`: `python3 -I scripts/publish.py`.
- Rebuild the home page after any member changes: `python3 -I scripts/build_attendance.py`.
- Add a member: scaffold with `scripts/new_tracker.py --out ca/<last>`, delete the copied `scripts/` and page
  files from the new folder, add it to `members.json` with format "shared", then follow the build steps.

Unfinished members: set `"live": false` on a member in `members.json` and `publish.py`, the attendance, leaders and directory builds all skip them. Remove the flag once `./tr <member> run_checks` passes.

API keys (FEC, congress.gov) are read from the macOS Keychain by `./tr`; they are never stored in this repo.

## Formats

`shared` members use `site/` and `scripts/`. `legacy` members (ca/rivas, ca/tran) still carry their own pages and
scripts from before the move and are being converted to the shared format.

Raw downloads (official vote XML, FEC files with donor addresses, press-release pages) stay out of git; see `.gitignore`.
