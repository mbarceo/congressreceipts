"""Downloads boundary shapes for the district map from the U.S. Census TIGERweb service.

Saves GeoJSON to data/geo/raw/. Usage: python3 -I scripts/fetch_geo.py
"""
import json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG, M

ROOT = os.environ.get("TRACKER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")   # member folder; set by ./tr
OUT = os.path.join(ROOT, "data/geo/raw")
os.makedirs(OUT, exist_ok=True)
BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"

def get(name, service, layer, where="1=1", bbox=None, offset="0.0003"):
    q = {"where": where, "outFields": "GEOID,NAME,BASENAME", "returnGeometry": "true",
         "outSR": "4326", "f": "geojson", "maxAllowableOffset": offset, "geometryPrecision": "5"}
    if bbox:
        q.update({"geometry": bbox, "geometryType": "esriGeometryEnvelope", "inSR": "4326",
                  "spatialRel": "esriSpatialRelIntersects"})
    url = f"{BASE}{service}/MapServer/{layer}/query?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    if "features" not in data: raise SystemExit(f"{name}: TIGERweb error {data.get('error')}")
    with open(os.path.join(OUT, name + ".geojson"), "w") as f:
        json.dump(data, f)
    print(name, len(data.get("features", [])), "features", data.get("error", ""))

GEOID = f"GEOID='{M['geoid']}'"
cds = {}
for name, svc, layer in (("cd120", "tigerWMS_Current", 54), ("cd119", "Legislative", 4)):
    get(name, svc, layer, GEOID)
    cds[name] = json.load(open(os.path.join(OUT, name + ".geojson")))["features"][0]["geometry"]
# Map frame: both district shapes, padded, so the same script works for any district
pts = [p for g in cds.values() for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]) for r in poly for p in r]
pad = 0.06
BBOX = f"{min(p[0] for p in pts)-pad:.4f},{min(p[1] for p in pts)-pad:.4f},{max(p[0] for p in pts)+pad:.4f},{max(p[1] for p in pts)+pad:.4f}"
print("frame", BBOX)
get("places", "tigerWMS_Current", 28, "STATE='06'", BBOX)
get("cdps", "tigerWMS_Current", 30, "STATE='06'", BBOX)
fips = ",".join(f"'{f}'" for f in CFG["geo"]["countyFips"] + ["06059", "06111", "06037"])
get("counties", "tigerWMS_Current", 82, f"GEOID IN ({fips})", BBOX, "0.0008")

# Communities: LA County's Board-approved Countywide Statistical Areas (CSAs). Unlike Census places, they split the
# City of Los Angeles into named communities (Pacoima, Sylmar, Van Nuys...), which is what CA-29 is mostly made of.
# Source: LA County Enterprise GIS, https://egis-lacounty.hub.arcgis.com/datasets/countywide-statistical-areas-csa
CSA = "https://services.arcgis.com/RmCCgQtiZLDCtblq/ArcGIS/rest/services/Location_Service_Info/FeatureServer/4/query?"
q = {"where": "1=1", "outFields": "LABEL,CITY_TYPE,LCITY,COMMUNITY", "returnGeometry": "true", "outSR": "4326", "f": "geojson",
     "maxAllowableOffset": "0.0002", "geometryPrecision": "5", "geometry": BBOX, "geometryType": "esriGeometryEnvelope",
     "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"}
data = json.load(urllib.request.urlopen(urllib.request.Request(CSA + urllib.parse.urlencode(q), headers={"User-Agent": "Mozilla/5.0"}), timeout=90))
if "features" not in data: raise SystemExit(f"csa: LA County GIS error {data.get('error')}")
json.dump(data, open(os.path.join(OUT, "csa.geojson"), "w"))
print("csa", len(data["features"]), "features")
