# Congress Receipts: guide for Claude Code

Nonpartisan, fully sourced accountability trackers for members of Congress, published at https://congressreceipts.org as a **static site** (GitHub Pages serves `main`; merging a pull request publishes). Python scripts build JSON from official records; vanilla HTML/JS pages render it. Read `docs/architecture.md` for the whole picture and `CONTRIBUTING.md` for workflow. For adding a member, use the **add-member** skill.

## Map
- `members.json` registry of tracked members · `tr` runner · `scripts/` ONE copy of every script (stdlib-only Python 3 + a few zsh) · `template/` skeletons for a new member
- `site/` SOURCE of the member pages (`index/money/stances/votes/statements/establishment/townhalls/sources.html`, `site.js`, `site.css`)
- `<state>/<member>/` one tracker: `tracker.config.json`, `data/`, `assets/portrait.jpg`; the `.html/.js/.css` inside are **generated copies** of `site/`
- Root `index/find/attendance/leaders/leadership/backlog/about.html` + `hub.js` + `hub.css` = hub pages and shared header/footer; root `data/` = hub data
- Leadership races (Senate leader vote, House Speaker vote): `leadership.html`, `data/leadership_*.json`, curated inputs in `data/leadership/`, scripts `scripts/build_leadership_*.py` and `scripts/verify_leadership_*.py`. Read `docs/leadership.md` before touching them. `AGENTS.md` is the entry point for non-Claude agents.
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

## Go slow on other people's websites

Government sites (senate.gov offices, house.gov, clerk.house.gov, govinfo, congress.gov) and the FEC API use bot protection and rate limits. On 2026-11-25 a burst of requests got both our scripts and the maintainer's own Chrome blocked on vanhollen.senate.gov, and the FEC key hit its hourly cap twice. Being blocked costs hours and blocks everyone, so:

- **One request at a time, a few seconds apart** (scripts already sleep 2 s between press-list pages; keep that). No parallel requests to the same host, and no loops of dozens of pages in one go.
- **Never paste or run a page-crawling loop in a browser console.** A browser on the maintainer's connection is still their connection.
- **Stop at the first 403 or 429.** Do not retry in a loop, rotate headers, or look for a way around the block. Wait hours, then resume slowly. Raw pages are cached under `data/` so a rerun picks up where it stopped.
- **Prefer official bulk and API sources** over scraping pages: roll-call XML (Clerk, senate.gov vote XML), govinfo BILLSTATUS, the congress.gov API, the FEC API.
- **FEC key: one member at a time.** The key allows about 1,000 calls an hour. Do not run two `fetch_fec` jobs together; if the cap is hit, wait the hour.
- **Verification scripts fetch live pages too** (`verify_all`, `verify_bills`). Run them once per change, not in a loop.
- **Fetch only what the tracker needs.** For press releases, the current Congress is usually enough.
- If you are blocked: stop, tell the maintainer, and move on to work that does not touch that site.

## Non-negotiable rules
1. **Every claim links to a primary source and is checked.** Votes, tallies, dollars and ranks come from official records through scripts; curated text uses placeholders (`{Vote} {yea} {nay}`). Never type a number a source can supply.
2. **Quotes must appear verbatim in the cited page.** Verify with code (normalize whitespace, `quote in text`) before saving.
3. **Fix the data, never the checker.** If `run_checks` fails, correct the curated data. Never weaken `verify_*.py` or `claims` to pass.
4. **Pick votes by reading official titles**, not keywords. Confirm bill identity and public-law numbers on govinfo; bill numbers collide across chambers. On motions to table/refer a Nay opposes the motion; say so.
5. **Verdicts only with a stated rule** (tiles and evidence cards). Issue sections show evidence and counts.
6. **Promises come from the member's own words** (campaign site via a pre-election Wayback snapshot), not endorsers or interviews.
7. **Never publish donor names, cities or addresses**; only employer, occupation, totals. Official portrait only. Neutral wording. Pronouns: use how the member's official bio refers to them, else they/them.
8. **No secrets in the repo, in files or in chat.** API keys come from the macOS Keychain (`security …`) or env vars `FEC_API_KEY` / `CONGRESS_API_KEY` via `./tr`. Never print, log, commit or ask the user to paste a key.
9. **Official roll-call XML IS committed**, once per chamber and Congress, in `data/rollcalls/<house|senate>/<congress>/` (every member reads the same files; never copy them into a member folder). Other raw data is not committed (`data/raw`, `data/fec/raw`, `data/statements_raw`, `data/billstatus`, `data/geo/raw`, `data/site_raw`, `data/sources/*.html`). Never `git add -f` them. `fetch_votes` / `fetch_votes_senate` only add missing files to the shared folder.
10. **Never edit generated files** (pages inside a member folder). Edit `site/`, then run `publish.py`.
11. **Do not bypass bot protection** (senate.gov returns 403 to scripts). Stop at the first 403/429 and follow "Go slow" above; use another route or tell the user.

## Git and teamwork
- Never push to `main`. One branch and one PR per task; one member per PR. Use a `git worktree` per task/session (`git worktree add ../congressreceipts-x -b branch origin/main`) because other sessions may have uncommitted work in the same folder. Stage explicit paths (`git add <paths>`), never `git add -A` in a shared folder.
- `members.json` is append-only (merge hotspot). Shared files (`site/`, `scripts/`, `hub.*`, `template/`, root hub pages) go in their own small PRs.
- A member whose tracker is not finished gets `"live": false` in `members.json`: `publish.py` and the attendance, leaders and directory builds all skip them, so nothing publishes. Remove the flag only after `./tr <member> run_checks` passes.
- Do not merge or deploy; that is the maintainer's job.

## Conventions
- Scripts take no member arguments: they read `TRACKER_DIR` (set by `./tr`) and `tracker.config.json` via `scripts/config.py`. Run Python with `-I`.
- Page copy is member-neutral: tokens (`{{short}}`, `{{poss}}`), `data-only="house|senate"`; never a verb after a pronoun token.
- Roll ids are `<year>-<number>` zero-padded (`2025-006`). House `voteId` = bioguide id; Senate `voteId` = LIS id (`S413`).
- Site is dark-only; fonts Archivo, Public Sans, IBM Plex Mono; no framework, no bundler.
- Changing `site.js`, `site.css`, `hub.js` or `hub.css` requires `publish.py` so `?v=` cache keys update everywhere (a large mechanical diff is expected).
