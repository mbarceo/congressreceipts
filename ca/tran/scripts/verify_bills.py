"""Verifies bill sponsorship, cosponsorship and House passage claims using official govinfo BILLSTATUS XML.

Saves each record in data/billstatus/ and writes data/bill_checks.json. Usage: python3 -I scripts/verify_bills.py
"""
import json, os, time, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data/billstatus"); os.makedirs(OUT, exist_ok=True)
TRAN = "T000491"
# (bill, claimed role, also check House passage?)
BILLS = [
 ("hr1637","sponsor",False),("hr5788","sponsor",True),("hr4746","sponsor",False),("hr4775","sponsor",False),("hr8066","sponsor",False),
 ("hr9883","sponsor",False),("hr10613","sponsor",False),("hr10108","sponsor",False),("hr6678","sponsor",False),("hr7969","sponsor",False),
 ("hres366","sponsor",False),("hres1235","sponsor",False),("hconres50","sponsor",False),("hres528","sponsor",False),("hres948","sponsor",False),
 ("hr3565","cosponsor",False),("hr2102","cosponsor",True),("hr4849","cosponsor",False),("hr4962","cosponsor",False),("hr6215","cosponsor",False),
 ("hr4966","cosponsor",False),("hr5673","cosponsor",False),("hr3122","cosponsor",False),("hr2725","cosponsor",False),("hr537","cosponsor",False),
 ("hr5653","cosponsor",False),("hr7297","cosponsor",False),("hr5973","cosponsor",False),("hr7852","cosponsor",False),("hr3779","cosponsor",False),
 ("hr12","cosponsor",False),("hr9941","cosponsor",False),("hr2029","cosponsor",False),("hr1877","cosponsor",False),("hr9187","cosponsor",False),
 ("hr842","cosponsor",False),("hr787","cosponsor",True),("hres996","cosponsor",False),("hr832","cosponsor",True),
]
def path_for(b):
    t = "".join(ch for ch in b if ch.isalpha()); return f"https://www.govinfo.gov/bulkdata/BILLSTATUS/119/{t}/BILLSTATUS-119{b}.xml"
res = {}
for b, role, passage in BILLS:
    p = os.path.join(OUT, b + ".xml")
    if not os.path.exists(p) or os.path.getsize(p) < 1000:
        try:
            data = urllib.request.urlopen(urllib.request.Request(path_for(b), headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read()
            open(p, "wb").write(data)
        except Exception as e:
            res[b] = {"ok": False, "issue": f"fetch failed: {e}"}; continue
        time.sleep(0.7)
    bill = ET.parse(p).getroot().find("bill")
    title = bill.findtext("title")
    sponsors = [s.findtext("bioguideId") for s in bill.find("sponsors")] if bill.find("sponsors") is not None else []
    cos = {c.findtext("bioguideId"): c.findtext("sponsorshipDate") for c in (bill.find("cosponsors") if bill.find("cosponsors") is not None else [])}
    actions = [(a.findtext("actionDate"), a.findtext("text") or "") for a in bill.find("actions")] if bill.find("actions") is not None else []
    intro = bill.findtext("introducedDate")
    is_role = (TRAN in sponsors) if role == "sponsor" else (TRAN in cos)
    passed = [d for d, t in actions if any(k in t for k in ("Passed/agreed to in House", "On passage Passed", "On motion to suspend the rules and pass the bill", "agreed to in House"))]
    latest = max((d for d, _ in actions), default=None)
    r = {"ok": is_role, "title": title, "role": role, "introduced": intro, "cosponsored": cos.get(TRAN), "latestAction": latest,
         "housePassed": passed[:1] or None, "url": path_for(b)}
    if not is_role: r["issue"] = f"Tran is not listed as {role}"
    if passage and not passed: r["ok"] = False; r["issue"] = (r.get("issue","") + " no House passage action found").strip()
    res[b] = r
    print(("OK  " if r["ok"] else "FAIL"), b, role, "|", (title or "")[:60], "| cosp", r["cosponsored"], "| intro", intro, "| latest", latest, "| passed", r["housePassed"], "|", r.get("issue",""))
json.dump(res, open(os.path.join(ROOT, "data/bill_checks.json"), "w"), indent=1)
print(sum(1 for r in res.values() if r.get("ok")), "of", len(res), "bill claims confirmed")
