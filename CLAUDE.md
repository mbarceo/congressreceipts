# Congress Receipts: guide for Claude Code

Nonpartisan, fully sourced accountability trackers for members of Congress, published at https://congressreceipts.org as a **static site** (GitHub Pages serves `main`; merging a pull request publishes). Python scripts build JSON from official records; vanilla HTML/JS pages render it. Read `docs/architecture.md` for the whole picture and `CONTRIBUTING.md` for workflow. For adding a member, use the **add-member** skill.

## Map
- `members.json` registry of tracked members · `tr` runner · `scripts/` ONE copy of every script (stdlib-only Python 3 + a few zsh) · `template/` skeletons for a new member
- `site/` SOURCE of the member pages (`index/money/stances/votes/statements/establishment/townhalls/sources.html`, `site.js`, `site.css`)
- `<state>/<member>/` one tracker: `tracker.config.json`, `data/`, `assets/portrait.jpg`; the `.html/.js/.css` inside are **generated copies** of `site/`
- Root `index/find/attendance/leaders/backlog/about.html` + `hub.js` + `hub.css` = hub pages and shared header/footer; root `data/` = hub data
- `docs/` full documentation (architecture, pipeline, config reference, verification, how-tos, troubleshooting)

## Commands
```bash
./tr <state>/<member> <script>          # run a shared script for one member, e.g. ./tr ca/padilla build_votes
./tr <state>/<member> run_checks        # verification: must pass before any PR
python3 -I scripts/new_tracker.py --name "…" --chamber house|senate --state XX [--district N] --bioguide X000000 [--vote-id S###] --pronouns he|she|they --out <state>/<last>
python3 -I scripts/publish.py [<member path> …]    # copy site/ into member folders; stamp cache keys
python3 -m http.server 8000             # preview (pages need HTTP, not file://)
```
Rebuild order for a member: fetch votes → `build_votes` → `build_alignment`; `fetch_statements` → `fetch_statement_bodies`; `resolve_fec` → `fetch_fec` → `build_fec` → `fetch_trackaipac`; then `build_stances` → `build_promises` → `build_establishment` → `build_cards` → `build_overview` → `run_checks`.

## Non-negotiable rules
1. **Every claim links to a primary source and is checked.** Votes, tallies, dollars and ranks come from official records through scripts; curated text uses placeholders (`{Vote} {yea} {nay}`). Never type a number a source can supply.
2. **Quotes must appear verbatim in the cited page.** Verify with code (normalize whitespace, `quote in text`) before saving.
3. **Fix the data, never the checker.** If `run_checks` fails, correct the curated data. Never weaken `verify_*.py` or `claims` to pass.
4. **Pick votes by reading official titles**, not keywords. Confirm bill identity and public-law numbers on govinfo; bill numbers collide across chambers. On motions to table/refer a Nay opposes the motion; say so.
5. **Verdicts only with a stated rule** (tiles and evidence cards). Issue sections show evidence and counts.
6. **Promises come from the member's own words** (campaign site via a pre-election Wayback snapshot), not endorsers or interviews.
7. **Never publish donor names, cities or addresses**; only employer, occupation, totals. Official portrait only. Neutral wording. Pronouns: use how the member's official bio refers to them, else they/them.
8. **No secrets in the repo, in files or in chat.** API keys come from the macOS Keychain (`security …`) or env vars `FEC_API_KEY` / `CONGRESS_API_KEY` via `./tr`. Never print, log, commit or ask the user to paste a key.
9. **Raw data is not committed** (`data/raw`, `data/fec/raw`, `data/statements_raw`, `data/billstatus`, `data/geo/raw`, `data/site_raw`, `data/sources/*.html`). Never `git add -f` them.
10. **Never edit generated files** (pages inside a member folder). Edit `site/`, then run `publish.py`.
11. **Do not bypass bot protection** (senate.gov returns 403 to scripts). Use another route or tell the user.

## Git and teamwork
- Never push to `main`. One branch and one PR per task; one member per PR. Use a `git worktree` per task/session (`git worktree add ../congressreceipts-x -b branch origin/main`) because other sessions may have uncommitted work in the same folder. Stage explicit paths (`git add <paths>`), never `git add -A` in a shared folder.
- `members.json` is append-only (merge hotspot). Shared files (`site/`, `scripts/`, `hub.*`, `template/`, root hub pages) go in their own small PRs.
- `publish.py` with no arguments generates pages for **every** member in `members.json`, finished or not. Run it per member, or delete the pages it generates for unfinished members before committing.
- Do not register a member in `members.json` until their tracker passes `run_checks`.
- Do not merge or deploy; that is the maintainer's job.

## Conventions
- Scripts take no member arguments: they read `TRACKER_DIR` (set by `./tr`) and `tracker.config.json` via `scripts/config.py`. Run Python with `-I`.
- Page copy is member-neutral: tokens (`{{short}}`, `{{poss}}`), `data-only="house|senate"`; never a verb after a pronoun token.
- Roll ids are `<year>-<number>` zero-padded (`2025-006`). House `voteId` = bioguide id; Senate `voteId` = LIS id (`S413`).
- Site is dark-only; fonts Archivo, Public Sans, IBM Plex Mono; no framework, no bundler.
- Changing `site.js`, `site.css`, `hub.js` or `hub.css` requires `publish.py` so `?v=` cache keys update everywhere (a large mechanical diff is expected).
