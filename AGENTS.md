# Start here (for any AI agent or new contributor)

Congress Receipts is a nonpartisan, fully sourced static site. This file only points you to the real instructions. **`CLAUDE.md` is the source of truth; read it first, even if you are not Claude.**

## Read, in this order
1. [`CLAUDE.md`](CLAUDE.md): the map of the repo, the commands, and the non-negotiable rules.
2. [`CONTRIBUTING.md`](CONTRIBUTING.md): setup and how to work and open a pull request.
3. [`docs/README.md`](docs/README.md): the index of every guide.
4. [`docs/verification.md`](docs/verification.md): the sourcing standard; read before you write any claim.
5. Working on the **Senate or House leadership-race page**? Read [`docs/leadership.md`](docs/leadership.md): files, data flow, what is verified and what is not, and the open items.

## The rules that matter most
- **Every claim links to a real source and is checked.** Never invent a source, quote or number. If you cannot verify something, say so on the page or leave it out.
- **Go slow on other people's websites.** One request at a time, a few seconds apart. Stop at the first 403 or 429. Never retry in a loop, rotate headers, or look for a way around a block. Tell the maintainer and move on.
- **Never push to `main`.** One branch and one pull request per task. Use a `git worktree` for each task (other sessions may have uncommitted work in the same folder). Stage explicit paths. Do not merge or deploy; that is the maintainer's job.
- **Shared files** (`site/`, `scripts/`, `hub.js`, `hub.css`, `template/`, the root hub pages) go in their own small pull requests. After changing `hub.js`, `hub.css` or `site.css`, run `python3 -I scripts/publish.py`.
- **No secrets** in files, commits or chat. Raw downloads are never committed.
- **Pronouns:** do not use he, she, him or her for anyone unless their official bio states pronouns. Use their name.
- Python scripts are standard library only and run with `python3 -I`.

## Quick orientation
- Hub pages are in the repo root (`index.html`, `find.html`, `attendance.html`, `leaders.html`, `leadership.html`, `backlog.html`, `about.html`); each member tracker lives in `<state>/<member>/`.
- To preview: `python3 -m http.server 8000` (pages need HTTP, not `file://`).
- Not sure what to work on? Ask the maintainer before starting, and check open pull requests first.
