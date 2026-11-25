# CA-29 Rivas Tracker

A nonpartisan accountability site for Rep. Luz Rivas (D, CA-29): her promises, votes, money, stances, town halls and public statements. Every claim links to its source, and the **Sources** tab shows how each one was checked.

## Pages
- `index.html`: overview, quick verdicts, district map, committees, promise scorecard, vote alignment, offices
- `money.html`, `establishment.html`, `townhalls.html`, `stances.html`, `votes.html`, `statements.html`, `sources.html`

All member-specific values live in `tracker.config.json`; scripts read it through `scripts/config.py`. `SCAFFOLD.md` has the full build notes.

## Data and how to refresh it
All data comes from public records. Run from the project folder:

```bash
./scripts/fetch_votes.sh && python3 -I scripts/build_votes.py && python3 -I scripts/build_alignment.py   # House Clerk roll calls
python3 -I scripts/fetch_statements.py && python3 -I scripts/fetch_statement_bodies.py                     # rivas.house.gov press releases
FEC_API_KEY=your_key python3 -I scripts/resolve_fec.py                                                     # once: finds her FEC IDs
FEC_API_KEY=your_key python3 -I scripts/fetch_fec.py && python3 -I scripts/build_fec.py                    # FEC filings
python3 -I scripts/fetch_trackaipac.py                                                                     # Track AIPAC figures
python3 -I scripts/fetch_geo.py && python3 -I scripts/build_map.py                                         # Census and LA County boundaries
```

Then rebuild the page data in this order:

```bash
python3 -I scripts/build_stances.py && python3 -I scripts/build_promises.py && python3 -I scripts/build_establishment.py && python3 -I scripts/build_cards.py && python3 -I scripts/build_overview.py
```

## Verification
```bash
./scripts/run_checks.sh   # claims registry, bill records, recomputed figures, full verification (Sources tab)
```

Raw downloads and saved copies of source pages are not committed (see `.gitignore`); the scripts recreate them.

## GitHub Pages
Settings → Pages → Deploy from a branch → `main`, folder `/ (root)`.
