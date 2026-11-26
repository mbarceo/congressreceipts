# Troubleshooting

## Downloads

**`HTTP Error 403: Forbidden` from senate.gov (votes or press releases)**
senate.gov sits behind bot protection that blocks scripted requests, and sometimes browser panes driven by automation as well. **Stop at the first 403: do not retry in a loop, rotate headers or look for a way around it** (a burst of requests once got both the scripts and the maintainer's own Chrome blocked for hours). Wait, then resume slowly.
- *Votes*: Senate roll-call files are identical for every senator and committed once in `data/rollcalls/senate/<congress>/`; nothing to copy. If a recent vote is missing, a maintainer adds the file there.
- *Press releases*: there is no supported workaround in the scripts (page 0 is always re-fetched from the site; only pages 1 and up are cached). Do not try to defeat the protection. Tell a maintainer, or build the tracker without statements for now and say so in the pull request.

**`FEC rate limit hit. Wait an hour or set FEC_API_KEY`**
You hit the hourly cap (about 10 calls an hour with `DEMO_KEY`, about 1,000 with a real key). Make sure the key is set (`./tr` supplies it from the Keychain, or export `FEC_API_KEY`). Finished files are kept; re-run the same command after an hour. Run one member at a time; two downloads share one key's quota.

**`No FEC key in the Keychain`**
Store it once: `security add-generic-password -U -a "$USER" -s fec-api-key -w` (same for `congress-api-key`), or export `FEC_API_KEY` / `CONGRESS_API_KEY` (Linux, WSL).

**`resolve_fec` says "Not unique, so nothing was written"**
Several candidates matched (common for shared surnames). Look the member up on fec.gov and set `fec.candidateId` and `fec.committeeId` in `tracker.config.json` by hand. Check `fec.cycles` too.

**`fetch_statements` prints `0 statements`, `IndexError`, or "Unrecognized press-release list layout"**
The site's markup differs from the known layouts. See [add-a-press-layout](howto/add-a-press-layout.md).

**`fetch_votes` seems stuck or slow**
It downloads one file per roll call (about 690 for a Congress) and stops after three missing numbers in a row. It skips files already present, so you can stop and resume.

## Building and checking

**`Not built: …` from `build_attendance.py`**
Its message names the cause: a member's `votes.json` disagrees with the official XML (re-run `fetch_votes` and `build_votes`), two members of a chamber cover different roll-call ranges (refetch the older tracker's votes), an event has no source, or a portrait file is missing. It reads the shared `data/rollcalls/` folders; see [rebuild-the-hub](howto/rebuild-the-hub.md).

**`release '<slug>' matched 0 entries` / `matched N entries`** (`build_promises`, `build_stances`)
A `stmt` value must be a substring of exactly one release URL in `statements.json`. Use the slug as it appears after `/press-releases/` (run `grep slug data/statements.json`).

**`no value for {name}` / unfilled `{placeholder}`**
A curated text used a placeholder the build cannot fill for that roll call (for example `{yea}` on an item with no `roll`). Add the `roll` or remove the placeholder.

**A claim fails in `run_checks`**
Open the Sources page data (`data/verification.json`) for that claim to see why: the quote is not in the release text, the vote or tally does not match, the bill role is wrong, or a required term is missing from the saved source. Fix the curated data. Never edit the checker.

**A bill's public law looks wrong**
govinfo BILLSTATUS can list a law against the wrong chamber's bill (it once listed S. 766's law on H.R. 766). Open the law's text at `https://www.govinfo.gov/content/pkg/PLAW-119publ<N>/html/PLAW-119publ<N>.htm` and confirm it is the bill you mean before writing "became law".

## Pages and publishing

**The page is blank or shows "not built yet"**
Serve over HTTP (`python3 -m http.server 8000`); opening the file directly breaks `fetch`. "Not built yet" means the data file for that section does not exist: run the build step that produces it ([pipeline](pipeline.md)).

**My change does not show on the live site**
Merged to `main`? Pages updates in about a minute. Did you run `publish.py` after editing `site/`, `hub.js` or the CSS (so copies and `?v=` keys updated)? Hard-refresh the browser.

**`publish.py` created pages for a member who is not ready**
Set `"live": false` on that member in `members.json`; `publish.py` and the attendance, leaders and directory builds then skip them. Delete the pages already generated (`git clean -fd <member folder>`). See [publish-and-deploy](howto/publish-and-deploy.md).

**`git status` lists `data/raw` (or other raw folders)**
They should be ignored. If a raw folder is a symlink (for example into a scratch cache), the `.gitignore` entries without a trailing slash (`**/data/raw`) cover it. Never `git add -f` raw data.

## Git

**Conflict in `members.json`**
Two people appended entries. Keep both entries (valid JSON: commas between objects), then `git add members.json && git rebase --continue`.

**Another Claude Code session changed my files**
Two sessions in one folder share uncommitted changes. Use one `git worktree` per task ([CONTRIBUTING.md](../CONTRIBUTING.md#working-rules-how-not-to-step-on-each-other)). To commit only some of the changes, `git add <paths>` explicitly instead of `git add -A`.

**I committed a donor name or a key**
Stop and tell a maintainer before pushing. If it was pushed, the history must be rewritten and any exposed key must be revoked and replaced.
