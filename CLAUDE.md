# Working in this repo (read first)

Congress Receipts builds fully sourced trackers for members of Congress. See README.md for layout and commands.

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

## Other house rules

- Edit shared pages in `site/` and shared scripts in `scripts/`, never a member's generated copy. Run any script for a member with `./tr <state>/<member> <script>`.
- A member whose tracker is not finished gets `"live": false` in `members.json` so nothing publishes.
- Never commit raw downloads, API keys or donor names. Sourcing rules are in the `legislator-tracker` skill's `references/standards.md`.
- Several people (and several Claude sessions) may share one folder: make your changes on your own branch, commit only files you changed, and use `git worktree` rather than switching branches under someone else.
