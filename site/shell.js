// Loader for thin member pages (members.json "pages": "stub"). Built by hand; not generated.
//
// A stub page (e.g. ca/tran/money.html) holds only the member-specific <head> (title, description, link preview) and one
// <script src="../../site/shell.js" data-page="money">. This script fetches the shared page (site/money.html) and
// site/manifest.json (current ?v= hashes), fills in the stub's own <title> and description, points site.css / site.js /
// hub.css / hub.js at the shared files, and swaps the assembled page in. The page then runs exactly as a copied one would:
// the address bar still shows the member folder, so tracker.config.json and data/... load from there.
// Because the hashes live in manifest.json (fetched fresh each time), editing site/ never changes a stub.
(function(){
  "use strict";
  const me = document.currentScript;
  if(!me) return;
  const page = me.dataset.page || "index";
  const base = me.getAttribute("src").replace(/site\/shell\.js(\?.*)?$/, "");   // "../../" from ca/tran/
  const site = base + "site/";
  const opts = {cache: "no-cache"};
  const manifestP = fetch(site + "manifest.json", opts).then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const pageP = fetch(site + page + ".html", opts).then(r => { if(!r.ok) throw new Error(r.status); return r.text(); });
  const hide = document.createElement("style");   // no flash of the empty stub
  hide.textContent = "body{visibility:hidden}";
  document.head.appendChild(hide);

  Promise.all([manifestP, pageP]).then(([man, html]) => {
    const v = f => man[f] ? "?v=" + man[f] : "";
    const own = sel => { const e = document.head.querySelector(sel); return e ? e.outerHTML : null; };
    const title = own("title"), desc = own('meta[name="description"]');
    if(title) html = html.replace(/<title>[\s\S]*?<\/title>/, () => title);
    if(desc) html = html.replace(/<meta name="description" content="[^"]*">/, () => desc);
    const css = `<link rel="stylesheet" href="${site}site.css${v("site.css")}">`;   // hub.css goes right after it, as publish.py does for copies
    html = html.replace('<link rel="stylesheet" href="site.css">', () => css + `\n<link rel="stylesheet" href="${base}hub.css${v("hub.css")}">`)
               .replace('<script src="site.js"></script>', () => `<script src="${site}site.js${v("site.js")}"></script>`);
    html = html.replace("</body>", `<script src="${base}hub.js${v("hub.js")}" data-base="${base}"></script>\n</body>`);
    document.open(); document.write(html); document.close();
  }).catch(err => {
    hide.remove();
    document.body.innerHTML = '<p style="font:16px system-ui;padding:24px">This page could not be loaded. Please reload, or <a href="' + base + '">go to the home page</a>.</p>';
    console.error("shell.js:", err);
  });
})();
