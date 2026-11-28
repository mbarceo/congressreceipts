"""Fallback for Find your rep: ZIP code area -> House district(s), computed from Census TIGERweb boundaries.

Use it only when the Census ZIP relationship file for a Congress is not published (see docs/howto/switch-to-120th.md).
It recomputes rows for the states whose districts changed and keeps every other row of data/zips.json.

How it works (stdlib only, so no polygon library):
  1. Districts: TIGERweb layer for the Congress (120th: tigerWMS_Current layer 54, 119th: Legislative layer 4).
  2. Which states changed: compare each district's AREALAND between the 119th and 120th layers (one request each, no geometry).
  3. For each changed state: download its district shapes and the ZIP code areas (ZCTAs) in tiles, two seconds apart.
  4. Sample a grid of points inside each ZIP area; a district gets the ZIP if at least MIN_SHARE of the sample points fall in it
     (0.2%, and always the district holding the most points). A sliver smaller than that may be missed; the Census file would list it.
  5. A ZIP that also touches an unchanged state keeps its rows for that state; only seats in changed states are replaced.

Usage: python3 -I scripts/build_zips_from_tiger.py --states UT[,LA...]|--changed [--congress 120] [--write]
       python3 -I scripts/build_zips_from_tiger.py --validate UT [--congress 119]
  --changed   work out the changed states from AREALAND (needs --congress 120)
  --validate  run the same method on one state for the given Congress and compare with data/zips.json
              (use --congress 119: the committed file is built from the 119th districts); prints the agreement, writes nothing
  --write     replace rows in data/zips.json (default is a dry run that prints a summary)
Go slow: one request at a time, two seconds apart; stop at the first 403 or 429 (repo rule). Cached under data/geo/raw/zips/.
"""
import json, math, os, sys, time, urllib.parse, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(REPO, "data/geo/raw/zips"); os.makedirs(CACHE, exist_ok=True)   # git-ignored (data/geo/raw)
BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
LAYER = {120: ("tigerWMS_Current", 54), 119: ("Legislative", 4)}
ZCTA = ("tigerWMS_Current", 2)
STATE_FIPS = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13",
              "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24", "MA": "25",
              "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36",
              "NC": "37", "ND": "38", "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48",
              "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56"}
FIPS_STATE = {v: k for k, v in STATE_FIPS.items()}
TILE = 0.4        # degrees per ZIP query tile (TIGERweb drops results for large boxes; same limit as fetch_geo.py)
GRID = 40         # sample points per side inside each ZIP area's bounding box
MIN_SHARE = 0.002  # a district needs this share of a ZIP's sample points to be listed
PAUSE = 2

def request(url, params):
    for k in range(2):
        time.sleep(PAUSE)
        try:
            req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "Mozilla/5.0"})
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            if e.code in (403, 429): raise SystemExit(f"HTTP {e.code} from TIGERweb: stop, wait some hours, then rerun (cached tiles are kept).")
            if k: raise
        except OSError:
            if k: raise

def query(service, layer, params):
    data = request(f"{BASE}{service}/MapServer/{layer}/query", {"f": "geojson" if params.get("returnGeometry") == "true" else "json", **params})
    if "features" not in data: raise SystemExit(f"TIGERweb error: {data.get('error')}")
    return data["features"]

def cached(name, fn):
    p = os.path.join(CACHE, name + ".json")
    if os.path.exists(p): return json.load(open(p))
    v = fn(); json.dump(v, open(p, "w")); return v

def seat_of(geoid):
    st, d = FIPS_STATE[geoid[:2]], geoid[2:]
    return f"{st}-{'AL' if d in ('00', '98') else str(int(d))}"

def areas(congress):
    svc, lay = LAYER[congress]
    fs = cached(f"areas{congress}", lambda: query(svc, lay, {"where": "1=1", "outFields": "GEOID,AREALAND", "returnGeometry": "false"}))
    return {f["attributes"]["GEOID"]: f["attributes"]["AREALAND"] for f in fs if f["attributes"]["GEOID"][:2] in FIPS_STATE}

def changed_states():
    new, old = areas(120), areas(119)
    return sorted({FIPS_STATE[g[:2]] for g in set(new) | set(old) if new.get(g) != old.get(g)})

def polys(geom):
    return geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]

def inside(x, y, rings):   # even-odd rule over every ring of one polygon (holes work)
    c = False
    for r in rings:
        j = len(r) - 1
        for i in range(len(r)):
            xi, yi, xj, yj = r[i][0], r[i][1], r[j][0], r[j][1]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
            j = i
    return c

def bbox(poly):
    xs = [p[0] for p in poly[0]]; ys = [p[1] for p in poly[0]]
    return min(xs), min(ys), max(xs), max(ys)

