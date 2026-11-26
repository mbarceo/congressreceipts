# The data pipeline

Every script lives once in `scripts/`. Run it for one member with the runner:

```bash
./tr ca/padilla build_votes        # = python3 -I scripts/build_votes.py, with TRACKER_DIR=ca/padilla
./tr ca/padilla run_checks
```

`./tr` sets `TRACKER_DIR`, supplies the API key to the scripts that need one (FEC or congress.gov), and `cd`s into the member's folder. Scripts read `tracker.config.json` through `scripts/config.py`. The `-I` flag (isolated mode) is used everywhere so a stray file in the current folder can never shadow a Python module.

## Stages

```
1 FETCH   download raw records            → data/raw, data/fec/raw, data/statements_raw, data/billstatus, data/geo/raw   (not in git)
2 BUILD   turn raw + curated inputs → JSON → data/*.json                                                                 (in git)
3 VERIFY  re-derive every claim and figure → data/claims.json, verification.json, computed_checks.json, bill_checks.json  (in git)
4 PUBLISH copy shared pages into member folders → <member>/*.html, site.js, site.css                                     (in git)
```

### Rebuild order for one member

1. **Raw data**
   - Votes: House `fetch_votes` (shell script, House Clerk XML) or Senate `fetch_votes_senate` (senate.gov XML) → `build_votes` → `build_alignment`
   - Statements: `fetch_statements` → `fetch_statement_bodies`
   - Money: `resolve_fec` (once) → `fetch_fec` → `build_fec`; then `fetch_trackaipac`
   - Bills: `fetch_bills` (congress.gov)
   - House only, map: `fetch_geo` → `build_map`
2. **Page data**, in this order, because each reads the previous outputs:
   `build_stances` → `build_promises` → `build_establishment` → `build_cards` → `build_overview`
3. **Verify:** `./tr <member> run_checks`.
4. **Publish:** `python3 -I scripts/publish.py <member path>`.

## Script reference

### Fetch
| Script | Needs | Writes | Notes |
|---|---|---|---|
| `fetch_votes.sh` | none | `data/raw/<year>-roll<NNN>.xml` | House Clerk. About 690 files per Congress; takes several minutes; skips files it already has |
| `fetch_votes_senate.py` | none | `data/raw/senate-<year>-<NNNNN>.xml` | senate.gov. May answer scripts with HTTP 403; see [troubleshooting](troubleshooting.md) |
| `fetch_statements.py` | none | `data/statements.json`, `data/statements_raw/` | Press-release lists. Layouts: `house-evo`, `wp-jetengine`, `wp-elementor`. A new site layout needs a parser ([how-to](howto/add-a-press-layout.md)) |
| `fetch_statement_bodies.py` | none | `data/statements_full.json` | Full text of every release, used to verify quotes. Cached |
| `resolve_fec.py` | FEC key | `fec.candidateId`, `committeeId`, `cycles` in the config | Run once per member. If several candidates match it writes nothing; set the ids by hand |
| `fetch_fec.py` | FEC key | `data/fec/raw/` | Cycle totals and every committee contribution. Rate-limited; resumable |
| `fetch_trackaipac.py` | none | `data/trackaipac.json` | Third-party figure, shown beside FEC data and labeled |
| `fetch_bills.py` | congress.gov key | `data/member_bills.json` | Every bill the member sponsored or cosponsored |
| `fetch_portrait.py` | none | `assets/portrait.jpg` | Bioguide first (kept current). Open the image to confirm it |
| `fetch_geo.py` | none | `data/geo/raw/` | Census boundary shapes, House only |

### Build
| Script | Reads | Writes |
|---|---|---|
| `build_votes.py` | raw roll calls | `data/votes.json`: the member's vote on every roll call, with party tallies |
| `build_alignment.py` | `votes.json` | `data/alignment.json`: agreement with peers and the party leader, party unity and rank |
| `build_fec.py` | `fec/raw` | `data/fec/summary.json`: Money page (employer and occupation only, never donor names) |
| `build_establishment.py` | `fec/raw`, `data/establishment_items.json` | `data/establishment.json`, `fec/establishment_calc.json`, `fec/leadership.json` |
| `build_stances.py` | `stance_picks.json`, `votes.json`, `statements*.json`, `trackaipac.json` | `data/stances.json` |
| `build_promises.py` | `promises.json`, `votes.json`, `statements.json` | `data/promises_built.json` |
| `build_cards.py` | `card_picks.json`, `stances.json`, `fec/establishment_calc.json` | `data/cards.json` (ICE, police, corporate evidence cards) |
| `build_overview.py` | stances, votes, statements, promises, cards, `events.json` | `data/overview.json` (verdict tiles, events) |
| `build_map.py` | `geo/raw` | `data/geo/map.json` (House only) |

