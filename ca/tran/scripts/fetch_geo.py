"""Downloads boundary shapes for the district map from the U.S. Census TIGERweb service.

Saves GeoJSON to data/geo/raw/. Usage: python3 -I scripts/fetch_geo.py
"""
import json, os, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data/geo/raw")
os.makedirs(OUT, exist_ok=True)
BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
BBOX = "-118.20,33.66,-117.76,33.96"  # map frame (lon/lat)

def get(name, service, layer, where="1=1", bbox=None, offset="0.0003"):
    q = {"where": where, "outFields": "GEOID,NAME,BASENAME", "returnGeometry": "true",
         "outSR": "4326", "f": "geojson", "maxAllowableOffset": offset, "geometryPrecision": "5"}
    if bbox:
        q.update({"geometry": bbox, "geometryType": "esriGeometryEnvelope", "inSR": "4326",
                  "spatialRel": "esriSpatialRelIntersects"})
    url = f"{BASE}{service}/MapServer/{layer}/query?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    with open(os.path.join(OUT, name + ".geojson"), "w") as f:
        json.dump(data, f)
    print(name, len(data.get("features", [])), "features", data.get("error", ""))

get("cd120", "tigerWMS_Current", 54, "GEOID='0645'")
get("places", "tigerWMS_Current", 28, "STATE='06'", BBOX)
get("cdps", "tigerWMS_Current", 30, "STATE='06'", BBOX)
get("counties", "tigerWMS_Current", 82, "GEOID IN ('06037','06059','06071','06065')", BBOX, "0.0008")
get("cd119", "Legislative", 4, "GEOID='0645'")
