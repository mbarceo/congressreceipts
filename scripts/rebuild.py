"""Rebuilds a member's page data (the offline BUILD stage) in the right order, skipping steps whose inputs did not change.

    python3 -I scripts/rebuild.py ca/rivas            one member
    python3 -I scripts/rebuild.py --all               every live member in members.json
    python3 -I scripts/rebuild.py ca/rivas --dry-run  show what is stale, change nothing
    python3 -I scripts/rebuild.py ca/rivas --force    ignore the cache and rebuild every step
    python3 -I scripts/rebuild.py ca/rivas --adopt    record the current files as up to date (no build); use once for an existing tracker
    python3 -I scripts/rebuild.py ca/rivas --checks   also run run_checks afterwards (it fetches live pages: once per change)

It never touches the network: fetch_* scripts (votes, statements, FEC, bills) stay separate and manual, so the
"go slow on other people's websites" rules are not affected. Steps whose raw input is not in git (FEC raw, Census shapes)
are skipped when that raw folder is absent, and the committed output is used as is.
A step is stale when its output is missing or the hash of its inputs (files, the script, shared code) differs from
the hash saved in <member>/data/.rebuild_state.json (git-ignored; per-checkout, so a fresh clone rebuilds once).
"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner

ROOT = runner.ROOT
SHARED = ["scripts/config.py", "scripts/votes_common.py"]
# (step, inputs relative to the member folder, outputs, raw folder that must exist or the step is skipped)
STEPS = [
    ("build_votes",         ["tracker.config.json", "@rollcalls"],                                  ["data/votes.json"], None),
    ("build_alignment",     ["tracker.config.json", "data/votes.json"],                             ["data/alignment.json"], None),
    ("build_fec",           ["tracker.config.json", "data/fec/raw"],                                ["data/fec/summary.json"], "data/fec/raw"),
    ("build_establishment", ["tracker.config.json", "data/fec/raw", "data/alignment.json", "data/establishment_items.json"],
                                                                                                     ["data/establishment.json", "data/fec/establishment_calc.json", "data/fec/leadership.json"], "data/fec/raw"),
    ("build_stances",       ["tracker.config.json", "data/stance_picks.json", "data/votes.json", "data/statements.json", "data/statements_full.json", "data/trackaipac.json", "data/fec/summary.json"],
                                                                                                     ["data/stances.json"], None),
    ("build_promises",      ["tracker.config.json", "data/promises.json", "data/votes.json", "data/statements.json"],
                                                                                                     ["data/promises_built.json"], None),
    ("build_cards",         ["tracker.config.json", "data/card_picks.json", "data/stances.json", "data/votes.json", "data/statements.json", "data/fec/summary.json", "data/fec/establishment_calc.json"],
                                                                                                     ["data/cards.json"], None),
    ("build_overview",      ["tracker.config.json", "data/cards.json", "data/events.json", "data/promises_built.json", "data/stances.json", "data/statements.json", "data/statements_full.json", "data/votes.json"],
                                                                                                     ["data/overview.json"], None),
    ("build_map",           ["tracker.config.json", "data/geo/raw"],                                 ["data/geo/map.json"], "data/geo/raw"),
]

def load_json(p, default=None):
    try: return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError): return default

def hash_path(h, p):
    """Hash a file's bytes, or a folder's file names and sizes (the roll-call folders hold ~1,600 files)."""
    if os.path.isfile(p):
        h.update(open(p, "rb").read())
    elif os.path.isdir(p):
        for dp, _, fs in sorted(os.walk(p)):
            for f in sorted(fs): h.update(f"{os.path.join(dp, f)}:{os.path.getsize(os.path.join(dp, f))}".encode())
    else:
        h.update(b"missing")

def output_hash(mdir, outputs):
    """Hash of what the step wrote, so a hand-edit or a git checkout of a generated file also counts as stale."""
    h = hashlib.sha256()
    for o in outputs: hash_path(h, os.path.join(mdir, o))
    return h.hexdigest()

def input_hash(mdir, cfg, step, inputs):
    h = hashlib.sha256()
    for rel in [f"scripts/{step}.py"] + SHARED:
        hash_path(h, os.path.join(ROOT, rel))
    for rel in inputs:
        if rel == "@rollcalls":
            m = cfg["member"]; rel = os.path.relpath(os.path.join(ROOT, "data", "rollcalls", m["chamber"], str(m.get("congress", 119))), mdir)
        hash_path(h, os.path.normpath(os.path.join(mdir, rel)))
    return h.hexdigest()

def step_status(mdir, cfg, state, step, inputs, outputs, raw):
    """(hash, status) for one step, computed now so it sees the outputs of steps that just ran."""
    if raw and not os.path.isdir(os.path.join(mdir, raw)):
        return None, f"skip: {raw} is not in this checkout (raw data is not committed)"
    h = input_hash(mdir, cfg, step, inputs)
    missing = [o for o in outputs if not os.path.exists(os.path.join(mdir, o))]
    return h, ("stale" if missing or state.get(step) != h + ":" + output_hash(mdir, outputs) else "fresh")

def save_state(mdir, state):
    json.dump(state, open(os.path.join(mdir, "data", ".rebuild_state.json"), "w"), indent=1, sort_keys=True)

def members_to_run(args):
    ms = json.load(open(os.path.join(ROOT, "members.json")))["members"]
    return [m["path"] for m in ms if m.get("live") is not False] if "--all" in args else [a for a in args if not a.startswith("--")]

def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    names = members_to_run(argv)
    if not names: raise SystemExit(__doc__)
    failed = []
    for member in names:
        mdir = runner.member_dir(member)
        cfg = load_json(os.path.join(mdir, "tracker.config.json"))
        if cfg is None: raise SystemExit(f"{member}: no tracker.config.json (legacy members are not handled by rebuild.py)")
        state = load_json(os.path.join(mdir, "data", ".rebuild_state.json"), {})
        print(f"== {member}")
        upstream_changed = False   # in a dry run, anything after a stale step is reported as stale too
        for step, inputs, outputs, raw in STEPS:
            if step == "build_map" and cfg["member"]["chamber"] != "house": continue
            h, status = step_status(mdir, cfg, state, step, inputs, outputs, raw)
            if status.startswith("skip"): print(f"  {step:20} {status}"); continue
            if "--adopt" in flags: state[step] = h + ":" + output_hash(mdir, outputs); print(f"  {step:20} adopted"); continue
            if "--force" in flags: status = "stale"
            if "--dry-run" in flags:
                if status == "stale": upstream_changed = True
                print(f"  {step:20} {'would rebuild' if status == 'stale' or upstream_changed else 'fresh'}"); continue
            if status != "stale": print(f"  {step:20} fresh"); continue
            print(f"  {step:20} rebuilding ...")
            proc = runner.run(member, step, check=False, capture=True)
            if proc.returncode:
                print(f"  {step:20} FAILED (exit {proc.returncode}); later steps depend on it, stopping {member}\n{proc.stdout[-1500:]}{proc.stderr[-1500:]}")
                failed.append(f"{member}:{step}"); break
            state[step] = h + ":" + output_hash(mdir, outputs)   # h was computed before this step ran; its inputs are unchanged by it
        if "--dry-run" not in flags: save_state(mdir, state)
        if "--checks" in flags and "--dry-run" not in flags and not failed:
            print("  run_checks (fetches live pages) ...")
            if runner.run(member, "run_checks", check=False): failed.append(f"{member}:run_checks")
    if failed: raise SystemExit("Failed: " + ", ".join(failed))

if __name__ == "__main__":
    main(sys.argv[1:])
