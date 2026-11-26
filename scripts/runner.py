"""Runs one shared script for one member: the pure-Python engine behind ./tr (no zsh needed, works on macOS, Linux, WSL, CI).

    python3 -I scripts/runner.py ca/padilla build_votes
    python3 -I scripts/runner.py ca/padilla run_checks

Does what the old zsh ./tr did: sets TRACKER_DIR, gives FEC / congress.gov scripts their API key (environment variable
first, macOS Keychain second; the key is never printed), cd's into the member folder, and runs the script with python3 -I.
Legacy members (a member-local scripts/ folder) still run their own scripts.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = {   # script -> (environment variable, Keychain service, where to get a key)
    "resolve_fec": "fec", "fetch_fec": "fec", "build_fec": "fec", "fetch_bills": "congress"}
KEY_INFO = {"fec": ("FEC_API_KEY", "fec-api-key"), "congress": ("CONGRESS_API_KEY", "congress-api-key")}

def api_key_env(script, env=None):
    """Environment for a script: adds its API key if it needs one. Exits with a clear message if none is found."""
    env = dict(os.environ if env is None else env)
    kind = KEYS.get(script)
    if not kind: return env
    var, service = KEY_INFO[kind]
    if env.get(var): return env
    try:
        out = subprocess.run(["security", "find-generic-password", "-a", env.get("USER", ""), "-s", service, "-w"],
                             capture_output=True, text=True)
        key = out.stdout.strip() if out.returncode == 0 else ""
    except FileNotFoundError:
        key = ""
    if not key:
        raise SystemExit(f"No {var} found. Set the {var} environment variable, or on macOS store it once with:\n"
                         f"  security add-generic-password -U -a \"$USER\" -s {service} -w")
    env[var] = key
    return env

def member_dir(member):
    d = os.path.join(ROOT, member.strip("/"))
    if not (os.path.isfile(os.path.join(d, "tracker.config.json")) or os.path.isdir(os.path.join(d, "scripts"))):
        raise SystemExit(f"No tracker.config.json in {d}")
    return d

def run(member, name, args=(), check=True, capture=False):
    """Run script `name` for `member`. run_checks is the four verification scripts in order. Returns the exit code."""
    d = member_dir(member)
    name = name[:-3] if name.endswith(".py") else name[:-3] if name.endswith(".sh") else name
    legacy = os.path.isdir(os.path.join(d, "scripts"))
    if legacy: print(f"(legacy member: using {member}/scripts)", file=sys.stderr)
    S = os.path.join(d, "scripts") if legacy else os.path.join(ROOT, "scripts")
    if name == "run_checks" and not legacy:
        steps = ["extract_claims", "verify_bills", "verify_computed", "verify_all"]
        for s in steps:
            code = run(member, s, args if s == steps[-1] else (), check=False)
            if code: return code
        return 0
    env = api_key_env(name); env["TRACKER_DIR"] = d
    if os.path.isfile(os.path.join(S, name + ".sh")):
        cmd = ["bash", os.path.join(S, name + ".sh")]   # the .sh scripts are written to run under bash (macOS, Linux, WSL)
    elif os.path.isfile(os.path.join(S, name + ".py")):
        cmd = [sys.executable, "-I", os.path.join(S, name + ".py")]
    else:
        raise SystemExit(f"No script {name} in {S}")
    proc = subprocess.run(cmd + list(args), cwd=d, env=env, capture_output=capture, text=True)
    if check and proc.returncode: sys.exit(proc.returncode)
    return proc.returncode if not capture else proc

if __name__ == "__main__":
    if len(sys.argv) < 3: raise SystemExit("Usage: ./tr <state/member> <script> [args]   e.g. ./tr ca/padilla build_votes")
    sys.exit(run(sys.argv[1], sys.argv[2], sys.argv[3:], check=False))
