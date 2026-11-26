# Leadership races (Senate leader vote and House Speaker vote)

`leadership.html` is a hub page with two tabs: **Senate** (Democratic leader vote, Schumer vs. Van Hollen, December 1, 2026, secret ballot) and **House** (Jeffries for Speaker, caucus nomination done on November 18 at 251 to 11, floor vote January 3, 2027). `leadership.html#senate` and `#house` open a tab. The home page has a tile for each race and the site menu has a "Leadership races" entry.

It is a hand-built hub page, not a member tracker. It is not generated from `site/` and does not use `tracker.config.json`.

## Where things are

| What | Where |
|---|---|
| The page (markup, styles, script) | `leadership.html` |
| Data the page reads | `data/leadership_senate.json`, `data/leadership_house.json`, `data/leadership_senate_polls.json` |
| Curated inputs | `data/leadership/senate_positions.csv`, `data/leadership/house_receipts.csv`, `data/leadership/whip_tracker_snapshot.json` |
| Link-check results (committed as the record) | `data/leadership/verification_senate.csv`, `data/leadership/verification_house.csv` |
| Build scripts | `scripts/build_leadership_senate.py`, `scripts/build_leadership_house.py` |
| Link checkers | `scripts/verify_leadership_senate.py`, `scripts/verify_leadership_house.py` |
| Saved pages and block list (git-ignored) | `data/raw/leadership_pages/`, `data/raw/leadership_blocked_hosts.txt` |

`data/leadership_senate_polls.json` is curated by hand. Every number in it was read on the poll's own page. There is no script for it.

## How the data flows

```
senate_positions.csv ──► verify_leadership_senate.py ──► verification_senate.csv ──┐
senate_positions.csv ──────────────────────────────────────────────────────────────┴─► build_leadership_senate.py ──► leadership_senate.json

whip_tracker_snapshot.json + house_receipts.csv ──► verify_leadership_house.py ──► verification_house.csv ──┐
whip_tracker_snapshot.json + house_receipts.csv ────────────────────────────────────────────────────────────┴─► build_leadership_house.py ──► leadership_house.json
```

```bash
python3 -I scripts/verify_leadership_senate.py   # opens each source page, slowly; writes verification_senate.csv
python3 -I scripts/verify_leadership_house.py    # same for the House
python3 -I scripts/build_leadership_senate.py    # validates the CSV, computes the counts, writes the JSON
python3 -I scripts/build_leadership_house.py
python3 -m http.server 8000                      # preview leadership.html (it needs HTTP, not file://)
```
Counts are computed by the build scripts. Never type a number the data can supply. The build scripts fail on a bad group, a missing source date, or a wrong voter count.

## What counts

