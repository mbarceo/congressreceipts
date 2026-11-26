# How to update the Backlog Queue

The Backlog Queue page (`backlog.html`) lists every sitting member of Congress by state and chamber with the status of their tracker. It joins two files:

- `data/congress.json`: the roster, built by `scripts/build_roster.py` from the `unitedstates/congress-legislators` current-members file.
- `data/queue.json`: the status you edit by hand.

## Change a status

Edit `data/queue.json`. Keys are **bioguide ids**.

```json
{
 "R000620": {"status": "done", "url": "https://congressreceipts.org/ca/rivas/"},
 "G000598": {"status": "progress"}
}
```

| `status` | Shown as |
|---|---|
| `done` | Live (links to `url`) |
| `progress` | In progress |
| `next` | Next up |
| `skip` | Skipped |
| *(not listed)* | Not started |

Rules
- Mark `progress` when you start a tracker, so two people do not build the same member. Mark `done` with the live URL (`https://congressreceipts.org/<state>/<last>/`) when it is merged and published.
- Keep the file's one-line-per-member layout so diffs stay small.
- Do this in **its own small pull request** (queue changes only). That keeps it fast to merge and out of the way of data work.
- A member-elect has no bioguide id and is not on the roster, so cannot be listed until sworn in.

## Refresh the roster

Needed after resignations, special elections or the start of a new Congress:
```bash
curl -sL https://unitedstates.github.io/congress-legislators/legislators-current.json -o /tmp/legislators-current.json
python3 -I scripts/build_roster.py /tmp/legislators-current.json data/congress.json /tmp/congress.md
```
The third argument is a Markdown summary the page does not use; write it outside the repo. Review the diff of `data/congress.json`, then commit it.
