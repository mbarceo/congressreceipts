# Luz Rivas tracker (CA-29): build status

Scaffolded from the Derek Tran tracker (CA-45). Static site, no build step. Preview with the `rivas-tracker` entry in `.claude/launch.json` (port 8646) or `python3 -m http.server` from this folder.

All member-specific values live in `tracker.config.json` (bioguide `R000620`, FEC candidate `H4CA29141`, committee `C00857417`). Scripts read it through `scripts/config.py`; none hardcode a name, ID or district. Run scripts as `python3 -I scripts/<name>.py`.

Data snapshot: roll calls through Nov 19, 2026; press releases through Nov 20, 2026; FEC filings through Oct 14, 2026.

## Pages (all built)
| Page | What it shows | Built from |
|---|---|---|
| Overview (`index.html`) | Header with 2024 and 2026 results, 8 verdict tiles, district map, committees, promise scorecard, vote alignment, recent statements, offices | `build_overview.py`, `build_promises.py`, `build_alignment.py`, `build_map.py` |
| Money | Contributions by source, every PAC, industry watch for her district's issues, employers, largest individual contributions (employer and occupation only), pro-Israel money, outside spending, UDP, Track AIPAC comparison | `build_fec.py`, `fetch_trackaipac.py` |
| Establishment | Verdict, signs each way, leadership money, PAC types, timeline, every vote she split from Jeffries | `build_establishment.py` + `data/establishment_items.json` |
| Town halls | 6 sourced events, how to ask about her next one | `data/events.json` via `build_overview.py` |
| Stances | Big questions (Israel/Palestine, ICE, police, corporate, homelessness, establishment), evidence cards, 8 issue sections | `build_stances.py`, `build_cards.py` |
| Every vote | 689 House roll calls | `build_votes.py` |
| Statements | 144 press releases with topics | `fetch_statements.py`, `fetch_statement_bodies.py` |
| Sources | Every claim's verification result and 24 recomputed figures | `scripts/run_checks.sh` |

## Rebuild and verify
1. Refresh raw data (see `README.md` for each fetch step; FEC needs `FEC_API_KEY`).
2. Rebuild page data, in order: `build_stances.py` → `build_promises.py` → `build_establishment.py` → `build_cards.py` → `build_overview.py`.
3. Verify: `./scripts/run_checks.sh`. Current result: 212 of 212 claims verified, 24 of 24 figures match.

## How the content is kept honest
- **Votes** are hand-picked by reading the Clerk's titles (keyword matching tagged the Gulf of America Act as immigration), but her vote and every tally always come from the Clerk record, never typed. Procedural votes show the Clerk's question and, for tabling and referral motions, what a Nay means.
- **Verdicts** appear only in the big-question tiles and cards; each states the rule that produced it. The Overview and Stances read the same data, so they can't disagree.
- **Promises** come from her own words on the archived 2024 campaign site (Wayback, Oct 31, 2024). Endorsers' words are not counted as her promises.
- **Numbers in curated text** are `{placeholders}` filled by the build scripts.
- **Verification** (`run_checks.sh`): claims are extracted from the built data plus `data/claims_static.json` (facts typed into pages, each with the terms its source must contain). Votes are checked against the Clerk, quotes and figures against her releases' full text, bills against govinfo, committees against her own entry in the Clerk's member file, and other pages are fetched and saved. Misquotes, wrong votes and wrong tallies count as failed. A planted-error test (flipped vote, wrong tally, fake quote, wrong figure) caught all four.
- **PAC types** use the FEC's organization type first, with name rules where the FEC gives none and to catch unions it files as corporations (the NEA fund).
- **Party-unity rank** counts ties: she is tied for 60th of 215.
- **Donor privacy**: donor names, cities and addresses are never published, though FEC records them. `build_fec.py` groups gifts by name and ZIP internally but writes only employer, occupation and totals; the Money page says so.
- **Track AIPAC disclosure**: the Money page notes that Track AIPAC is listed among the 2026 endorsers of her opponent, Angélica María Dueñas.

## Corrections made by the checks (for the record)
- Her manufacturing bill (H.R. 5157) never left committee; its text became law as Sec. 8802 of the FY2026 defense bill (P.L. 119-60), which she voted against.
- The bill she voted for, H.R. 6644, is the 21st Century ROAD to Housing Act (P.L. 119-101).
- Rank was 61st from an arbitrary tie-break; corrected to tied for 60th.
- Promise quotes now cite only the source with the exact words.

## Reference data
- `data/reference/whofundedgenocide_pacs.json`: the 44 committees whofundedgenocide.com lists as the pro-Israel lobby (with FEC IDs), plus J Street, and what the site says about Rivas and Tran. Third-party advocacy source; not used on any page. Its roster confirms the Money page misses no pro-Israel PAC; its per-member totals differ from FEC filings and give no date range.

## What's left
- **Publish**: no git remote yet. Create a GitHub repo, push, then Settings → Pages → `main`, root.
- **Stances depth**: every section is a sample, not every vote (science and education now has 10 picked votes).
- **Unconfirmed, so left off the site**: the date of one roundtable (shown as "Spring 2026"). Dueñas's eight 2026 endorsers are now listed from her campaign site. Her Dec 29, 2024 NBC LA interview (found via NBC's caption file) gave priorities, not pledges, so nothing was added.
- **Git history**: commits made before Nov 24, 2026 contain the old `data/fec/summary.json` with donor names and cities. Rewrite history before pushing if they must not be published.
- **District map**: community shares are by land area, not population.
- **Data refresh**: everything is a Nov 2026 snapshot; rerun the fetch, build and check steps to update.
