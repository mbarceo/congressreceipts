# How to refresh a member's data

Do this when new votes, press releases or FEC filings come in. Run from the repository root. Replace `ca/padilla` with the member's folder.

```bash
# 1. New votes (re-runs skip files already downloaded)
./tr ca/padilla fetch_votes            # House: fetch_votes ; Senate: fetch_votes_senate
./tr ca/padilla build_votes
./tr ca/padilla build_alignment

# 2. New press releases (page 0 is always re-fetched; older pages are cached)
./tr ca/padilla fetch_statements
./tr ca/padilla fetch_statement_bodies

# 3. New FEC filings (slow; one member at a time)
./tr ca/padilla fetch_fec
./tr ca/padilla build_fec
./tr ca/padilla build_establishment

# 4. Page data, in this order
./tr ca/padilla build_stances
./tr ca/padilla build_promises
./tr ca/padilla build_cards
./tr ca/padilla build_overview

# 5. Verify, then look at the pages
./tr ca/padilla run_checks
python3 -m http.server 8000
```

Notes
- **Raw data is not in git.** A fresh clone has none, so `fetch_votes` re-downloads the whole Congress the first time (House: a few minutes). That is normal.
- A new vote does not appear in Stances until someone adds it to `stance_picks.json`. Refreshing updates counts, alignment, attendance and the Votes page automatically.
- **FEC downloads resume.** If you hit the rate limit ("FEC rate limit hit"), wait an hour and run `fetch_fec` again; finished files are kept.
- A claim that now fails (for example because a press release was edited or removed) must be fixed in the curated data, not by changing the checker.
- After refreshing several members, rebuild the hub: [rebuild-the-hub.md](rebuild-the-hub.md).
- Commit only the built JSON (`data/*.json`, `data/fec/summary.json`, …). `git status` should not list `data/raw`, `data/fec/raw`, `data/statements_raw` or `data/billstatus`.
