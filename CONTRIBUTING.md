# Contributing to Congress Receipts

Welcome. This guide gets you from zero to your first pull request, including how to work with your **own Claude Code account**. For how the system works, read [docs/architecture.md](docs/architecture.md) first (10 minutes).

## What you can work on

- **Add a member's tracker** (the main job): [docs/howto/add-a-member.md](docs/howto/add-a-member.md)
- **Refresh a tracker** with new votes, releases or filings: [refresh-a-member](docs/howto/refresh-a-member.md)
- **Improve the site** (pages, design, the hub): [edit-shared-pages](docs/howto/edit-shared-pages.md)
- **Support a new press-release layout**: [add-a-press-layout](docs/howto/add-a-press-layout.md)
- **Update the Backlog Queue**: [update-the-queue](docs/howto/update-the-queue.md)

Before you pick a member, check `data/queue.json` and the open pull requests, and tell the others which member you are taking (mark them `progress` in the queue, in a small pull request of its own).

## One-time setup

### 1. Accept the repository invitation
You were added as a collaborator on `mbarceo/congressreceipts`. Accept the invitation (email or github.com/mbarceo/congressreceipts), then:
```bash
git clone https://github.com/mbarceo/congressreceipts.git
cd congressreceipts
```
You can push branches directly. **Never push to `main`**; everything goes through a pull request.

### 2. Requirements
- macOS or Linux (on Windows use WSL). `zsh`, `git`, and Python 3 (developed on 3.14; standard library only, nothing to `pip install`).
- The GitHub CLI (`gh`) is optional but handy: `gh auth login`.
- About 1 GB of free disk per few trackers while building (raw downloads; they are never committed).

### 3. API keys
Two free keys. **Each person uses their own.** Do not share keys, and never put one in a file, a commit, an issue or a chat with an AI assistant.

| Key | Used for | Get it |
|---|---|---|
| FEC | campaign finance | https://api.open.fec.gov/developers/ |
| congress.gov | bills sponsored and cosponsored | https://api.congress.gov/sign-up/ |

**macOS (recommended):** store each in the Keychain once. The command prompts for the key, so it never appears on screen or in shell history.
```bash
security add-generic-password -U -a "$USER" -s fec-api-key -w
security add-generic-password -U -a "$USER" -s congress-api-key -w
```
`./tr` reads them automatically when a script needs one.

**Linux, WSL or CI:** export the variables in the shell session that runs the command (for example from your password manager), so `with_fec_key.sh` / `with_congress_key.sh` use them:
```bash
export FEC_API_KEY=…        # never commit this, and don't paste it into Claude Code
export CONGRESS_API_KEY=…
```

### 4. Claude Code with your own account
Each contributor uses their own Claude account and plan (for example Claude Pro); usage counts against your plan, not anyone else's.

1. Install Claude Code and sign in (see Anthropic's guide: https://docs.claude.com/en/docs/claude-code/overview). In short: install it, run `claude` in a terminal inside the repo folder, and choose to sign in with your Claude account (`/login` if prompted). The Claude desktop app's Code tab works too.
2. Start it **in the repository folder** (`cd congressreceipts && claude`). It automatically loads two things from this repo:
   - **`CLAUDE.md`**: the project rules and a map of the code.
   - **The `add-member` skill** (`.claude/skills/add-member/`): the step-by-step workflow and the sourcing standards for building a tracker.
3. Ask for the job in plain words, for example: *"Add a tracker for Rep. Jane Doe, CA-12, following the add-member skill. Work on a new branch and stop before publishing."*
4. Claude will run the `./tr …` commands and edit data files. **You are the editor**: it proposes vote picks, quotes and statuses; you read the source behind every claim. Treat its output like a draft from a research assistant.

Tips
- Approve commands you understand; decline anything that touches keys, `git push` to `main`, or deletes data you did not create.
- Do not paste API keys, tokens or personal data into the conversation.
- Long downloads (`fetch_votes`, `fetch_fec`) take minutes to an hour. Let them finish; they resume if interrupted.
- If Claude suggests changing a checker so a claim passes, say no: fix the data.

## Working rules (how not to step on each other)

1. **One branch and one pull request per task.** One member per pull request. Name branches `add-<state>-<last>`, `refresh-<last>`, `site-<topic>`, `queue-<topic>`.
2. **One working copy per task.** If you run several Claude Code sessions (or work on two tasks), give each its own `git worktree`; they share the repository but not the files:
   ```bash
   git fetch origin
   git worktree add ../congressreceipts-garcia -b add-ca-garcia origin/main
   ```
   Two sessions in the same folder overwrite each other's files and mix their uncommitted changes.
3. **Shared files are small, separate pull requests.** Anything in `site/`, `scripts/`, `hub.js`, `hub.css`, the root hub pages, `template/` or `members.json` affects everyone. Do not bundle it with a member's data.
4. **`members.json` is append-only** and a frequent conflict. Rebase on `main` right before you open the pull request.
5. **Do not run `python3 -I scripts/publish.py` with no arguments** unless you are changing shared files, and then delete the pages it generates for unfinished members (see [publish-and-deploy](docs/howto/publish-and-deploy.md)). Publish your own member with `publish.py <path>`.
6. **Never commit raw data or secrets.** `git status` must not show `data/raw`, `data/fec/raw`, `data/statements_raw`, `data/billstatus`, `data/site_raw`, `data/geo/raw`, any `.env` file or a key. Donor names, cities and addresses are never published.
7. **Do not edit generated files.** Pages inside a member folder are copies of `site/`; edit `site/`.
8. **Follow the sourcing rules** in [docs/verification.md](docs/verification.md). They are why this site is trusted.
9. **Ask before going outside the plan.** Anything that publishes (merging, running the full publisher) or changes who sees what is for the maintainer.

## Your first pull request, step by step

```bash
git fetch origin
git worktree add ../congressreceipts-<last> -b add-<state>-<last> origin/main
cd ../congressreceipts-<last>

# ... do the work (see docs/howto/add-a-member.md) ...
./tr <state>/<last> run_checks          # must pass

git status                              # only your member's folder (and members.json) should be listed
git add <state>/<last> members.json
git commit -m "Add <Name> tracker"
git push -u origin add-<state>-<last>
gh pr create --base main --fill         # or open it on github.com
```

In the pull request description say what the tracker covers, which checks passed, anything left undone (for example "events not researched"), and attach nothing secret. A maintainer reviews and merges; merging publishes the site ([how deployment works](docs/howto/publish-and-deploy.md)).

## Getting unstuck

[docs/troubleshooting.md](docs/troubleshooting.md) covers the common failures: senate.gov returning 403, the FEC rate limit, "0 statements", missing raw data, and merge conflicts in `members.json`.

## Code of conduct for content

Congress Receipts is nonpartisan and factual. Describe records, not motives. Do not publish anything you cannot source to an official or primary record. Do not name donors. If you are unsure whether a claim is supportable, leave it out and say so in the pull request.
