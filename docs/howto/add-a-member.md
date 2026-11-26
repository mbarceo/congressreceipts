# How to add a member

Time: a few hours of work spread over a day or two, mostly waiting on downloads and curating. If you use Claude Code, the bundled **add-member** skill (`.claude/skills/add-member/`) walks through exactly these steps; just say "add a tracker for Rep. Jane Doe".

Before you start, read [verification.md](../verification.md): the sourcing rules apply to everything you curate.

## 0. Prepare

- Work on a branch, ideally in its own worktree so other work in your checkout is untouched:
  ```bash
  git fetch origin
  git worktree add ../congressreceipts-<last> -b add-<state>-<last> origin/main
  cd ../congressreceipts-<last>
  ```
- Have your FEC and congress.gov API keys set up ([CONTRIBUTING.md](../../CONTRIBUTING.md#api-keys)).
- Check `data/queue.json` and open pull requests so nobody else is already building this member.

## 1. Collect the ids

| You need | Where to find it |
|---|---|
| **Bioguide id** (`G000598`) | `data/congress.json` (search the name) or bioguide.congress.gov. A letter and six digits |
| **Senate LIS id** (`S390`), senators only | `<lis_member_id>` in any senate.gov roll-call XML. If another senator's tracker is already downloaded, `grep -A8 "Van Hollen (D-MD)" ca/padilla/data/raw/senate-2025-00001.xml` |
| **Pronouns** | The way the member's official biography refers to them. If you cannot confirm, use `they` |
| **Official site and press path** | The member's `.house.gov` / `.senate.gov` site. The press list is usually `/media/press-releases` (House) or `/newsroom/press-releases` (Senate) |

## 2. Scaffold

```bash
python3 -I scripts/new_tracker.py --name "Robert Garcia" --chamber house --state CA --district 42 \
    --bioguide G000598 --pronouns he --site https://robertgarcia.house.gov --out ca/garcia

python3 -I scripts/new_tracker.py --name "Chris Van Hollen" --chamber senate --state MD \
    --bioguide V000128 --vote-id S390 --pronouns he --short "Van Hollen" --out md/van-hollen
```

Folder = `<state>/<last-name>`, lowercase, hyphenated. The script writes `tracker.config.json` and the `data/` skeletons from `template/` and prints the remaining steps with the right `./tr` commands. It does not run `git init` inside the repo.

Then open `tracker.config.json` and check `member.site`, `pressPath` (both are guesses), `inOfficeSince`, `leader`, `peers`. Set `profile` as you research (committees, facts, offices); every fact typed there also needs a `claims_static.json` entry.

**Add the member to `members.json` now, with `"live": false`** . The easy way is to add `--register` to the scaffold command above: it appends the entry and refreshes the queue. By hand, use `format: "shared"`, `pages: "stub"`, `chamber`, `voteId`, `portrait: "assets/portrait.jpg"`, `eventsResearched: false`. While `live` is `false`, `publish.py` and the attendance, leaders and directory builds skip the member, so nothing unfinished goes public. Everything below runs through `./tr` and works either way.

## 3. Portrait (always)

```bash
./tr ca/garcia fetch_portrait
```
Open `ca/garcia/assets/portrait.jpg` and confirm it is the current official photo. It uses bioguide first (kept current). If the image is small and a larger official portrait exists, replace it and keep `portraitSource` accurate. Never use an unofficial photo.

## 4. Votes

```bash
./tr ca/garcia fetch_votes                # House: ~690 roll calls per Congress; a few minutes
./tr md/van-hollen fetch_votes_senate     # Senate
./tr ca/garcia build_votes
./tr ca/garcia build_alignment
```
Senate roll-call files are identical for every senator. If senate.gov answers scripts with HTTP 403, copy `senate-*.xml` from another senator's `data/raw/` into the new member's `data/raw/`. For a House or Senate member, check the roll count against another member of the same chamber; `build_attendance` refuses to build if they differ.

## 5. Statements

```bash
./tr ca/garcia fetch_statements           # add --max-pages 3 for a quick first pass
./tr ca/garcia fetch_statement_bodies
```
Check the first rows against the live press page. If the script reports 0 rows or "Unrecognized layout", the site needs a parser: [add-a-press-layout.md](add-a-press-layout.md). If the site returns 403 to scripts you cannot scrape it; ask a maintainer.

## 6. Money and bills

```bash
./tr ca/garcia resolve_fec        # once; writes the FEC ids into the config
./tr ca/garcia fetch_fec          # slow and rate-limited; re-run to resume
./tr ca/garcia build_fec
./tr ca/garcia fetch_trackaipac
./tr ca/garcia fetch_bills
```
If `resolve_fec` finds several candidates it writes nothing: set `fec.candidateId` and `fec.committeeId` by hand (look the member up on fec.gov). Run **one member's `fetch_fec` at a time**; the API key is limited to about 1,000 calls an hour and a senator needs several thousand calls in total.

House members also need the district map: set `geo.countyFips` and `geo.counties`, then `fetch_geo` and `build_map`.

## 7. Curate

This is the editorial work. Each file's format is in [config-reference.md](../config-reference.md); each skeleton in `data/` has a `_note`.

1. **Read first.** List the member's votes (`data/votes.json`) and release titles (`data/statements.json`), then pick issues the member actually works on. Read the official titles of the bills; do not pick by keyword.
2. **`stance_picks.json`**: 6 to 10 issue sections with a mix of roll calls (`roll` + `{Vote}` text) and statements (`u` + an exact quote `q`), plus the Israel/Palestine card.
3. **`promises.json`**: the member's own campaign promises, from a Wayback snapshot of their campaign site. Use `member_bills.json` to find the bills behind each promise. Add every bill you cite to `bills.json`.
4. **`card_picks.json`, `establishment_items.json`, `events.json`, `claims_static.json`** as the skeletons describe.

Quotes must be verbatim. A quick way to guarantee that is to assert it in code before saving: load `statements_full.json`, normalize whitespace, and check `quote in text`.

## 8. Rebuild and check

```bash
./tr ca/garcia build_stances
./tr ca/garcia build_promises
./tr ca/garcia build_establishment
./tr ca/garcia build_cards
./tr ca/garcia build_overview
./tr ca/garcia run_checks
```
Fix the data until every check passes. Never edit a checker to make a claim pass.

## 9. Publish for this member only

1. When `./tr ca/garcia run_checks` passes, **remove `"live": false`** from the member in `members.json` (keep entries append-only to avoid merge conflicts).
2. `python3 -I scripts/publish.py ca/garcia` generates the member's pages.
3. Preview: `python3 -m http.server 8000`, open `http://localhost:8000/ca/garcia/`. Read every page.
4. Rebuild the hub if you want the member on it ([rebuild-the-hub.md](rebuild-the-hub.md)).
5. Run `python3 -I scripts/build_queue.py` so `data/queue.json` shows the member as `done` with their URL ([update-the-queue.md](update-the-queue.md)).
6. Commit and open a pull request: **one member per pull request**, and do not include raw data. See [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Special case: a member-elect with no votes yet

A senator- or representative-elect has no roll calls, no bioguide id and no press page on an official site. Scaffold with a placeholder bioguide (`X000000`) and `--vote-id TODO`, build only what exists (money, campaign promises from an archived site, campaign statements), keep `"live": false` on the `members.json` entry and leave the queue alone until they are sworn in.
