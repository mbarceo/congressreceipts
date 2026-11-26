# Senators: what differs from the House

The pipeline is shared; these are the differences when a member is a senator. Everything else in [pipeline.md](pipeline.md) and [howto/add-a-member.md](howto/add-a-member.md) applies unchanged.

Scaffold a senator with:

```bash
python3 -I scripts/new_tracker.py --name "Alex Padilla" --chamber senate --state CA \
  --bioguide P000145 --vote-id S413 --pronouns he --since 2021-01-20 --out ca/padilla
```

## Identity: two ids
- **Bioguide id** (`member.bioguide`): used for govinfo bill checks, Track AIPAC lookups by name, the portrait.
- **LIS member id** (`member.voteId`, e.g. `S413`): the only id in Senate roll-call XML (`<lis_member_id>`). Every vote script keys on `voteId` (`votes_common.MY_ID`, falling back to bioguide for the House). Peers in `peers[].id` must also be LIS ids for a senator.
- Find both, plus the official site, in `https://www.senate.gov/general/contact_information/senators_cfm.xml` (bioguide, website) and any vote XML (`lis_member_id`).

## Votes
- Menus: `https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_<congress>_<session>.xml` (session 1 = first year of the Congress; 119th: 2025 = 1, 2026 = 2).
- Each vote: `.../roll_call_votes/vote<congress><session>/vote_<congress>_<session>_<NNNNN>.xml`; the citable page is the same path ending `.htm` (`votes_common.vote_url`).
- `scripts/fetch_votes_senate.py` downloads into `data/raw/senate-<year>-<NNNNN>.xml` (if senate.gov answers 403, copy the identical files from another senator's `data/raw/`); `votes_common._senate` parses them into the same shape as House rolls, so `build_votes`, `build_alignment` and the verifiers don't branch on chamber. Roll numbers restart every session.
- Senate XML writes bills as `H.R. 29` / `S.J.Res. 12`; `votes.html` normalizes both forms for congress.gov links.
- There is no Speaker election; `index.html` skips the Speaker item for senators. Cloture votes matter in the Senate; read the question before calling a vote procedural.
- Party unity rank and "typical Democrat" figures are computed among Senate Democrats. Independents who caucus with Democrats (Sanders, King) carry party `I` in the XML; check how `votes_common.party_side` treats them before quoting a rank.

## Money (FEC)
- `resolve_fec.py` searches office `S` (no district) and, for senators, writes `fec.cycles` from the election that began the current term through the current cycle (six-year term, three two-year FEC cycles), e.g. Padilla (elected 2022): 2022, 2024, 2026; Schiff (elected 2024): 2024, 2026. `--keep-cycles` keeps hand-set cycles.
- Leader box on the Money page and Overview: `fec.leadershipRx` `SCHUMER|^IMPACT$` and `fec.leadershipIds` `["C00346312", "C00348607"]` (Friends of Schumer, Impact). `new_tracker.py` writes these.
- `fec.leaders.senate` lists the Senate Democratic leadership and the DSCC for `build_establishment.py` (roles from `https://www.senate.gov/senators/leadership.htm`).
- Contribution limits per election are the same as for House candidates, but a six-year cycle span means older limits apply to early cycles; don't state a single limit for every cycle.

## Track AIPAC
- Senator slug: `member-<first>-<last>-<st>-sen-<party>` (e.g. `member-alex-padilla-ca-sen-d`). `fetch_trackaipac.py` builds it when the member's or peer's `dist` is a state code. Set `member.trackaipacSlug` or a peer's `slug` when Track AIPAC spells a name differently.

## Statements
- senate.gov office sites use other CMSes than house.gov. `fetch_statements.py` detects `wp-jetengine` (padilla.senate.gov) and `wp-elementor` (schiff.senate.gov); set `member.pressLayout` to force one. Senators can have 1,000-2,000 releases: use `--max-pages` for a first pass.
- A list at `/newsroom/press-releases/` can link releases under another path; verify_all accepts release URLs under any prefix the list actually uses.

## Committees
- House seats are checked against the Clerk's member file (`"check": "clerk-committees"`). For a senator use `"check": "senate-committees"` in `data/claims_static.json`: every committee and subcommittee named in `must` must list the senator in senate.gov's membership XML (matched by last name and state).

## Pages
- No district map: `index.html` hides `#district` when `member.chamber` is `"senate"` and shows `#state` only if `profile.state.intro` or `profile.state.facts` is filled. `fetch_geo.py` and `build_map.py` are House-only; `geo` in the config is a note.
- All chamber wording comes from `site.js` (`{{chamberName}}`, `{{voteSource}}`, `{{voteSourceLong}}`, `{{leaderName}}`, `{{officeNoun}}`, ...). Sources and votes pages say "Senate roll calls" and link senate.gov.
- Leader defaults: Senate Chuck Schumer (`S270`), House Hakeem Jeffries (`J000294`), in `leader` and as the first peer.

## Known gaps
- The Senate pipeline has been run end to end for Padilla and Schiff; Van Hollen's votes and alignment are built. Record anything that breaks here.
- senate.gov blocks scripted requests (403) for votes and press pages; see [troubleshooting.md](troubleshooting.md).
- Grep a new scaffold for leftovers from another member (`Rivas`, `Clerk`, `CA-29`, `district`) before publishing.
