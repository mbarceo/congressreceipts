"""Checks bill claims against govinfo's official BILLSTATUS records (data/billstatus/), writes data/bill_checks.json.

Each entry: bill, the role claimed (sponsor, cosponsor or none), and an optional public law that must be listed.
Usage: python3 -I scripts/verify_bills.py
"""
import json, os, sys, time, urllib.request
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import M, ROOT

OUT = os.path.join(ROOT, "data/billstatus"); os.makedirs(OUT, exist_ok=True)
ME = M["bioguide"]
BILLS = [  # (bill, role claimed, public law claimed or None)
    ("hr5157", "sponsor", None),      # Streamlining American Manufacturing Strategy Act (stand-alone; never left committee)
    ("s1071", "none", "119-60"),      # FY2026 NDAA, which carried it as Sec. 8802
    ("hr7374", "sponsor", None),      # Housing Without Fear Act
    ("hr6644", "none", "119-101"),    # 21st Century ROAD to Housing Act
]
url_for = lambda b: f"https://www.govinfo.gov/bulkdata/BILLSTATUS/119/{''.join(c for c in b if c.isalpha())}/BILLSTATUS-119{b}.xml"
res = {}
for b, role, law in BILLS:
    p = os.path.join(OUT, b + ".xml")
    if not os.path.exists(p) or os.path.getsize(p) < 1000:
        try:
            open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(url_for(b), headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
            time.sleep(0.7)
        except Exception as e:
            res[b] = {"ok": False, "issue": f"fetch failed: {e}"}; continue
    bill = ET.parse(p).getroot().find("bill")
    kids = lambda tag: list(bill.find(tag)) if bill.find(tag) is not None else []
    sponsors = [s.findtext("bioguideId") for s in kids("sponsors")]
    cos = {c.findtext("bioguideId"): c.findtext("sponsorshipDate") for c in kids("cosponsors")}
    laws = [l.findtext("number") for l in kids("laws")]
    acts = sorted((a.findtext("actionDate"), a.findtext("text") or "") for a in kids("actions"))
    issues = []
    if role == "sponsor" and ME not in sponsors: issues.append(f"{M['short']} is not the sponsor")
    if role == "cosponsor" and ME not in cos: issues.append(f"{M['short']} is not a cosponsor")
    if law and law not in laws: issues.append(f"Public Law {law} not listed")
    res[b] = {"ok": not issues, "title": bill.findtext("title"), "role": role, "introduced": bill.findtext("introducedDate"),
              "laws": laws, "latestAction": acts[-1][0] if acts else None, "latestText": acts[-1][1][:120] if acts else None,
              "url": url_for(b), "issue": "; ".join(issues)}
    print("OK  " if not issues else "FAIL", b, "|", (res[b]["title"] or "")[:55], "| laws", laws, "| latest", res[b]["latestAction"], res[b]["issue"])
json.dump(res, open(os.path.join(ROOT, "data/bill_checks.json"), "w"), indent=1)
