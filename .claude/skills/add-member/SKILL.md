---
name: add-member
description: Build a nonpartisan, fully sourced accountability tracker for a member of Congress (House or Senate) in this repository, from scaffold through checks and a pull request. Use when asked to add, build, start or "do" a tracker for a representative or senator, or to refresh or extend an existing member's tracker.
---

# Add a member to Congress Receipts

You are working inside the Congress Receipts repository. The project's rules are in `CLAUDE.md` (already loaded); the full procedure is in `docs/howto/add-a-member.md`. Read these before acting:

1. `docs/howto/add-a-member.md`: the step-by-step procedure (follow it in order)
2. `docs/verification.md`: the sourcing rules and the checks (never relax them)
3. `docs/config-reference.md`: formats of the curated files
4. `docs/senate-differences.md`: if the member is a senator
5. `docs/troubleshooting.md`: when something fails

## Before touching anything

- Confirm who the member is (name, chamber, state, district) and that nobody else is already building them (`data/queue.json`, open pull requests: `gh pr list`).
- Work on a new branch in its own worktree: `git fetch origin && git worktree add ../congressreceipts-<last> -b add-<state>-<last> origin/main`. Other sessions may have uncommitted work in the main folder; never mix into it.
- API keys must be available to `./tr` (macOS Keychain items `fec-api-key` and `congress-api-key`, or env vars `FEC_API_KEY` / `CONGRESS_API_KEY`). If they are missing, tell the user how to store them (CONTRIBUTING.md) and stop. Never ask the user to paste a key into the chat.

## Order of work

1. Ids and scaffold (`scripts/new_tracker.py --out <state>/<last>`). Pronouns: how the member's official bio refers to them; otherwise `they`.
2. Portrait (`./tr <member> fetch_portrait`), then open `assets/portrait.jpg` and confirm it is the current official photo.
3. Votes → statements → money → bills, each through `./tr <member> <script>`; check each result against the live source before moving on (first rows of statements, roll-call counts, FEC ids).
4. Curate: read the member's real record first (`data/votes.json`, `data/statements.json`, `data/member_bills.json`), then write `stance_picks.json`, `promises.json`, `card_picks.json`, `establishment_items.json`, `events.json`, `claims_static.json`, `bills.json`, and the `profile` block in the config. Generate these with a small script that **asserts every quote is a verbatim substring of its source's full text** before writing, and resolves release slugs to exactly one URL.
5. Rebuild in order (`build_stances` → `build_promises` → `build_establishment` → `build_cards` → `build_overview`), then `./tr <member> run_checks`. Fix data until it passes; never edit a checker.
6. Preview (`python3 -m http.server 8000`) and read every page: portrait, names, pronouns, tallies, links. Check for leftovers from other members.
7. Only when checks pass: register in `members.json`, run `python3 -I scripts/publish.py <member path>` (one member), and open a pull request containing just this member's folder and `members.json`.

## Judgment calls (what to hold to)

- Pick roll calls by reading official titles; confirm bill identity and public law on govinfo; say what a Nay means on tabling and referral motions.
- Promises are the member's own words from a pre-election Wayback snapshot, with a `why` for every status. "Stalled" means introduced or cosponsored but only referred to committee.
- Verdicts only where a rule is stated on the page. Issue sections show evidence, not conclusions.
- No donor names; official portrait only; neutral wording; leave out anything you cannot source.
- If a site blocks scripts (senate.gov 403), do not bypass it: copy Senate roll-call XML from another senator's `data/raw`, or build without statements and say so.
- A member-elect has no votes: build money, promises and campaign statements only, and do not register them in `members.json` or the queue.

## Finish

Report: what was built, which checks passed, what is not done (for example events, FEC still downloading), and the pull request link. Do not merge. Do not run the full publisher (`publish.py` with no arguments) unless asked.
