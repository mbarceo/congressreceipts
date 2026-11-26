"""One-screen health report for every tracked member. Offline and read-only: it never fetches anything or writes files.

    python3 -I scripts/status.py                 table for every member in members.json
    python3 -I scripts/status.py ca/rivas        one member, with details
    python3 -I scripts/status.py --strict        exit 1 if any live member has a problem (for CI or a pre-PR check)

Columns: flags from members.json (live/hub), rebuild state (see scripts/rebuild.py), roll calls in votes.json vs the shared
committed XML, claim verification counts (data/verification.json), whether the copied pages match site/, and whether the
public queue (data/queue.json) matches what scripts/build_queue.py derives from members.json. "stale" means a build step would run if you ran rebuild.py.
"""
import collections, glob, hashlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_queue, rebuild, runner

ROOT = runner.ROOT
PAGES = ["index", "money", "stances", "votes", "statements", "establishment", "townhalls", "sources"]

def jload(p, default=None):
    try: return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError): return default

def rollcall_count(chamber, congress):
    pat = "senate-*.xml" if chamber == "senate" else "*-roll*.xml"
    return len(glob.glob(os.path.join(ROOT, "data", "rollcalls", chamber, str(congress), pat)))

def short_hash(p):
    return hashlib.sha1(open(p, "rb").read()).hexdigest()[:8]

def check_member(mem, queue, expected_queue):
    path, problems, notes = mem["path"], [], []
    mdir = os.path.join(ROOT, path)
    cfg = jload(os.path.join(mdir, "tracker.config.json"))
    live = mem.get("live") is not False
    row = {"path": path, "live": "yes" if live else "NO", "hub": "no" if mem.get("hub") is False else "yes"}
    if not cfg:
        row.update(build="-", votes="-", claims="-", pages="-", queue="-"); problems.append("no tracker.config.json"); return row, problems, notes
    m = cfg["member"]
    # rebuild state (dry run, no cache write)
    state = jload(os.path.join(mdir, "data", ".rebuild_state.json"), {})
    stale, tracked = [], 0
    for step, inputs, outputs, raw in rebuild.STEPS:
        if step == "build_map" and m["chamber"] != "house": continue
        h, st = rebuild.step_status(mdir, cfg, state, step, inputs, outputs, raw)
        if st.startswith("skip"): continue
        tracked += 1
        if st == "stale": stale.append(step)
    row["build"] = "stale:" + str(len(stale)) if stale else "fresh"
    if stale: notes.append("stale build steps: " + ", ".join(stale) + (" (no cache yet: run rebuild.py --adopt if the data is known good)" if not state else ""))
    # votes vs shared rolls
    votes = jload(os.path.join(mdir, "data", "votes.json"), [])
    total = rollcall_count(m["chamber"], m.get("congress", 119))
    row["votes"] = f"{len(votes)}/{total}"
    if len(votes) != total: problems.append(f"votes.json has {len(votes)} roll calls, shared XML has {total}")
    # verification
    ver = jload(os.path.join(mdir, "data", "verification.json"), {})
    cnt = collections.Counter(v.get("status") for v in ver.values() if isinstance(v, dict))
    bad = cnt.get("failed", 0) + cnt.get("partial", 0)
    row["claims"] = f"{cnt.get('verified', 0)}ok" + (f" {cnt.get('partial', 0)}partial" if cnt.get("partial") else "") + (f" {cnt.get('failed', 0)}FAIL" if cnt.get("failed") else "") if ver else "none"
    if not ver: problems.append("no verification.json (run_checks never ran)")
    if bad: problems.append(f"{bad} claims partial/failed")
    # pages: copies must match site/; stubs (members.json "pages": "stub") only need a stub for every shared page
    out = []
    if mem.get("pages") == "stub":
        for f in sorted(os.listdir(os.path.join(ROOT, "site"))):
            if f.endswith(".html") and "site/shell.js" not in (open(os.path.join(mdir, f), encoding="utf-8").read() if os.path.isfile(os.path.join(mdir, f)) else ""):
                out.append(f"{f} is not a current stub")
    else:
        for f in ("site.js", "site.css"):
            src, cp = os.path.join(ROOT, "site", f), os.path.join(mdir, f)
            if not os.path.isfile(cp): out.append(f"{f} missing")
            elif short_hash(src) != short_hash(cp) and open(cp, encoding="utf-8").read().split("\n", 1)[-1] != open(src, encoding="utf-8").read(): out.append(f"{f} differs")
        sj = os.path.join(mdir, "index.html")
        if os.path.isfile(sj):
            mv = re.search(r"site\.js\?v=(\w+)", open(sj, encoding="utf-8").read())
            if mv and mv.group(1) != short_hash(os.path.join(ROOT, "site", "site.js")): out.append("cache key old")
        elif live: out.append("index.html missing")
    row["pages"] = ("stub" if mem.get("pages") == "stub" else "ok") if not out else "STALE"
    if out and live: problems.append("pages not published from current site/: " + ", ".join(out) + " (run publish.py)")
    # queue: data/queue.json is derived from members.json by scripts/build_queue.py
    q, want = queue.get(m["bioguide"]), expected_queue.get(m["bioguide"])
    row["queue"] = q.get("status", "?") if q else "-"
    if want and q != want: problems.append(f"data/queue.json says {q} but members.json implies {want} (run build_queue.py)")
    return row, problems, notes

def main(argv):
    only = [a for a in argv if not a.startswith("--")]
    members = jload(os.path.join(ROOT, "members.json"))["members"]
    queue = {k: v for k, v in jload(os.path.join(ROOT, "data", "queue.json"), {}).items() if not k.startswith("_")}
    expected = build_queue.derive()
    rows, bad = [], 0
    for mem in members:
        if only and mem["path"] not in only: continue
        rows.append((mem, *check_member(mem, queue, expected)))
    cols = ["path", "live", "hub", "build", "votes", "claims", "pages", "queue"]
    w = {c: max(len(c), *(len(r[1][c]) for r in rows)) for c in cols}
    print("  ".join(c.ljust(w[c]) for c in cols))
    for mem, row, problems, notes in rows:
        print("  ".join(row[c].ljust(w[c]) for c in cols))
        if mem.get("live") is not False and problems: bad += 1
    print()
    for mem, row, problems, notes in rows:
        for p in problems: print(f"{row['path']}: {'PROBLEM' if mem.get('live') is not False else 'draft'}: {p}")
        for n in notes: print(f"{row['path']}: note: {n}")
    known = {jload(os.path.join(ROOT, m['path'], 'tracker.config.json'), {}).get('member', {}).get('bioguide') for m in members}
    for k in queue:
        if k not in known: print(f"data/queue.json: {k} ({queue[k].get('status')}) has no entry in members.json")
    if "--strict" in argv and bad: sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])
