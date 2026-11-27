"""Downloads boundary shapes for the district map from the U.S. Census TIGERweb service.

Saves GeoJSON to data/geo/raw/. Usage: python3 -I scripts/fetch_geo.py
"""
import json, math, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M

ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
OUT = os.path.join(ROOT, "data/geo/raw")
os.makedirs(OUT, exist_ok=True)
BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
TILE = 0.4   # degrees per query tile

def get(name, service, layer, where="1=1", bbox=None, offset="0.0003"):
    q = {"where": where, "outFields": "GEOID,NAME,BASENAME", "returnGeometry": "true",
         "outSR": "4326", "f": "geojson", "maxAllowableOffset": offset, "geometryPrecision": "5"}
    # TIGERweb silently returns only part of the matches for a large bbox (no exceededTransferLimit flag, and
    # resultOffset returns nothing more), so a wide frame such as a district with islands or two distant areas
    # lost whole cities. Query the frame in tiles of at most TILE degrees and merge by GEOID. Two seconds between requests.
    tiles = [bbox]
    if bbox:
        x0, y0, x1, y1 = (float(v) for v in bbox.split(","))
        nx, ny = max(1, math.ceil((x1 - x0) / TILE)), max(1, math.ceil((y1 - y0) / TILE))
        tiles = [f"{x0 + (x1 - x0) * i / nx:.4f},{y0 + (y1 - y0) * j / ny:.4f},{x0 + (x1 - x0) * (i + 1) / nx:.4f},{y0 + (y1 - y0) * (j + 1) / ny:.4f}"
                 for i in range(nx) for j in range(ny)]
    feats, seen = [], set()
    for n, tile in enumerate(tiles):
        if n: time.sleep(2)
        tq = dict(q)
        if tile: tq.update({"geometry": tile, "geometryType": "esriGeometryEnvelope", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"})
        url = f"{BASE}{service}/MapServer/{layer}/query?" + urllib.parse.urlencode(tq)
        data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
        if "features" not in data: raise SystemExit(f"{name}: TIGERweb error {data.get('error')}")
        for f in data["features"]:
            k = (f.get("properties") or {}).get("GEOID") or id(f)
            if k not in seen: seen.add(k); feats.append(f)
    data = {"type": "FeatureCollection", "features": feats}
    with open(os.path.join(OUT, name + ".geojson"), "w") as f:
        json.dump(data, f)
    print(name, len(data.get("features", [])), "features", data.get("error", ""))

# "geoid" is the member's district in the 120th Congress (new map). A district that changed number can set "geoidOld"
# to the 119th-Congress district the member represented (Sánchez: CA-38 became CA-41); it defaults to "geoid".
GEOID_NEW = f"GEOID='{M['geoid']}'"
GEOID_OLD = f"GEOID='{M.get('geoidOld') or M['geoid']}'"
cds = {}
for name, svc, layer, where in (("cd120", "tigerWMS_Current", 54, GEOID_NEW), ("cd119", "Legislative", 4, GEOID_OLD)):
    get(name, svc, layer, where)
    cds[name] = json.load(open(os.path.join(OUT, name + ".geojson")))["features"][0]["geometry"]
# Map frame: both district shapes, padded, so the same script works for any district
pts = [p for g in cds.values() for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]) for r in poly for p in r]
pad = 0.06
BBOX = f"{min(p[0] for p in pts)-pad:.4f},{min(p[1] for p in pts)-pad:.4f},{max(p[0] for p in pts)+pad:.4f},{max(p[1] for p in pts)+pad:.4f}"
print("frame", BBOX)
# Places, CDPs and counties come from the member's own state (the first two digits of geoid are its FIPS code).
STATE = M["geoid"][:2]
get("places", "tigerWMS_Current", 28, f"STATE='{STATE}'", BBOX)
get("cdps", "tigerWMS_Current", 30, f"STATE='{STATE}'", BBOX)
if STATE == "06" and CFG["geo"]["countyFips"]:   # California trackers with named counties: those plus LA, Orange and Ventura as grey context (unchanged since the first maps)
    fips = ",".join(f"'{f}'" for f in CFG["geo"]["countyFips"] + ["06059", "06111", "06037"])
    get("counties", "tigerWMS_Current", 82, f"GEOID IN ({fips})", BBOX, "0.0008")
else:               # no named counties (every other state, or an unconfigured California tracker): every county of the state inside the frame; build_map colors the named ones and greys the rest
    get("counties", "tigerWMS_Current", 82, f"STATE='{STATE}'", BBOX, "0.0008")

# Communities: LA County's Board-approved Countywide Statistical Areas (CSAs). Unlike Census places, they split the
# City of Los Angeles into named communities (Pacoima, Sylmar, Van Nuys...), which is what CA-29 is mostly made of.
# Source: LA County Enterprise GIS, https://egis-lacounty.hub.arcgis.com/datasets/countywide-statistical-areas-csa
if "06037" not in CFG["geo"]["countyFips"]:   # the CSAs cover Los Angeles County only
    raise SystemExit(0)
CSA = "https://services.arcgis.com/RmCCgQtiZLDCtblq/ArcGIS/rest/services/Location_Service_Info/FeatureServer/4/query?"
q = {"where": "1=1", "outFields": "LABEL,CITY_TYPE,LCITY,COMMUNITY", "returnGeometry": "true", "outSR": "4326", "f": "geojson",
     "maxAllowableOffset": "0.0002", "geometryPrecision": "5", "geometry": BBOX, "geometryType": "esriGeometryEnvelope",
     "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"}
data = json.load(urllib.request.urlopen(urllib.request.Request(CSA + urllib.parse.urlencode(q), headers={"User-Agent": "Mozilla/5.0"}), timeout=90))
if "features" not in data: raise SystemExit(f"csa: LA County GIS error {data.get('error')}")
json.dump(data, open(os.path.join(OUT, "csa.geojson"), "w"))
print("csa", len(data["features"]), "features")
