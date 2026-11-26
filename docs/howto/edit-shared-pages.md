# How to change the site itself

Two kinds of pages, edited in different places.

| You want to change | Edit | Never edit |
|---|---|---|
| A member page (Overview, Money, Stances, Votes, Statements, Establishment, Town halls, Sources) for **every** member | `site/<page>.html`, `site/site.js`, `site/site.css` | The copies inside `ca/padilla/…`, `md/van-hollen/…` (they start with a comment saying "Built from site/… Edit site/…, not this copy.") |
| The header, footer, favicon or logo | `hub.js`, `hub.css`, `assets/` | n/a |
| The home, Find, Who's showing up, Leaders, Backlog or About page | the file at the repository root (`index.html`, `find.html`, …) | n/a |
| One member's wording | that member's `tracker.config.json` (`profile`) or curated `data/*.json` | n/a |

## Steps

1. Branch from `main` (use a worktree if other work is open).
2. Edit the source files.
3. Preview. Serve the repository root: `python3 -m http.server 8000`. Member pages are at `http://localhost:8000/ca/padilla/`; hub pages at `http://localhost:8000/`. Check a **House** member and a **Senate** member, and a phone-width window.
4. Run the publisher to copy your change into the member folders and refresh the cache keys:
   ```bash
   python3 -I scripts/publish.py
   ```
5. Look at what changed with `git status`. If trackers that are not finished yet are registered in `members.json`, `publish.py` will also create pages for them; delete those new files (`git clean -fd <member folder>`) or run the publisher per member (`python3 -I scripts/publish.py ca/padilla ca/rivas …`) so unfinished trackers do not go public.
6. Commit the source change **and** the regenerated copies together, and open a pull request. A change to `site.js`, `site.css`, `hub.js` or `hub.css` rewrites the `?v=` cache key in every page of every member, so such pull requests touch many files. That is expected; the only differences in the copies should be the new key and your change.

## Rules for page code

- **No member-specific text or logic in HTML or JS.** Use tokens (`{{short}}`, `{{poss}}`) and `data-only="house"` / `data-only="senate"`. A page must render for a House member, a senator, and a member with missing data.
- Pages must handle a missing data file gracefully (show "not built yet").
- Write copy so a verb never follows a pronoun token: "Where {{short}} stands", not "Where {{subj}} stands".
- The site is dark-only by design; colors are CSS variables in `site/site.css`.
- Vanilla HTML, CSS and JavaScript only. No framework, bundler or package manager.
- Fonts: Archivo (display), Public Sans (body), IBM Plex Mono (data).
- After changing a page's data needs, update the data files list in [pipeline.md](../pipeline.md#data-files-in-a-member-folder).
