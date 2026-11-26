# How to support a new press-release page layout

`scripts/fetch_statements.py` reads a member's press-release **list pages**. Each website platform needs a small parser. Existing layouts:

| `pressLayout` | Platform | Example |
|---|---|---|
| `house-evo` | house.gov Drupal "evo" theme: one `<div class="views-row">` per release, `?page=N` | `tran.house.gov`, `robertgarcia.house.gov` |
| `wp-jetengine` | WordPress + JetEngine listing grid | `padilla.senate.gov` |
| `wp-elementor` | WordPress + Elementor loop grid | `schiff.senate.gov` |

`pressLayout: "auto"` (the default) detects one from the first page.

## Symptoms that you need a change

- `Unrecognized press-release list layout …` (no parser matches).
- It runs but prints `0 statements` or `page 0: 0 rows`. The layout is close to a known one but a selector no longer matches. (This happened with `robertgarcia.house.gov`: the title heading was `h3` where the parser expected `h5`.)

## Steps

1. Save the first list page and look at one release block:
   ```bash
   curl -sL -A "Mozilla/5.0" "https://MEMBER-SITE/media/press-releases" -o /tmp/p0.html
   ```
2. Find the repeating wrapper element for one release and where the title link, date and excerpt sit inside it.
3. Either loosen the selector in the closest existing parser, or add a new one:
   - `parse_<name>(page_html)` returns `[(href, title_html, date_text, excerpt_html), …]`, **one tuple per release, read from that release's own block only** so a title, date and excerpt can never be stitched from different releases.
   - Register it in `PARSERS`, add a rule to `detect()`, and a pager rule to `pager()` (how to get page N).
   - If dates use a new format, add it to `parse_date()`.
4. Run it and compare with the live page:
   ```bash
   ./tr <member> fetch_statements --max-pages 3
   ```
   The first rows must match the newest releases on the site, and the oldest row must be plausible (the member's start date).
5. Run `fetch_statement_bodies`, which finds each release body by layout (`evo-press-release__body` for house.gov; WordPress sites use their own selector). Check that `statements_full.json` has no missing texts: quotes are verified against them.
6. Test a second member on the same platform to make sure you did not break it. A capped run overwrites that member's `data/statements.json`, so restore it afterwards:
   ```bash
   ./tr ca/tran fetch_statements --max-pages 1
   git diff --stat ca/tran/data/statements.json   # the newest rows must be unchanged
   git checkout -- ca/tran/data/statements.json   # undo the capped run
   ```
7. Update the layouts table above and the docstring at the top of `fetch_statements.py`.

## If the site blocks scripts

senate.gov sites sit behind bot protection and may return `403 Access Denied`, even in a browser pane driven by automation. The script already waits and retries. Do not try to bypass bot detection. There is currently no supported way to feed it saved pages (page 0 is always re-fetched; only later pages are cached in `data/statements_raw/`). Tell a maintainer, or build the tracker without statements for now and say so in the pull request. (A `--from-cache` option would be a useful improvement.)
