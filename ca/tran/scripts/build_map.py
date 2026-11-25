"""Projects Census shapes in data/geo/raw into SVG paths for the district map: data/geo/map.json.

Usage: python3 -I scripts/build_map.py
"""
import json, math, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
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
CMAP = {"Los Angeles County": "LA", "Orange County": "OC"}
allc = load("counties")
counties = {CMAP[f["properties"]["NAME"]]: f["geometry"] for f in allc if f["properties"]["NAME"] in CMAP}
others = [f["geometry"] for f in allc if f["properties"]["NAME"] not in CMAP]
places = load("places") + load("cdps")

# Frame: union of both district shapes, padded
bs = [bbox(g) for g in cd.values()]
x0, y0 = min(b[0] for b in bs) - 0.035, min(b[1] for b in bs) - 0.03
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

feat = []
for f in places:
    g = f["geometry"]
    name = f["properties"]["BASENAME"]
    cdp = f["properties"]["NAME"].endswith("CDP")
    c, _ = inter_centroid(g, None, 0.004)
    lonlat = ((c[0] / KX) + x0, y1 - c[1] / KY)
    county = next((k for k, cg in counties.items() if contains(cg, *lonlat)), "")
    item = {"n": name, "cdp": cdp, "c": county, "d": path(g), "ctr": c}
    for k, dg in cd.items():
        pt, share = inter_centroid(g, dg)
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
