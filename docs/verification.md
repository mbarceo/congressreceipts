# Sourcing standards and verification

The site's one promise is that every claim links to a source and has been checked against it. These rules are why the trackers can be trusted. **Fix the data, never the checker, to make a check pass.** Each rule below came from a real error.

## The rules

1. **Every claim links to a primary source where one exists.** Primary: official records (House Clerk and senate.gov roll calls, govinfo, congress.gov, FEC, election officials) and people's and groups' own sites. Secondary: news reports and trackers (Track AIPAC, OpenSecrets), always labeled as such.
2. **Votes and tallies are never typed.** The member's vote, the result and every count come from the official roll-call XML through the build scripts. Curated text uses `{placeholders}` that the scripts fill.
3. **Pick votes by reading official titles.** Keyword matching mislabels bills (it once tagged the Gulf of America Act as immigration). Confirm what a bill number actually is: H.R. 6644 is the *21st Century ROAD to Housing Act* (Public Law 119-101) even though its roll-call title reads "Housing for the 21st Century Act".
4. **Verdicts only where a rule is stated.** Verdicts appear only in the "big question" tiles and evidence cards, each with the rule that produced it. Issue sections show evidence and counts and leave the call to the reader. Overview and Stances read the same data files so they cannot disagree.
5. **Quote only words that appear in the cited source.** A quote must appear verbatim in the page it links to (the release's full text, or a saved copy). If the words are on a different page, cite that page.
6. **Endorsers' words are not the member's promises.** Promises come from the member's own words (campaign site, announcement, debates). Interviews give priorities, not pledges.
7. **Cite campaign sites through Wayback snapshots** taken before the election, because campaign sites change or vanish.
8. **Procedural motions invert meaning.** On a motion to table or to refer, a Nay is a vote *against* killing or sidelining the measure. Show the official question and say what a Nay means.
9. **Omnibus and vehicle bills.** A member's own bill can become law inside another bill, and bill numbers collide across chambers (govinfo once listed S. 766's public law on H.R. 766). Check BILLSTATUS *and* the enacted text before writing "stalled" or "became law".
10. **Donor names never appear.** Names, cities and addresses are public in FEC records but are never published: only employer, occupation and totals. Raw FEC files stay out of git. If an old commit contains names, rewrite history before pushing.
11. **PAC types** use the FEC organization type first, then name rules (unions the FEC files as corporations, e.g. the NEA fund; law-firm partnerships).
12. **Ranks count ties.** "Tied for 60th of 215", never an arbitrary tie-break.
13. **Third-party figures are labeled and disclosed.** Track AIPAC totals appear beside FEC-itemized figures, not instead of them, with the read date. Disclose a source's stake when it has one.
14. **Unconfirmed facts stay off the site.** If a date or detail cannot be sourced, show the approximation as such or leave it out.
15. **Official portrait only.** Every page shows the member's official portrait. Never substitute an unofficial photo.
16. **Neutral wording.** The site is nonpartisan. State what a record shows, not what to think of it.

## The checks

`./tr <member> run_checks` runs four scripts in order:

| Step | Script | Fails when |
|---|---|---|
| 1 | `extract_claims.py` | (collects) every claim the pages show, plus `claims_static.json`, into `data/claims.json` |
| 2 | `verify_bills.py` | a bill's role (sponsor / cosponsor / none), public law or House passage disagrees with govinfo BILLSTATUS |
| 3 | `verify_computed.py` | a figure the site shows disagrees with the same figure recomputed from the raw files by separate code |
| 4 | `verify_all.py` | a claim's source does not support it |

`verify_all.py` checks by source type:

| Source | What must be true |
|---|---|
| House Clerk or senate.gov roll call | The recorded vote matches the claim and every tally quoted ("231–182") is one of the roll's real totals (all, Democrats, Republicans) |
| The member's press release | The release is in `statements.json`; every quote and dollar figure in the claim appears in its full text |
| Official bill record | The govinfo BILLSTATUS checks from `verify_bills.py` pass |
| This site's own figures | Dollar figures and percentages match a value recomputed by `verify_computed.py` |
| Any other web page | The page is fetched and saved in `data/sources/`; quotes, figures, percentages and required terms must appear on it |
| Static facts (`claims_static.json`) | The `must` terms appear on the source. Committee seats are read from the Clerk's member file (`"check": "clerk-committees"`, House) or senate.gov committee XML (`"check": "senate-committees"`, Senate). PDFs read by hand are recorded with what was read |

Each claim gets a status, written to `data/verification.json` and shown on the Sources page: `verified`, `partial`, `failed` or `negative-finding` (a stated absence, e.g. "no press release mentions X", confirmed by search). The pipeline has been tested by planting a flipped vote, a wrong tally, a fake quote and a wrong figure; all four were caught.

**Run the checks after every data change, and before every pull request.** Typed facts (committee lists, election results, anything in `profile`) go in `claims_static.json` with the exact terms the source must contain.

## Before opening a pull request

- [ ] `./tr <member> run_checks` passes: all claims verified or explained, all recomputed figures match.
- [ ] Grep the member's pages and config for leftovers from the template or another member (names, district numbers, `TODO`) and for wording that does not fit the chamber (`Clerk`, `Speaker`, `district` on a Senate page).
- [ ] No donor names in `data/fec/` (`git log -p -- <member>/data/fec` shows only employer and occupation).
- [ ] No API keys, raw downloads or `.env` files staged (`git status`).
- [ ] Open every page in the browser: portrait, names, pronouns, tallies and links.
