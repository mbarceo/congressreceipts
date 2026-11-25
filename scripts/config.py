"""Loads tracker.config.json so no script hardcodes a member, district or ID.

Usage inside a script:  from config import CFG, ROOT   (scripts run with `python3 -I scripts/x.py`,
so -I strips the script dir from sys.path; each script therefore adds it back explicitly).
"""
import json, os
ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
CFG = json.load(open(os.path.join(ROOT, "tracker.config.json")))
M, FEC = CFG["member"], CFG["fec"]

def need(value, what):
    """Stop with a clear message if a TODO config value is still unresolved."""
    if not value or str(value).startswith("TODO"):
        raise SystemExit(f"Set {what} in tracker.config.json first.")
    return value
