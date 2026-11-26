# How to rebuild the hub pages

The hub pages (home, Who's showing up, Leaders tracker, Find your rep, Backlog Queue) read JSON from the root `data/` folder. Rebuild it after a member's data changes or a member is added.

```bash
python3 -I scripts/build_attendance.py     # home + Who's showing up  → data/attendance.json
python3 -I scripts/build_leaders.py        # Leaders tracker          → data/leaders.json
python3 -I scripts/build_directory.py      # Find your rep            → data/directory.json, data/zips.json
```

## What each needs

- **`build_attendance.py`** reads `members.json`, each member's `data/votes.json`, `data/events.json`, portrait, **and each member's raw roll-call XML in `data/raw/`**, which it recounts as an independent check. Raw files are not in git, so on a fresh clone download them first for **every** registered member:
  ```bash
  ./tr ca/rivas fetch_votes && ./tr ca/tran fetch_votes && ./tr ca/garcia fetch_votes
  ./tr ca/padilla fetch_votes_senate        # or copy senate-*.xml from another senator's data/raw/
  ```
  It refuses to build ("Not built: …") if a member's `votes.json` disagrees with the official XML, if two members of one chamber cover different roll-call ranges (refetch the older tracker's votes and `build_votes`), if an event has no source, or if a portrait is missing.
- **`build_leaders.py`** reads only each member's committed data (alignment, establishment, FEC leadership, verification). No raw files.
- **`build_directory.py`** downloads the House Clerk member list and the Census ZIP file into `data/directory_raw/` (ignored by git). Re-run after a special election.

## Adding a member to the hub

1. Finish the member's tracker and pass `run_checks`.
2. Add them to `members.json` (and set `eventsResearched` honestly; `false` shows that town halls have not been researched).
3. Make sure every entry in their `data/events.json` has a source.
4. Rebuild the three hub files above, commit them, and publish the member's pages ([publish-and-deploy.md](publish-and-deploy.md)).

Registering a member in `members.json` before their data is complete will make `build_attendance.py` fail or show incomplete numbers. Add them last.
