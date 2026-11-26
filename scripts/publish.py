"""Publishes every member's site from the shared pages in site/.

For each member in members.json with format "shared", copies site/*.html, site.js and site.css into the member's
folder (ca/padilla/ ...) and bakes that member's name into each page's <title> and description, so link previews and
search engines see "Who Funds Alex Padilla" rather than {{name}}; site.js fills the rest at runtime from the
member's tracker.config.json. Every member page, legacy ones included, also gets the shared Congress Receipts header (add_header).
The copied files are build output: edit site/, never a member's copy. Each copy starts with a comment saying so.
A member with "pages": "stub" in members.json gets thin stub pages instead of copies: each holds only the member's own
<title> and description plus a script tag for site/shell.js, which loads the shared page from site/ at view time. Stubs only
change when a member's name or a page's title/description changes, because the ?v= cache keys live in site/manifest.json
(written here, fetched fresh by shell.js). Copies of site.js and site.css are removed from a stub member's folder.
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

def add_header(html, base):
    """Adds the Congress Receipts header (logo, Home, Find your rep, Who's showing up, Leaders tracker) to a member page,
    using the hub's own hub.css and hub.js so there is one header everywhere. Safe to run again."""
    if "hub.js" in html: return html
    html = html.replace('<link rel="stylesheet" href="site.css">', f'<link rel="stylesheet" href="site.css">\n<link rel="stylesheet" href="{base}hub.css">', 1)
    return html.replace("</body>", f'<script src="{base}hub.js" data-base="{base}"></script>\n</body>', 1)

import hashlib
def ver(path):
    """Short content hash: pages link site.js?v=<hash>, so a browser never runs a stale copy after an update."""
    return hashlib.sha1(open(path, "rb").read()).hexdigest()[:8]
VER = {f: ver(os.path.join(SITE, f)) for f in ("site.js", "site.css")}
VER.update({f: ver(os.path.join(REPO, f)) for f in ("hub.js", "hub.css")})
def stamp(html):
    for f, v in VER.items():
        html = re.sub(r'(src|href)="((?:\.\./)*)' + re.escape(f) + r'(?:\?v=\w+)?"', lambda m: f'{m.group(1)}="{m.group(2)}{f}?v={v}"', html)
    return html

# Cache keys for stub pages: shell.js reads this, so stubs never need rewriting when a shared file changes
json.dump(VER, open(os.path.join(SITE, "manifest.json"), "w"), indent=1, sort_keys=True); open(os.path.join(SITE, "manifest.json"), "a").write("\n")

STUB = """<!doctype html>
<!-- Stub built by scripts/publish.py. The page itself is site/{f}, loaded by site/shell.js. Edit site/{f}, not this file. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{head}
<script src="{base}site/shell.js" data-page="{page}"></script>
</head>
<body>
<noscript>This page needs JavaScript. Sources and data are linked from <a href="{base}">the home page</a>.</noscript>
</body>
</html>
"""

members = json.load(open(os.path.join(REPO, "members.json")))["members"]
only = sys.argv[1:] or None
for mem in members:
    if only and mem["path"] not in only: continue
    if mem.get("live") is False: print(f"{mem['path']}: skipped (live: false in members.json)"); continue
    dst = os.path.join(REPO, mem["path"]); base = "../" * mem["path"].count("/") + "../"
    if mem.get("format") != "shared":
        # Legacy members keep their own pages; they only get the shared header added in place
        n = 0
        for f in sorted(os.listdir(dst)):
            if f.endswith(".html"):
                p = os.path.join(dst, f); s0 = open(p, encoding="utf-8").read(); s1 = add_header(s0, base)
                if s1 != s0: open(p, "w", encoding="utf-8").write(s1); n += 1
        print(f"{mem['path']} (legacy): header added to {n} pages"); continue
    m = json.load(open(os.path.join(dst, "tracker.config.json")))["member"]
    t = tokens(m, m.get("chamber", "house"))
    n = 0
    stub = mem.get("pages") == "stub"
    if stub:
        for f in ("site.js", "site.css"):   # no longer used by this member's pages
            if os.path.exists(os.path.join(dst, f)): os.remove(os.path.join(dst, f))
    for f in sorted(os.listdir(SITE)):
        src = os.path.join(SITE, f)
        if stub and f.endswith(".html"):
            head = "\n".join(fill(x, t) for x in HEAD.findall(open(src, encoding="utf-8").read()))   # description, then title
            open(os.path.join(dst, f), "w", encoding="utf-8").write(STUB.format(f=f, head=head, base=base, page=f[:-5])); n += 1
        elif f.endswith(".html"):
            s = open(src, encoding="utf-8").read()
            s = HEAD.sub(lambda x: fill(x.group(0), t), s)
            s = add_header(s, base)
            s = stamp(s)
            s = s.replace("<!doctype html>\n", "<!doctype html>\n" + MARK.format(f=f), 1)
            open(os.path.join(dst, f), "w", encoding="utf-8").write(s); n += 1
        elif f in ("site.js", "site.css") and not stub:
            shutil.copyfile(src, os.path.join(dst, f)); n += 1
    left = [x for x in re.findall(r"\{\{\w+\}\}", "".join(HEAD.findall(open(os.path.join(dst, "index.html")).read())))]
    print(f"{mem['path']}: {n} files" + (f"; unfilled head tokens {left}" if left else ""))

# The hub pages (home, find, attendance, leaders, backlog, about) use the same stylesheet as the trackers and the shared header files
shutil.copyfile(os.path.join(SITE, "site.css"), os.path.join(REPO, "site.css"))
for f in ("index.html", "find.html", "attendance.html", "leaders.html", "leadership.html", "backlog.html", "about.html"):
    p = os.path.join(REPO, f); s0 = open(p, encoding="utf-8").read(); s1 = stamp(s0)
    if s1 != s0: open(p, "w", encoding="utf-8").write(s1)
print("hub pages stamped")
