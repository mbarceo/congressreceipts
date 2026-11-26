# Configuration and file formats

Every file below is JSON. Skeletons for a new member are in `template/`; each curated skeleton has a `_note` field explaining itself. Fields starting with `_` are comments and are ignored.

## `members.json` (the registry)

```json
{ "members": [
  { "path": "ca/padilla", "name": "Alex Padilla", "party": "D", "seat": "Senate",
    "chamber": "senate", "voteId": "S413", "format": "shared",
    "portrait": "assets/portrait.jpg", "oldRepo": "ca-sen-padilla-tracker", "eventsResearched": false }
]}
```

| Field | Meaning |
|---|---|
| `path` | Folder and URL: `<state>/<last-name>` in lowercase (`md/van-hollen`) |
| `chamber` | `house` or `senate` |
| `voteId` | The id roll-call files use: **bioguide id for the House** (`R000620`), **LIS member id for the Senate** (`S413`). Find a LIS id in any senate.gov vote XML (`<lis_member_id>`) |
| `format` | `shared` (all new members) or `legacy` |
| `pages` | `stub` (use for every new member): the member's pages are thin stubs that load the shared pages in `site/` through `site/shell.js`, so a site change never touches the member folder. Omit for the older layout where `publish.py` copies `site/` pages, `site.js` and `site.css` into the folder |
| `portrait` | Path inside the member folder |
| `eventsResearched` | `false` until town halls and events have been collected; the hub shows it as such |
| `live` | `false` keeps the member out of every build and publish (pages, attendance, leaders, directory) until `run_checks` passes. Omit it, or use `true`, for a finished tracker |
| `oldRepo` | Old per-member repo that now only redirects (optional) |

`publish.py`, `build_attendance.py`, `build_leaders.py` and `build_directory.py` all read this file. Entries with `"live": false` are skipped by all of them, so register a member early with the flag set and remove it when the tracker is finished (see [publish-and-deploy](howto/publish-and-deploy.md)).

## `data/queue.json` (Backlog Queue page)

```json
{ "R000620": { "status": "done", "url": "https://congressreceipts.org/ca/rivas/" },
  "G000598": { "status": "progress" } }
```
Entries for tracked members are generated from `members.json` by `scripts/build_queue.py` (`done` + `url` when live and on the hub, otherwise `progress`); do not hand-edit them. Keyed by **bioguide id** of a sitting member (the page lists everyone in `data/congress.json`). `status`: `done`, `progress`, `next` or `skip`; anyone not listed is "Not started". Add `url` once the tracker is live. Someone who has been elected but not yet sworn in has no bioguide id and cannot be listed.

## `<member>/tracker.config.json`

