"""Writes the redirect pages that replace an old per-member repo's site after the move to this repo.

The old repo keeps only index.html and 404.html. Both send visitors to the same page in the new location
(congressreceipts.org/ca-rep-29-tracker/money.html -> congressreceipts.org/ca/rivas/money.html), by script, with a
meta refresh to the member's home page and a visible link as fallbacks. The old repo's history keeps the old site.
Usage: python3 -I scripts/redirect_stub.py <old-repo-name> <new-path> <output-folder>
       python3 -I scripts/redirect_stub.py ca-rep-29-tracker ca/rivas "~/luz rivas tracker"
"""
import os, sys

old, new, out = sys.argv[1], sys.argv[2].strip("/"), os.path.expanduser(sys.argv[3])
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>This tracker has moved</title>
<link rel="canonical" href="https://congressreceipts.org/{new}/">
<meta http-equiv="refresh" content="3; url=https://congressreceipts.org/{new}/">
<script>
  // Same page, new home: /{old}/money.html -> /{new}/money.html
  var rest = location.pathname.replace(/^\\/{old}\\/?/, "").replace(/^\\//, "");
  location.replace("https://congressreceipts.org/{new}/" + rest + location.search + location.hash);
</script>
<style>body{{font-family:system-ui,sans-serif;background:#111916;color:#e3ebe6;display:grid;place-items:center;min-height:100vh;margin:0;padding:16px}}a{{color:#93b8a3}}</style>
</head>
<body>
<p>This tracker has moved to <a href="https://congressreceipts.org/{new}/">congressreceipts.org/{new}</a>.</p>
</body>
</html>
"""
os.makedirs(out, exist_ok=True)
for f in ("index.html", "404.html"):
    open(os.path.join(out, f), "w").write(PAGE.format(old=old, new=new))
print(f"Wrote index.html and 404.html to {out}: /{old}/ -> /{new}/")
