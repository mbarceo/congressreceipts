"""Projects Census shapes in data/geo/raw into SVG paths for the district map: data/geo/map.json.

Usage: python3 -I scripts/build_map.py
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG

ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
RAW = os.path.join(ROOT, "data/geo/raw")
load = lambda n: json.load(open(os.path.join(RAW, n + ".geojson")))["features"]

def rings(geom):
    if geom["type"] == "Polygon": return [geom["coordinates"]]
    return geom["coordinates"]  # MultiPolygon: list of polygons

def pip(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside

def contains(geom, x, y):
    for poly in rings(geom):
        if pip(x, y, poly[0]) and not any(pip(x, y, h) for h in poly[1:]):
            return True
    return False

def bbox(geom):
    pts = [p for poly in rings(geom) for r in poly for p in r]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)

cd = {"new": load("cd120")[0]["geometry"], "old": load("cd119")[0]["geometry"]}
CMAP = CFG["geo"]["counties"]
allc = load("counties")
counties = {CMAP[f["properties"]["NAME"]]: f["geometry"] for f in allc if f["properties"]["NAME"] in CMAP}
others = [f["geometry"] for f in allc if f["properties"]["NAME"] not in CMAP]
# Base layer: LA County Countywide Statistical Areas when fetched (they split the City of LA into communities),
# else Census places + CDPs (whole cities only).
USE_CSA = os.path.exists(os.path.join(RAW, "csa.geojson"))
places = load("csa") if USE_CSA else load("places") + load("cdps")

def csa_name(props):
    lab = (props.get("LABEL") or "").strip()
    if lab.startswith("Los Angeles - "): return lab[len("Los Angeles - "):], "la"      # City of LA community
    if lab.startswith("City of "): return lab[len("City of "):], "city"               # another incorporated city
    if lab.startswith("Unincorporated - "): return lab[len("Unincorporated - "):], "uninc"
    return lab, "other"

# Frame: union of both district shapes, padded
bs = [bbox(g) for g in cd.values()]
x0, y0 = min(b[0] for b in bs) - CFG["geo"]["padLon"], min(b[1] for b in bs) - CFG["geo"]["padLat"]
x1, y1 = max(b[2] for b in bs) + 0.035, max(b[3] for b in bs) + 0.025
W = 900
KX = W / (x1 - x0)
KY = KX / math.cos(math.radians((y0 + y1) / 2))
H = round((y1 - y0) * KY)
proj = lambda lon, lat: (round((lon - x0) * KX, 1), round((y1 - lat) * KY, 1))

def path(geom):
    out = []
    for poly in rings(geom):
        for r in poly:
            pts = [proj(*p) for p in r]
            d = "M" + "L".join(f"{x:g},{y:g}" for x, y in pts) + "Z"
            out.append(d)
    return "".join(out)

def inter_centroid(a, b, step=0.0015):
    """Approximate centroid (projected) and area share of a∩b by grid sampling."""
    bx0, by0, bx1, by1 = bbox(a)
    sx = sy = n = tot = 0
    y = by0
    while y <= by1:
        x = bx0
        while x <= bx1:
            if contains(a, x, y):
                tot += 1
                if b is None or contains(b, x, y):
                    sx += x; sy += y; n += 1
            x += step
        y += step
    if not n: return None, 0
    return proj(sx / n, sy / n), n / tot

def overlaps(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

feat = []
cdb = {k: bbox(g) for k, g in cd.items()}
for f in places:
    g = f["geometry"]
    if not g: continue
    if USE_CSA:
        name, kind = csa_name(f["properties"])
        cdp = kind == "uninc"
    else:
        name, kind = f["properties"]["BASENAME"], "city"
        cdp = f["properties"]["NAME"].endswith("CDP")
    gb = bbox(g)
    step0 = max(0.002, ((gb[2] - gb[0]) * (gb[3] - gb[1]) / 900) ** 0.5)   # ~900 samples per shape
    c, _ = inter_centroid(g, None, step0)
    if c is None: continue
    lonlat = ((c[0] / KX) + x0, y1 - c[1] / KY)
    county = next((k for k, cg in counties.items() if contains(cg, *lonlat)), "") or next(iter(counties), "")
    item = {"n": name, "kind": kind, "cdp": cdp, "c": county, "d": path(g), "ctr": c}
    for k, dg in cd.items():
        if not overlaps(gb, cdb[k]): continue
        step = max(0.0012, ((gb[2] - gb[0]) * (gb[3] - gb[1]) / 4000) ** 0.5)  # ~4000 samples: share accurate to ~1-2%
        pt, share = inter_centroid(g, dg, step)
        if share > 0.01:
            item[k] = {"lbl": pt, "share": round(share, 3)}
    feat.append(item)

out = {"w": W, "h": H, "x0": x0, "y1": y1, "kx": KX, "ky": KY,
       "counties": {k: path(g) for k, g in counties.items()},
       "other": "".join(path(g) for g in others),
       "cd": {k: path(g) for k, g in cd.items()},
       "places": feat}
with open(os.path.join(ROOT, "data/geo/map.json"), "w") as f:
    json.dump(out, f, separators=(",", ":"))
print("frame", W, "x", H)
for p in sorted(feat, key=lambda p: p["n"]):
    print(f'{p["n"]:18} {p["c"]:2} new={p.get("new",{}).get("share","-"):<6} old={p.get("old",{}).get("share","-")}')
