"""Reads Track AIPAC's published "Israel Lobby Total" for Derek Tran and each comparison member.

money.html used to have these numbers typed in by hand. This reads them from each member's public page
(https://www.trackaipac.com/tracker/people/<slug>) and records the URL and read date, so the Money page can show
them with a source. Track AIPAC says it compiles from fec.gov but does not itemize; the page labels it as a
third-party figure. Writes data/trackaipac.json. Usage: python3 -I scripts/fetch_trackaipac.py
"""
import datetime, json, os, re, time, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data/trackaipac.json")
BASE = "https://www.trackaipac.com/tracker/people/"
PAUSE = 0.6   # seconds between requests

# name, district, group, Track AIPAC slug. Slugs are the ones money.html already linked to.
PEOPLE = [
    ("Derek Tran", "CA-45", "me", "member-derek-tran-ca-45-d"),
    ("Young Kim (R)", "CA-40", "neighbor", "member-young-kim-ca-40-r"),
    ("Dave Min", "CA-47", "neighbor", "member-dave-min-ca-47-d"),
    ("Lou Correa", "CA-46", "neighbor", "member-lou-correa-ca-46-d"),
    ("Hakeem Jeffries", "NY-8", "leadership", "member-hakeem-jeffries-ny-08-d"),
    ("Pete Aguilar", "CA-33", "leadership", "member-pete-aguilar-ca-33-d"),
    ("Katherine Clark", "MA-5", "leadership", "member-katherine-clark-ma-05-d"),
    ("Josh Gottheimer", "NJ-5", "centrist", "member-josh-gottheimer-nj-05-d"),
    ("Ritchie Torres", "NY-15", "centrist", "member-ritchie-torres-ny-15-d"),
    ("Jared Golden", "ME-2", "centrist", "member-jared-golden-me-02-d"),
    ("Ro Khanna", "CA-17", "progressive", "member-ro-khanna-ca-17-d"),
    ("Greg Casar", "TX-35", "progressive", "member-greg-casar-tx-35-d"),
    ("Rashida Tlaib", "MI-12", "progressive", "member-rashida-tlaib-mi-12-d"),
    ("Alexandria Ocasio-Cortez", "NY-14", "progressive", "member-alexandria-ocasio-cortez-ny-14-d"),
    ("Ilhan Omar", "MN-5", "progressive", "member-ilhan-omar-mn-05-d"),
]

def read(u):
    try:
        h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        return None, False, str(e)
    m = re.search(r"Israel Lobby Total</dt><dd[^>]*>\s*\$([\d,]+)", h) or re.search(r"Israel Lobby Total[\s\S]{0,300}?\$([\d,]+)", h)
    total = int(m.group(1).replace(",", "")) if m else None
    return total, bool(re.search(r"rejects?\s+AIPAC", h, re.I)), "" if m else "no Israel Lobby Total on page"

out, missing = [], []
for i, (name, dist, group, slug) in enumerate(PEOPLE):
    if i: time.sleep(PAUSE)
    u = BASE + slug
    total, rejects, err = read(u)
    if total is None:
        missing.append((name, u, err)); continue
    out.append({"name": name, "dist": dist, "group": group, "total": total, "url": u, "rejects": rejects, "me": group == "me"})
    print(f"{name:<26} {dist:<6} ${total:>10,}{'  rejects AIPAC' if rejects else ''}")
if missing:
    print("\nNOT READ:", *missing, sep="\n  ")
if not out:
    raise SystemExit("nothing read; data/trackaipac.json left unchanged")
json.dump({"read": datetime.date.today().isoformat(), "source": "Track AIPAC (trackaipac.com), Israel Lobby Total", "members": out},
          open(OUT, "w"), indent=1)
print("wrote", os.path.relpath(OUT, ROOT), len(out), "members")
