"""Builds data/directory.json and data/zips.json for "Find your rep": every member of Congress, and which
districts each ZIP code area falls in.

Sources (official, downloaded into data/directory_raw/, which stays out of git):
  House:  the House Clerk's member list, clerk.house.gov/xml/lists/MemberData.xml (name, party, state, district, bioguide)
  Senate: the newest senate.gov roll-call XML in data/rollcalls/senate (all 100 senators with name, party, state);
          senate.gov's own contact list refuses automated downloads
  ZIPs:   Census Bureau ZCTA-to-119th-district relationship file. A ZIP code area that crosses a district line maps
          to every district it touches, and the page says so.
Tracked members are matched through members.json (House by bioguide, Senate by LIS id).
Usage: python3 -I scripts/build_directory.py
"""
import datetime, glob, json, os, re, subprocess
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO, "data/directory_raw"); os.makedirs(RAW, exist_ok=True)
SRC = {"house.xml": "https://clerk.house.gov/xml/lists/MemberData.xml",
       "zcta_cd119.txt": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_zcta520_natl.txt"}
FIPS = {"01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA",
        "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA",
        "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY",
        "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX",
        "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR", "78": "VI"}

for f, u in SRC.items():
    p = os.path.join(RAW, f)
    if not os.path.exists(p) or os.path.getsize(p) < 10000:
        subprocess.run(["curl", "-s", "-L", "-A", "Mozilla/5.0", "--max-time", "120", "-o", p, u], check=True)

reg = [x for x in json.load(open(os.path.join(REPO, "members.json")))["members"] if x.get("live", True) and x.get("hub", True)]
tracked = {m["voteId"]: m["path"] for m in reg}
members = []

# House: one entry per seat; vacancies are kept so a ZIP in a vacant district says so
for m in ET.parse(os.path.join(RAW, "house.xml")).getroot().iter("member"):
    sd = m.findtext("statedistrict") or ""; st, dn = sd[:2], sd[2:]
    i = m.find("member-info"); bid = (i.findtext("bioguideID") or "").strip()
    name = re.sub(r"\s+", " ", (i.findtext("official-name") or "").strip())
    seat = f"{st}-{'AL' if dn in ('00', '') else str(int(dn))}"
    members.append({"name": name or "Vacant", "party": (i.findtext("party") or "").strip(), "state": st, "seat": seat,
                    "chamber": "house", "id": bid, "vacant": not name, "path": tracked.get(bid)})

# Senate: the newest roll-call file lists all 100 senators
sen = sorted(glob.glob(os.path.join(REPO, "data/rollcalls/senate/*/senate-*.xml")), key=os.path.basename)
if not sen: raise SystemExit("No Senate roll-call XML under data/rollcalls/senate; run fetch_votes_senate first.")
for m in ET.parse(sen[-1]).getroot().iter("member"):
    lis = m.findtext("lis_member_id")
    members.append({"name": f"{m.findtext('first_name')} {m.findtext('last_name')}", "party": m.findtext("party"), "state": m.findtext("state"),
                    "seat": "Senate", "chamber": "senate", "id": lis, "vacant": False, "path": tracked.get(lis)})

# ZIP code area -> district(s)
zips = {}
with open(os.path.join(RAW, "zcta_cd119.txt"), encoding="utf-8-sig") as f:
    head = f.readline().strip().split("|"); gi, zi = head.index("GEOID_CD119_20"), head.index("GEOID_ZCTA5_20")
    for line in f:
        c = line.rstrip("\n").split("|")
        z, g = c[zi], c[gi]
        if not z or g[:2] not in FIPS or g[2:] == "ZZ": continue
        seat = f"{FIPS[g[:2]]}-{'AL' if g[2:] in ('00', '98') else str(int(g[2:]))}"
        zips.setdefault(z, [])
        if seat not in zips[z]: zips[z].append(seat)

missing = [p for p in tracked.values() if p not in {m["path"] for m in members}]
if missing: raise SystemExit(f"Tracked members not found in the official lists: {missing}")
json.dump({"members": members, "built": datetime.date.today().isoformat(),
           "sources": {"house": SRC["house.xml"], "senate": "senate.gov roll-call XML (" + os.path.basename(sen[-1]) + ")", "zips": SRC["zcta_cd119.txt"]}},
          open(os.path.join(REPO, "data/directory.json"), "w"), separators=(",", ":"))
json.dump(zips, open(os.path.join(REPO, "data/zips.json"), "w"), separators=(",", ":"))
h, s = sum(m["chamber"] == "house" for m in members), sum(m["chamber"] == "senate" for m in members)
print(f"{h} House seats ({sum(m['vacant'] for m in members)} vacant), {s} senators, {len(zips)} ZIP codes; "
      f"{sum(1 for m in members if m['path'])} tracked; zips.json {os.path.getsize(os.path.join(REPO, 'data/zips.json')) // 1024} KB")
