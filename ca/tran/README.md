# CA-45 Tran Tracker

A nonpartisan accountability site for Rep. Derek Tran (D, CA-45): his promises, votes, money, stances, town halls and public statements. Every claim links to its source, and the **Sources** tab shows how each one was checked.

## Pages
- `index.html`: overview, district map, promise scorecard, verdicts, vote alignment, town halls (`#townhalls`)
- `money.html`, `establishment.html`, `stances.html`, `votes.html`, `statements.html`, `sources.html`

## Data and how to refresh it
All data comes from public records. Run from the project folder:

```bash
./scripts/fetch_votes.sh && python3 -I scripts/build_votes.py && python3 -I scripts/build_alignment.py   # House Clerk roll calls
python3 -I scripts/fetch_statements.py                                                                     # tran.house.gov press releases
FEC_API_KEY=your_key python3 -I scripts/fetch_fec.py && python3 -I scripts/build_establishment.py && python3 -I scripts/build_fec.py   # FEC filings
python3 -I scripts/fetch_geo.py && python3 -I scripts/build_map.py                                         # Census district boundaries
python3 -I scripts/fetch_trackaipac.py                                                                     # Track AIPAC figures (Money and Overview)
python3 -I scripts/build_cards.py                                                                          # Stances evidence cards from data/card_picks.json
```

## Verification
```bash
node scripts/extract_claims.js      # builds data/claims.json from every page and data/cards.json
python3 -I scripts/verify_bills.py  # govinfo bill records
python3 -I scripts/verify_computed.py
python3 -I scripts/verify_all.py    # writes data/verification.json (shown on the Sources tab)
```

Donor names and locations are never published: the Money page lists only each top donor's employer and occupation.

Raw downloads and saved copies of source pages are not committed (see `.gitignore`); the scripts recreate them.

## GitHub Pages
Settings → Pages → Deploy from a branch → `main`, folder `/ (root)`.
