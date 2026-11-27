"""Downloads every Senate roll call of the configured Congress from senate.gov into data/rollcalls/senate/<congress>/senate-<year>-<NNNNN>.xml.

Reads the per-session vote menus (roll_call_lists/vote_menu_<congress>_<session>.xml) to learn how many votes
exist, then fetches each vote's XML. Files already downloaded are skipped, so reruns only pick up new votes.
Usage: python3 -I scripts/fetch_votes_senate.py
"""
import os, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, ROOT, rollcalls_dir

CONGRESS = int(M.get("congress", 119))
FIRST_YEAR = 2023 + 2 * (CONGRESS - 118)       # 119th Congress: sessions 1 and 2 are 2025 and 2026
OUT = rollcalls_dir("senate", CONGRESS); os.makedirs(OUT, exist_ok=True)   # shared, committed
UA = {"User-Agent": "Mozilla/5.0 (civic-research)"}

def get(url):
    for attempt in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):    # blocked or rate limited: stop, never retry around it
                sys.exit(f"Blocked (HTTP {e.code}) at {url}: stopping. Wait a few hours, then rerun; downloaded files are kept.")
            if attempt == 2: raise
            time.sleep(3)
        except Exception as e:
            if attempt == 2: raise
            time.sleep(3)

total = 0
for session in (1, 2):
    year = FIRST_YEAR + session - 1
    try:
        menu = ET.fromstring(get(f"https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_{CONGRESS}_{session}.xml"))
    except Exception as e:
        print(f"session {session}: no vote menu yet ({e})"); continue
    numbers = sorted(int(v.findtext("vote_number")) for v in menu.iter("vote"))
    new = 0
    for n in numbers:
        path = os.path.join(OUT, f"senate-{year}-{n:05d}.xml")
        if os.path.exists(path) and os.path.getsize(path) > 500: continue
        body = get(f"https://www.senate.gov/legislative/LIS/roll_call_votes/vote{CONGRESS}{session}/vote_{CONGRESS}_{session}_{n:05d}.xml")
        if b"<roll_call_vote" not in body[:400]:
            print(f"  skipped {year}-{n}: not a roll-call file"); continue
        open(path, "wb").write(body); new += 1
        time.sleep(3)
    total += len(numbers)
    print(f"{year} (session {session}): {len(numbers)} roll calls listed, {new} downloaded now")
print(total, "Senate roll calls in this Congress")