### Verify
| Script | What it does |
|---|---|
| `extract_claims.py` | Collects every sourced claim the pages show, plus `claims_static.json` (facts typed into pages), into `data/claims.json` |
| `verify_bills.py` | Checks each bill in `data/bills.json` (role: sponsor / cosponsor / none, public law, House passage) against govinfo BILLSTATUS |
| `verify_computed.py` | Recomputes key figures with separate code from the raw files and compares them with what the site shows |
| `verify_all.py` | Verifies each claim against its source: roll call, press release (quotes and dollar figures), FEC, congress.gov, archived page. Writes `data/verification.json` for the Sources page |
| `run_checks.sh` | Runs all four in order |

### Shared code and tooling
| File | Role |
|---|---|
| `config.py` | Loads `TRACKER_DIR/tracker.config.json` (`CFG`, `M` = member, `FEC`) |
| `votes_common.py` | Chamber-agnostic roll-call loader and the `{Vote} {yea} {nay} …` placeholder filler used by every vote script |
| `new_tracker.py` | Scaffolds a new member folder from `template/` ([how-to](howto/add-a-member.md)) |
| `publish.py` | Copies `site/` pages into member folders and stamps cache keys ([how-to](howto/publish-and-deploy.md)) |
| `with_fec_key.sh`, `with_congress_key.sh` | Supply an API key from the environment or the macOS Keychain |
| `redirect_stub.py` | Writes redirect pages for the old per-member repositories |

## Data files in a member folder

Committed. Curated files are written by hand (or with Claude Code); built files are written by scripts and should never be edited.

| File | Kind | Feeds |
|---|---|---|
| `tracker.config.json` | curated | everything (identity, FEC ids, peers, profile text) |
| `stance_picks.json` | curated | Stances page issues and the Israel card |
| `card_picks.json` | curated | the evidence cards |
| `promises.json` | curated | the promise scorecard |
| `establishment_items.json` | curated | the Establishment page |
| `events.json` | curated | the Town halls page |
| `claims_static.json` | curated | facts typed into pages that need a source check |
| `bills.json` | curated | bills the pages make claims about (checked by `verify_bills`) |
| `votes.json`, `alignment.json`, `statements.json`, `statements_full.json`, `stances.json`, `promises_built.json`, `cards.json`, `establishment.json`, `overview.json`, `fec/summary.json`, `trackaipac.json`, `member_bills.json`, `geo/map.json` | built | the pages |
| `claims.json`, `verification.json`, `computed_checks.json`, `bill_checks.json`, `sources/index.json` | built | the Sources page |

Not committed (listed in `.gitignore`): `data/raw/`, `data/fec/raw/`, `data/statements_raw/`, `data/billstatus/`, `data/geo/raw/`, `data/site_raw/`, `data/sources/*.html`.

Formats of the curated files are in [config-reference.md](config-reference.md). Each skeleton in `template/data/` carries a `_note` explaining its format.

## Hub data

The hub pages read JSON from the repository's `data/` folder:

| File | Page | Built by | Reads |
|---|---|---|---|
| `attendance.json` | home, Who's showing up | `build_attendance.py` | `members.json`, each member's `votes.json`, `events.json` and **raw roll-call XML** |
| `leaders.json` | Leaders tracker | `build_leaders.py` | each member's committed `data/` |
| `directory.json`, `zips.json` | Find your rep | `build_directory.py` | House Clerk member list, Census ZIP-to-district file, a senator's raw votes (download cache in `data/directory_raw/`, ignored) |
| `congress.json` | Backlog Queue | `build_roster.py` | the `unitedstates/congress-legislators` current-members file |
| `queue.json` | Backlog Queue | edited by hand | n/a |

`build_attendance.py` refuses to build if a tracker's `votes.json` disagrees with the official XML it recounts, or if two members of one chamber cover different roll-call ranges (refetch the older tracker's votes).

## API keys

| Key | Used by | Get it | Environment variable |
|---|---|---|---|
| FEC | `resolve_fec`, `fetch_fec`, `build_fec` | https://api.open.fec.gov/developers/ | `FEC_API_KEY` |
| congress.gov | `fetch_bills` | https://api.congress.gov/sign-up/ | `CONGRESS_API_KEY` |

Without a key `fetch_fec` falls back to the public `DEMO_KEY`, which allows only about 10 calls an hour. Even a real key is capped (about 1,000 calls an hour), and a senator's six-year span needs several thousand calls, so a download can stop partway; finished files are kept and the next run resumes. Run one member at a time. Keys are never stored in files; see [CONTRIBUTING.md](../CONTRIBUTING.md#api-keys).