- **Only public statements.** A member counts for a position only if a source shows they said it, put out a statement, or voted that way. "Leaning" reports do not count.
- **Senate.** 55 Democratic senators can vote, so 28 wins (Amy Klobuchar was elected governor and cannot vote; some outlets say 29 of 56). Schumer and Van Hollen are counted for themselves, so the totals are senators plus the candidate. Groups: `schumer`, `van_hollen`, `against_schumer` (won't back Schumer, no pick), `undecided` (said they have not decided), `no_statement` (labelled "No position stated": declined to say, or nothing found), `ineligible`.
- **House.** Groups: backs, leaning, undecided, opposed. A member the whip tracker lists but where no statement of their own was found is **tracker-only**: shown with a dashed edge and counted separately. The tracker counts 162 more Democrats with no public position; they are counted, not named. Jeffries needs a majority of those voting (218 if all 435 vote).
- **When sources disagree.** The starting points are the Democratic Whip Tracker (democraticwhiptracker.com, last captured November 20, 2026) and, for the Senate, Wikipedia's 2026 Senate Democratic Caucus leadership election page. Newer dated reports override them. Each such tile is marked "Sources disagree" (Senate: a `note` starting `DISPUTED`) or "Newer reports differ from the whip tracker" (House). Wikipedia and the whip tracker are cross-checks, not primary sources.

### `senate_positions.csv`
`name, state, role, group, is_candidate, t, w, d, stance_summary, source_url, source_outlet, source_date, receipt, note`.
`t`, `w` and `d` are what the whip tracker, Wikipedia and the original dataset said (codes S, V, A, U); the build compares them to `group` to print "Whip tracker and Wikipedia agree/differ". `receipt` is `primary` (own office or post), `news`, `list` (a news outlet's list), `stale` (before the election) or `none`. A row with a `source_url` must have a full ISO `source_date`.

### `house_receipts.csv`
`race_id, name, tracker_stance, status, source_url, source_outlet, source_date, note`. `status` starts with `verified_primary`, `verified_news…`, `conflict_with_tracker` or `not_found…`. A `not_found…` row becomes tracker-only and its link is not shown. The reader-facing sentence for each tile is written in `SUMMARY` inside `build_leadership_house.py`, with `OVERRIDE` (members moved from the tracker's group) and `DISPUTE` (the "sources disagree" text). The `note` column is internal.

## Verification: what is and is not checked (as of November 26, 2026)

The checkers open each link once, 3 seconds apart, and compare the page. They can show that a page loads, that it names the member near "Schumer"/"Van Hollen" (Senate) or "Jeffries"/"Speaker" (House), and that a quoted phrase appears word for word. **A page that names a member does not prove the position.**

| | Senate (56 rows) | House (107 names) |
|---|---|---|
| Quote matched word for word | 6 | 9 |
| Page names the member near the race | 37 | 66 |
| Link could not be read by script (tagged on the page) | 7 | 20 |
| No source | 4 (Blunt Rochester, Duckworth, Schiff, and Klobuchar who cannot vote) | 17 tracker-only |

**"Verification in progress" tag.** Tiles whose check result is `skipped_host_blocked`, `blocked`, `skipped_unreadable_site` or `fetch_failed` carry an amber tag. To clear it, replace the source with one the checker can read, then re-run the checker and the build. There is no manual-confirmation field yet; if a person confirms a link by hand, say so in the pull request and ask the maintainer how to record it.

**Sites that block scripts** (they returned 403/429 and were skipped for 24 hours): thehill.com, apnews.com, axios.com, kdvr.com, cnsmaryland.org, michiganchronicle.com, news.lee.net, news10.com, startribune.com, washingtontimes.com, wgno.com, bringmethenews.com. X posts cannot be read by script. Follow "Go slow on other people's websites" in `CLAUDE.md`: stop at the first 403 or 429, never retry in a loop, never look for a way around a block. The checkers already do this and remember blocks in `data/raw/leadership_blocked_hosts.txt`.

## Known gaps and open items

- **Refresh before each vote and freeze after.** Positions are as of November 26. Refresh before December 1 (Senate) and January 3 (House), then freeze each race with its result and keep the pre-vote snapshot.
- **The page still shows a "Draft" notice.** Remove it when the tagged tiles are confirmed.
- **Jake Johnson (MN-1).** A search summary said his race is headed to a recount, but the source site blocked the checker. It is unverified and deliberately not on the page.
- **Senate rows with no direct statement:** Schiff (trackers conflict), Duckworth, Blunt Rochester. Warner and Stratton are flagged because sources disagree.
- **Polls.** Only the Economist/YouGov and Data for Progress polls are shown. An Indivisible/YouGov poll in Wikipedia's table was left out because its page was not found.
- **Quotes.** Only the 15 word-for-word matches above are verified quotes; other tile text paraphrases a source.

## How to refresh (checklist)

1. Work in a git worktree on a new branch (see `CLAUDE.md`). Never push to `main`.
2. Re-read the whip tracker's lists and update `whip_tracker_snapshot.json`; update `senate_positions.csv` and `house_receipts.csv`. Every changed position needs a real, dated source. Do not invent a source or a quote.
3. Run the two checkers (in the background, one at a time; they take a few minutes).
4. Run the two build scripts and open `leadership.html` on both tabs, at desktop and phone width.
5. Update the verification table above if the numbers changed, then open a pull request. The maintainer merges.

## Writing rules for this page

- Do not use he, she, him or her for anyone unless the member's official bio states pronouns. Use the name.
- Neutral, descriptive wording. No verdicts, no party colors for candidates.
- The site is dark-only and uses the shared `site.css`, `hub.css` and `hub.js`. After changing `hub.js`, `hub.css` or `site.css`, run `scripts/publish.py` so cache keys update (it already stamps `leadership.html`).
