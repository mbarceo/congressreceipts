"""Builds data/leaders.json for the Leaders Tracker: how closely each member sides with their party's leader.

For each member in members.json, from that member's own built data (nothing is typed here):
  votes  data/alignment.json: agreement with the leader on every vote both cast, and on the votes where Democrats
         split (the leader is the peer named in the member's config: House Hakeem Jeffries, Senate Chuck Schumer);
         party-unity rate and rank among Democrats
  splits data/establishment.json (or establishment_votes.json in older trackers): how many times they split
  money  data/fec/leadership.json: what the leaders' committees gave, by cycle
  checks data/verification.json: how many of the tracker's claims passed the source checks, and when
  verdict the Establishment page's own headline (members.json "establishment" for trackers that don't store it)
Usage: python3 -I scripts/build_leaders.py
"""
import json, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: (lambda f: json.load(open(f)) if os.path.exists(f) else None)(os.path.join(REPO, *p))
LEADER = {"house": "Hakeem Jeffries", "senate": "Chuck Schumer"}
out = []
for m in J("members.json")["members"]:
    p = m["path"]; al = J(p, "data/alignment.json") or {}
    cfg = J(p, "tracker.config.json") or {}
    leader = (cfg.get("leader") or {}).get("name") or LEADER[m["chamber"]]
    peer = next((x for x in al.get("peers", []) if x["name"] == leader), {})
    es = J(p, "data/establishment.json"); ev = J(p, "data/establishment_votes.json")
    nums = (es or {}).get("nums", {})
    lead = J(p, "data/fec/leadership.json") or {}
    cycles = sorted({k[1:] for v in lead.values() for k in v if k.startswith("y")})
    money = {c: round(sum(v.get("y" + c, 0) for v in lead.values())) for c in cycles}
    vr = J(p, "data/verification.json") or {}
    recs = [r for r in vr.values() if isinstance(r, dict) and r.get("status")]
    checks = {"verified": sum(r["status"] in ("verified", "negative-finding") for r in recs), "total": len(recs),
              "checked": max((r.get("checked") or "" for r in recs), default="") or None} if recs else None
    verdict = (es or {}).get("headline") or (m.get("establishment") or {}).get("headline")
    out.append({"name": m["name"], "party": m["party"], "seat": m["seat"], "chamber": m["chamber"], "path": p + "/",
                "portrait": f"{p}/{m['portrait']}", "leader": leader,
                "agree": peer.get("all"), "agreeN": peer.get("allN") or nums.get("both") or (ev or {}).get("both"),
                "agreeSplit": peer.get("contested"), "splitVotes": al.get("contested"),
                "splits": nums.get("ndiff") if nums.get("ndiff") is not None else (ev or {}).get("splits"),
                "unity": al.get("memberUnity", al.get("tranUnity")), "rank": al.get("memberRank", al.get("tranRank")), "dems": al.get("dems"),
                "money": money, "moneyTotal": sum(money.values()) if money else None,
                "verdict": verdict if verdict and verdict != "TBD" else None, "checks": checks})
json.dump({"members": out}, open(os.path.join(REPO, "data/leaders.json"), "w"), indent=1)
for x in out:
    print(f'{x["name"]:13} with {x["leader"]:16} {x["agree"]}% all, {x["agreeSplit"]}% on {x["splitVotes"]} split votes; splits {x["splits"]}; '
          f'unity {x["unity"]}% (rank {x["rank"]}/{x["dems"]}); leader money {x["money"]}; verdict {x["verdict"]}')