def districts(congress, st):
    svc, lay = LAYER[congress]
    fs = cached(f"cd{congress}_{st}", lambda: query(svc, lay, {"where": f"STATE='{STATE_FIPS[st]}'", "outFields": "GEOID", "returnGeometry": "true",
                "outSR": "4326", "maxAllowableOffset": "0.0005", "geometryPrecision": "5"}))
    return [(seat_of(f["properties"]["GEOID"]), [(p, bbox(p)) for p in polys(f["geometry"])]) for f in fs]

def zctas(st, dists):
    xs = [b[0] for _, ps in dists for _, b in ps] + [b[2] for _, ps in dists for _, b in ps]
    ys = [b[1] for _, ps in dists for _, b in ps] + [b[3] for _, ps in dists for _, b in ps]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    nx, ny = max(1, math.ceil((x1 - x0) / TILE)), max(1, math.ceil((y1 - y0) / TILE))
    out = {}
    for i in range(nx):
        for j in range(ny):
            box = f"{x0 + (x1 - x0) * i / nx:.4f},{y0 + (y1 - y0) * j / ny:.4f},{x0 + (x1 - x0) * (i + 1) / nx:.4f},{y0 + (y1 - y0) * (j + 1) / ny:.4f}"
            fs = cached(f"zcta_{st}_{i}_{j}", lambda: query(ZCTA[0], ZCTA[1], {"where": "1=1", "outFields": "ZCTA5", "returnGeometry": "true", "outSR": "4326",
                        "maxAllowableOffset": "0.0005", "geometryPrecision": "5", "geometry": box, "geometryType": "esriGeometryEnvelope",
                        "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"}))
            for f in fs:
                z = f["properties"].get("ZCTA5")
                if z and f.get("geometry"): out[z] = f["geometry"]
    return out

def seats_for(geom, dists):
    counts, total = {}, 0
    for poly in polys(geom):
        bx0, by0, bx1, by1 = bbox(poly)
        for a in range(GRID):
            for b in range(GRID):
                x, y = bx0 + (bx1 - bx0) * (a + .5) / GRID, by0 + (by1 - by0) * (b + .5) / GRID
                if not inside(x, y, poly): continue
                total += 1
                for seat, ps in dists:
                    if any(b0[0] <= x <= b0[2] and b0[1] <= y <= b0[3] and inside(x, y, p) for p, b0 in ps):
                        counts[seat] = counts.get(seat, 0) + 1; break
    if not total or not counts: return []
    top = max(counts, key=counts.get)
    return [s for s in counts if s == top or counts[s] / total >= MIN_SHARE]

def compute(congress, st):
    d = districts(congress, st)
    return {z: seats_for(g, d) for z, g in zctas(st, d).items()}

def arg(name):
    a = sys.argv[1:]; return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else None

if __name__ == "__main__":
    congress = int(arg("--congress") or 120)
    zpath = os.path.join(REPO, "data/zips.json"); zips = json.load(open(zpath))
    if arg("--validate"):
        st = arg("--validate"); got = compute(congress, st)
        same = diff = 0; bad = []
        for z, seats in got.items():
            ref = sorted(s for s in zips.get(z, []) if s.startswith(st + "-"))
            mine = sorted(s for s in seats if s.startswith(st + "-"))
            if not ref and not mine: continue
            if ref == mine: same += 1
            else: diff += 1; bad.append((z, ref, mine))
        print(f"{st} (Congress {congress}): {same} ZIPs match data/zips.json, {diff} differ ({100 * same / max(1, same + diff):.1f}% agree)")
        for b in bad[:15]: print("  ZIP", b[0], "committed", b[1], "computed", b[2])
        sys.exit(0)
    states = changed_states() if "--changed" in sys.argv else [s.strip().upper() for s in (arg("--states") or "").split(",") if s.strip()]
    if not states: raise SystemExit("Give --states XX[,YY] or --changed (see the docstring).")
    print("states to recompute:", ", ".join(states))
    keep = set(states)
    new = {}
    for st in states:
        for z, seats in compute(congress, st).items(): new.setdefault(z, []).extend(seats)
        print(st, "done")
    merged = dict(zips)
    for z, seats in new.items():
        others = [s for s in zips.get(z, []) if s.split("-")[0] not in keep]   # seats in states that are not being recomputed
        merged[z] = others + [s for s in dict.fromkeys(seats)]
    print(f"{len(new)} ZIP areas recomputed; {sum(1 for z in new if sorted(merged[z]) != sorted(zips.get(z, [])))} rows differ from data/zips.json")
    if "--write" in sys.argv:
        json.dump(merged, open(zpath, "w"), separators=(",", ":")); print("wrote data/zips.json")
