# Congress Receipts documentation

| Read | When |
|---|---|
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | You were just added to the project: setup, keys, Claude Code, working rules, first pull request |
| [architecture.md](architecture.md) | You want to understand how the whole site works |
| [pipeline.md](pipeline.md) | You need to know what a script does, what it reads and writes, and in what order to run them |
| [config-reference.md](config-reference.md) | You are editing `members.json`, `tracker.config.json` or a curated data file |
| [verification.md](verification.md) | You are curating content or a check failed (the sourcing rules live here) |
| [senate-differences.md](senate-differences.md) | The member is a senator |
| [leadership.md](leadership.md) | You are working on the Senate and House leadership-race page (`leadership.html`) |
| [troubleshooting.md](troubleshooting.md) | Something broke |

Diagrams in these docs are [Mermaid](https://mermaid.js.org/); GitHub renders them in the browser.

## How-to guides

| Task | Guide |
|---|---|
| Add a member's tracker (flow diagrams, cloud vs Mac) | [howto/add-a-member.md](howto/add-a-member.md) |
| Refresh a tracker with new votes, releases, filings | [howto/refresh-a-member.md](howto/refresh-a-member.md) |
| Change the site's pages, header or design | [howto/edit-shared-pages.md](howto/edit-shared-pages.md) |
| Understand publishing and deployment | [howto/publish-and-deploy.md](howto/publish-and-deploy.md) |
| Support a new press-release page layout | [howto/add-a-press-layout.md](howto/add-a-press-layout.md) |
| Update the Backlog | [howto/update-the-queue.md](howto/update-the-queue.md) |
| Rebuild the home, attendance, leaders and Find pages | [howto/rebuild-the-hub.md](howto/rebuild-the-hub.md) |

## For Claude Code and other AI agents

Any agent, not just Claude, should start at [`../AGENTS.md`](../AGENTS.md), which points to `CLAUDE.md` and the guides below.

The repository includes `CLAUDE.md` (project rules and a map, loaded automatically) and the `add-member` skill in `.claude/skills/add-member/`. See [CONTRIBUTING.md](../CONTRIBUTING.md#4-claude-code-with-your-own-account).

## Known gaps (good first improvements)

- **`fetch_statements` cannot read pages you saved by hand** when a site blocks scripts (page 0 is always re-fetched). A `--from-cache` option would help.
- **No automated checks on pull requests.** A GitHub Action could run `run_checks` for changed members, fail on staged raw data or API keys, and check JSON validity.
- **`build_attendance` needs every member's raw XML locally.** Caching a per-Congress roll-call archive, or recording official per-member counts in committed files, would remove that.
- **A few shell helpers still need `zsh`** (`fetch_votes.sh`, `run_checks.sh`, the key wrappers). `./tr` itself no longer does. Python-only versions would make Windows easier.
- **FEC downloads are not throttled.** A Senate download needs several thousand calls and the key allows about 1,000 an hour; a fetcher that spaces its calls over the hour would avoid the stop-and-resume.
