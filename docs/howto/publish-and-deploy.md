# How publishing and deployment work

## Publishing = copying shared pages into member folders

`scripts/publish.py` is the "build step". It reads `members.json` and, for every member with `format: "shared"`:

1. Copies `site/*.html`, `site/site.js` and `site/site.css` into the member's folder.
2. Fills the member's name into each page's `<title>` and meta description (so link previews say "Who Funds Alex Padilla").
3. Adds the shared header (`hub.css`, `hub.js`) and stamps `?v=<hash>` cache keys on `site.js`, `site.css`, `hub.js`, `hub.css`.
4. Puts a "Built from site/… do not edit" comment at the top.

It also copies `site/site.css` to the root `site.css`, stamps the cache keys on the hub pages, and, for `legacy` members, only adds the header.

```bash
python3 -I scripts/publish.py                  # every member in members.json
python3 -I scripts/publish.py ca/padilla       # one member
python3 -I scripts/publish.py ca/padilla ca/rivas
```

**It writes pages for every member in `members.json`, including trackers that are not finished.** Until the project has a per-member "draft" switch, either run it per member, or run it for everyone and delete the new pages of unfinished members before committing:
```bash
git status --short            # find the new, untracked folders' pages
git clean -fdq ca/garcia      # remove generated pages for a member that is not ready
```

## Deployment

GitHub Pages serves `main` from the repository root; there is no CI and no build on GitHub.

```
your branch ──▶ pull request ──▶ review ──▶ merge to main ──▶ GitHub Pages updates congressreceipts.org (about a minute)
```

- Pages deploys whatever is committed. Generated pages and built JSON must be committed; raw downloads must not.
- `.nojekyll` makes Pages serve files as-is; `CNAME` holds `congressreceipts.org`.
- Nothing validates a pull request automatically. Run `./tr <member> run_checks` first, and preview locally.
- To roll back, revert the merge commit on `main`.

## Who can merge

Only people with write access to `mbarceo/congressreceipts` can push branches and merge. Keep `main` protected in repository settings (require a pull request before merging) so nobody publishes by accident.

## Cache behavior

Visitors' browsers cache scripts and styles. The `?v=<hash>` stamps change whenever the file content changes, so an update is picked up on the next visit. `hub.js` also asks the browser to revalidate every `data/*.json` request. If you change `site.js`, `site.css`, `hub.js` or `hub.css` and forget to run `publish.py`, visitors can get a new page with an old script.
