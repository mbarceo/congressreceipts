"""Publishes every member's site from the shared pages in site/.

For each member in members.json with format "shared", copies site/*.html, site.js and site.css into the member's
folder (ca/padilla/ ...) and bakes that member's name into each page's <title> and description, so link previews and
search engines see "Who Funds Alex Padilla" rather than {{name}}; site.js fills the rest at runtime from the
member's tracker.config.json. Legacy members keep their own pages and are left alone.
The copied files are build output: edit site/, never a member's copy. Each copy starts with a comment saying so.
Usage: python3 -I scripts/publish.py            (all members)
       python3 -I scripts/publish.py ca/padilla (one member)
"""
import json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from new_tracker import tokens, fill

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "site")
HEAD = re.compile(r"(<title>.*?</title>|<meta name=\"description\" content=\"[^\"]*\">)", re.S)
MARK = "<!-- Built from site/{f} by scripts/publish.py. Edit site/{f}, not this copy. -->\n"

members = json.load(open(os.path.join(REPO, "members.json")))["members"]
only = sys.argv[1:] or None
for mem in members:
    if mem.get("format") != "shared" or (only and mem["path"] not in only): continue
    dst = os.path.join(REPO, mem["path"])
    m = json.load(open(os.path.join(dst, "tracker.config.json")))["member"]
    t = tokens(m, m.get("chamber", "house"))
    n = 0
    for f in sorted(os.listdir(SITE)):
        src = os.path.join(SITE, f)
        if f.endswith(".html"):
            s = open(src, encoding="utf-8").read()
            s = HEAD.sub(lambda x: fill(x.group(0), t), s)
            s = s.replace("<!doctype html>\n", "<!doctype html>\n" + MARK.format(f=f), 1)
            open(os.path.join(dst, f), "w", encoding="utf-8").write(s); n += 1
        elif f in ("site.js", "site.css"):
            shutil.copyfile(src, os.path.join(dst, f)); n += 1
    left = [x for x in re.findall(r"\{\{\w+\}\}", "".join(HEAD.findall(open(os.path.join(dst, "index.html")).read())))]
    print(f"{mem['path']}: {n} files" + (f"; unfilled head tokens {left}" if left else ""))
