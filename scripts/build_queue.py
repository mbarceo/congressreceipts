"""Keeps data/queue.json (the Backlog Queue page) in step with members.json, so the status of a tracked member is never typed by hand.

    python3 -I scripts/build_queue.py           rewrite data/queue.json
    python3 -I scripts/build_queue.py --check   exit 1 if it is out of date (used by status.py --strict)

Rule for every member in members.json (keyed by the bioguide id in its tracker.config.json):
  done      live, and on the hub (no "live": false and no "hub": false); url = https://congressreceipts.org/<path>/
  progress  everything else: live: false (not published) or hub: false (published but unfinished)
Entries for people with no tracker (status "skip", or hand-set "progress") are editorial and are kept exactly as they are.
A member with a placeholder bioguide id (X000000, a member-elect) is left out. Prints what changed.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://congressreceipts.org/"
QUEUE = os.path.join(ROOT, "data", "queue.json")

def derive():
    out = {}
    for m in json.load(open(os.path.join(ROOT, "members.json")))["members"]:
        cfg = json.load(open(os.path.join(ROOT, m["path"], "tracker.config.json")))
        bio = cfg["member"]["bioguide"]
        if not re.fullmatch(r"[A-Z]\d{6}", bio) or bio == "X000000": continue
        done = m.get("live") is not False and m.get("hub") is not False
        out[bio] = {"status": "done", "url": f"{BASE}{m['path']}/"} if done else {"status": "progress"}
    return out

def render(note, entries):
    lines = [f' "_note": {json.dumps(note, ensure_ascii=False)}'] + [f' {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}' for k, v in entries.items()]
    return "{\n" + ",\n".join(lines) + "\n}\n"

def main(argv):
    old = json.load(open(QUEUE))
    note = old.pop("_note", "")
    members = derive()
    keep = {k: v for k, v in old.items() if k not in members}   # editorial entries for non-members
    new = {**dict(sorted(members.items(), key=lambda kv: list(old).index(kv[0]) if kv[0] in old else len(old))), **keep}
    text = render(note, new)
    changes = [k for k in new if old.get(k) != new[k]] + [k for k in old if k not in new]
    if "--check" in argv:
        if text != open(QUEUE).read(): print("data/queue.json is out of date: " + ", ".join(changes) + "\nRun: python3 -I scripts/build_queue.py"); sys.exit(1)
        print("data/queue.json is up to date"); return
    open(QUEUE, "w").write(text)
    print("changed: " + ", ".join(changes) if changes else "data/queue.json already up to date")

if __name__ == "__main__":
    main(sys.argv[1:])
