"""Downloads the member's official portrait into assets/portrait.jpg and records its source in tracker.config.json.

Every tracker page shows this photo, so run it right after setting up the config. Sources, in priority order (official
or public-domain government photos keyed by bioguide ID):
  1. Bioguide, the official congressional directory (bioguide.congress.gov/photo/<ID>.jpg): kept current
  2. House only: House Clerk member images (clerk.house.gov/images/members/<ID>.jpg)
  3. congress.gov (img/member/<id>_200.jpg)
  4. The public-domain congressional image set (unitedstates.github.io/...): larger but can be outdated
The first real JPEG of reasonable size is kept, and the later sources are not requested. Look at the saved photo to confirm it's current.
Usage: python3 -I scripts/fetch_portrait.py
"""
import json, os, struct, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M, ROOT

bid = M["bioguide"]
sources = [f"https://bioguide.congress.gov/photo/{bid}.jpg"] + \
          ([f"https://clerk.house.gov/images/members/{bid}.jpg"] if M.get("chamber", "house") == "house" else []) + [
    f"https://www.congress.gov/img/member/{bid.lower()}_200.jpg",
    f"https://unitedstates.github.io/images/congress/450x550/{bid}.jpg",
]

def jpeg_size(b):
    """(width, height) of a JPEG, or None if it isn't one."""
    if b[:2] != b"\xff\xd8": return None
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF: i += 1; continue
        marker, seg = b[i + 1], struct.unpack(">H", b[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", b[i + 5:i + 9]); return w, h
        i += 2 + seg
    return None

found = []
for url in sources:
    try:
        body = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read()
    except Exception as e:
        print("  no photo at", url, f"({e})"); continue
    size = jpeg_size(body)
    if not size or size[0] < 150 or len(body) < 8000:
        print("  not a usable photo at", url); continue
    found.append((size[0] * size[1], url, body, size))
    break   # first usable source in priority order wins; do not call the remaining hosts (go slow on government sites)
if not found:
    raise SystemExit("No official portrait found. Ask the user before using any other photo.")
# Take the first usable source in priority order, not the largest: bioguide is the official directory and is kept
# current, while the larger public-domain copies can be years old (Schiff's is his House-era photo).
_, url, body, size = found[0]
os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
open(os.path.join(ROOT, "assets/portrait.jpg"), "wb").write(body)
CFG["member"].update({"portrait": "assets/portrait.jpg", "portraitSource": url, "portraitSize": list(size)})
json.dump(CFG, open(os.path.join(ROOT, "tracker.config.json"), "w"), indent=2, ensure_ascii=False)
print(f"Saved assets/portrait.jpg ({size[0]}x{size[1]}) from {url}")