| Block | Purpose |
|---|---|
| `member` | Identity and display values. `name`, `first`, `last`, `short` (used in copy), `honorific`, `title`, `pronouns {subj,obj,poss}`, `bioguide`, `voteId`, `party`, `state`, `stateName`, `chamber`, `district`/`districtLabel`/`seatLabel` (House), `area`, `congress`, `inOfficeSince`, `site`, `domain`, `pressPath`, `pressLayout` (`auto`, `house-evo`, `wp-jetengine`, `wp-elementor`), `campaignSite`, `portrait`, `committees` |
| `leader` | The party leader to compare with: `name`, `voteId`, `title` (House: Jeffries `J000294`; Senate: Schumer `S270`) |
| `fec` | `candidateId`, `committeeId`, `cycles` (even years; House: first race and current; Senate: every cycle of the current term), `cycleLabels`, `leadershipRx` and `leadershipIds` (the leader's committees), `leaders` (`house` / `senate` lists), `watch` (industry categories shown on the Money page: `id`, `label`, `why`, `rx`) |
| `geo` | House only: county FIPS codes and labels for the district map. Senators: a note only |
| `statements` | `localTerms` (a `|`-separated list marking a release as local news), `defaultLang` |
| `peers` | Colleagues to compare with: `{id, name, dist, group}`. `id` is a vote id; `group` is `Party leadership`, `Centrist` or `Progressive` |
| `profile` | The curated text on the Overview: `lede`, `facts`, `factSources`, `committees`, `caucuses`, `offices`, `online`, `handles`, Money-page notes, events text, and (House) district-map labels or (Senate) `state` context |
| `overview` | Verdict-tile settings: `costPromise`, `themes`, `votes` |

Strings in `profile` allow `[label](url)`, `**bold**` and `{{tokens}}`. **Every fact typed into `profile` also goes in `claims_static.json` with its source.**

### Page-copy tokens

`site.js` fills `{{name}}`, `{{short}}`, `{{title}}`, `{{honorific}}`, `{{subj}}`/`{{obj}}`/`{{poss}}` (and capitalized `{{Subj}}`…), `{{chamberName}}`, `{{seatLabel}}`, `{{districtLabel}}`, `{{stateName}}`, `{{area}}`, `{{domain}}`, `{{voteSource}}`, `{{leaderName}}` and more (the full list is at the top of `site/site.js`). Write copy so a verb never follows a pronoun token ("Where {{short}} stands", not "Where {{subj}} stands") so "they" still reads correctly. `data-only="house"` or `data-only="senate"` on an element hides it in the other chamber; `data-if="key"` hides it when the value is empty.

## Curated data files

### `stance_picks.json` → Stances page
```json
{ "issues": [ { "id": "immigration", "name": "Immigration and ICE", "intro": "One or two neutral sentences.",
    "statementRx": "", "rolls": [], "statementPicks": [],
    "items": [
      { "d": "2025-01-22", "roll": "2025-023", "t": "{Vote} the Laken Riley Act (S. 5). It passed {yea}–{nay}." },
      { "d": "2025-01-24", "t": "Reintroduced the ICE Security Reform Act.", "u": "<release URL>", "q": "exact words from that release" } ] } ],
  "israel": { "question": "...", "headline": "Mixed", "headlineWhy": "...{npal}...{nisr}...{nmixed}...", "summary": "...",
    "items": [ { "d": "2026-07", "dir": "pal|isr|mixed", "roll": "2026-243", "yea": "pal", "text": "...", "also": ["<url>"] } ] } }
```
- `roll` is a roll-call id `<year>-<number>`, zero-padded to three digits (`2025-289`; the same format for House and Senate, matching `id` in `votes.json`). The member's vote and the tallies are filled from `votes.json`; never type them. Placeholders: `{Vote}` ("Voted for" / "Voted against" / "Did not vote on"), `{yea}`, `{nay}`, `{dY}`/`{dN}` and others from `votes_common.roll_phrases`.
- `q` must appear **verbatim** in the cited `u`. The build and `verify_all` check this.
- Flags: `brk` (breaks with party, set automatically for roll items), `unv` (unverified), `none` (no statement found), `approx`.
- On a motion to table or refer, a Nay opposes the tabling. Say so in the text.

### `promises.json` → promise scorecard
```json
{ "sources": { "site2024": { "label": "His 2024 campaign site (archived Oct 31, 2024)", "u": "https://web.archive.org/web/…" } },
  "promises": [ { "issue": "Minimum wage", "kind": "explicit", "status": "stalled", "promise": "exact words", "quote": true,
      "src": ["site2024"], "why": "what the status rests on",
      "actions": [ { "u": "https://www.congress.gov/bill/…", "text": "Cosponsored H.R. 2743." },
                   { "roll": "2025-190", "text": "{Vote} H.R. 1 … {yea}–{nay}." },
                   { "stmt": "slug-of-one-release", "text": "…" } ] } ] }
```
`status`: `delivered`, `progress`, `stalled`, `contradicted`, `none`. `kind`: `explicit` (the member's own words, quoted) or `paraphrase`. Every status needs a `why`. A `stmt` value must match exactly one release in `statements.json`. Cite campaign sites through Wayback snapshots taken before the election.

### `card_picks.json` → evidence cards (ICE, police, corporate)
Each card has `key`, `q`, `eb`, `pro`/`con` labels, and `items` pointing `pro` or `con`; headlines are computed by `build_cards.py` from a rule stated on the card.

### `establishment_items.json` → Establishment page
`question`, `headline`, `summary`, `why` (the rule), `roles`, `tiles` (numbers in `{braces}` are filled from FEC and vote data), `signs.e` / `signs.i` (evidence of establishment alignment / independence), `timeline`, `left`.

### `events.json` → Town halls page
`{ "events": [ { "date", "type", "role": "hosted|participated", "title", "city", "notes", "u" } ] }`. Every event needs a source (`u` or `stmt`).

### `claims_static.json` → Sources page
Facts typed straight into pages: `{ "page", "section", "text", "url", "must": ["terms the source must contain"] }`; `"check": "clerk-committees"` (House) or `"senate-committees"` (Senate) verifies committee seats against the official membership files.

### `bills.json` → bill claims
`{ "bills": [ { "bill": "hr2743", "role": "cosponsor", "law": null, "housePassed": false, "note": "…" } ] }`. A bare id is the 119th Congress; add the Congress for older bills (`118-hr82`). `role` is `sponsor`, `cosponsor` or `none`. `law` is a public-law number (`118-273`) that must be listed. `verify_bills.py` checks all of it against govinfo.

## Votes, ids and conventions

- **Roll-call ids**: `<year>-<number>`, zero-padded (`2025-006`). Roll numbers restart each year (House) or session (Senate).
- **Ranks count ties** ("tied for 60th of 215"), never an arbitrary tie-break.
- **PAC types** use the FEC organization type first, then name rules.
- **Donor names, cities and addresses are never published**, only employer, occupation and totals.
