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

## Documentation

Start at [docs/README.md](docs/README.md). New collaborator? Read [CONTRIBUTING.md](CONTRIBUTING.md). Using Claude Code? `CLAUDE.md` and the `add-member` skill load automatically.

- [Architecture](docs/architecture.md) · [Data pipeline](docs/pipeline.md) · [Config and file formats](docs/config-reference.md) · [Sourcing standards and checks](docs/verification.md) · [Troubleshooting](docs/troubleshooting.md)

## Go slow on other people's websites

Blocks from government sites and the FEC key's hourly cap cost hours for everyone. Space requests a few seconds apart, never crawl in bursts, stop at the first 403 or 429, and run one FEC download at a time. Full rules are in [CLAUDE.md](CLAUDE.md), which Claude Code reads automatically.

## Common tasks

- Rebuild one member: `./tr ca/padilla build_votes` (then build_alignment, build_stances, build_promises,
  build_establishment, build_cards, build_overview), then `./tr ca/padilla run_checks`.
- Publish the shared pages to every member after editing `site/`: `python3 -I scripts/publish.py`.
- Rebuild the home page after any member changes: `python3 -I scripts/build_attendance.py`.
- Add a member: scaffold with `python3 -I scripts/new_tracker.py --out ca/<last> ...` (it copies the skeletons from `template/`; the
  pages come from `site/` when you publish), then follow [docs/howto/add-a-member.md](docs/howto/add-a-member.md).

Unfinished members: set `"live": false` on a member in `members.json` and `publish.py`, the attendance, leaders and directory builds all skip them. Remove the flag once `./tr <member> run_checks` passes.

API keys (FEC, congress.gov) are read from the macOS Keychain or the `FEC_API_KEY` / `CONGRESS_API_KEY` environment variables by `./tr`; they are never stored in this repo.

## Formats

`shared` members use `site/` and `scripts/` (every member today). `legacy` is the older layout, where a member kept its own pages
and scripts; it is still supported by `./tr` and `publish.py` but no member uses it now.

Raw downloads (official vote XML, FEC files with donor addresses, press-release pages) stay out of git; see `.gitignore`.
