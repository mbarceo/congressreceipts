// Extracts every sourced claim on the site into data/claims.json (the claims registry).
// Usage: node scripts/extract_claims.js
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(ROOT, f), "utf8");
const H = "https://tran.house.gov/media/press-releases/";
const R = n => "https://clerk.house.gov/Votes/" + n, CLERK = R, CLERK_V = R;
const CAMP = "https://web.archive.org/web/20241101090742/https://www.derektranforcongress.com/";
const PP = "https://projects.propublica.org/itemizer/committee/C00851790/pac-donations/";

// Pull a literal (array or object) that starts at `const NAME =` and evaluate it with the helpers above.
function literal(src, name){
  const i = src.indexOf("const " + name + " =");
  if(i < 0) throw new Error("missing " + name);
  let j = src.indexOf("=", i) + 1;
  while(/\s/.test(src[j])) j++;
  const open = src[j], close = open === "[" ? "]" : "}";
  let depth = 0, k = j, inStr = null, esc = false;
  for(; k < src.length; k++){
    const c = src[k];
    if(inStr){ if(esc) esc = false; else if(c === "\\") esc = true; else if(c === inStr) inStr = null; continue; }
    if(c === '"' || c === "'" || c === "`"){ inStr = c; continue; }
    if(c === open) depth++; else if(c === close){ depth--; if(depth === 0) break; }
  }
  return eval("(" + src.slice(j, k + 1) + ")");
}
const strip = s => String(s || "").replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
const claims = [];
const add = (page, section, c) => claims.push({id: `${page}:${section}:${claims.filter(x=>x.page===page&&x.section===section).length + 1}`, page, section, ...c});

// Stances topics
const st = read("stances.html");
literal(st, "STANCES").forEach(x => add("stances", x.t, {date: x.d, text: x.s, quote: x.q || null, url: x.u, urls: x.also ? [x.u, ...x.also] : undefined, flags: {brk: !!x.brk, unv: !!x.unv, none: !!x.none}}));
// Overview promises
const ov = read("index.html");
literal(ov, "PROMISES").forEach(p => {
  add("overview", "promise:" + p.issue, {text: "Promise: " + p.promise, quote: p.quote ? p.promise : null, url: p.src, kind: "promise"});
  p.actions.forEach(a => add("overview", "promise:" + p.issue, {text: a.text, url: a.u || null}));
});
// HTML list items with a source link (overview, establishment, money)
function htmlItems(file, page){
  const s = read(file);
  const re = /<li>([\s\S]*?)<\/li>/g; let m;
  while((m = re.exec(s))){
    if(m[1].includes("${")) continue;
    const all = [...m[1].matchAll(/href="([^"]+)"/g)].map(h => h[1]);
    const ext = all.filter(h => h.startsWith("http")), loc = all.filter(h => !h.startsWith("http"));
    const hrefs = ext.length ? ext : loc.map(h => "local:" + h);
    const text = strip(m[1]).replace(/\s+(Source|Roll call|Money tab|ProPublica|KQED|CalMatters|Jewish Insider|FEC data|FEC totals below|FEC|CPC members|CPC|J Street|NBC News|CBS News|AP|Roundtable|Red to Blue|Frontline|NDC members|Task force|Endorsement|Primary result|Laken Riley|H\.Res\. 488|Blue Dogs|Problem Solvers|Computed from roll calls|Track AIPAC|CA Secretary of State|Wikipedia, citing the Secretary of State)(?=\s|$)/g, " ").trim();
    if(text.length > 30) add(page, "list", {text, url: hrefs[0] || null, urls: hrefs});
  }
}
htmlItems("index.html", "overview");
htmlItems("establishment.html", "establishment");
htmlItems("money.html", "money");
// Evidence cards (data/cards.json, built by scripts/build_cards.py; rendered by palestine.js, ice.js and corporate.js)
const CARDS = Object.fromEntries(JSON.parse(read("data/cards.json")).cards.map(c => [c.key, c]));
CARDS.palestine.items.forEach(x => add("palestine", x.s, {date: x.d, text: x.t, url: x.u, urls: x.urls, flags: {unv: !!x.unv}}));
["ice", "police"].forEach(k => CARDS[k].items.forEach(x => add(k, x.s, {date: x.d, text: x.t, url: x.u, urls: x.urls, flags: {brk: !!x.brk}})));
CARDS.corporate.items.forEach(x => add("corporate", x.s, {date: x.d, text: x.t, url: x.u, urls: x.urls, flags: {brk: !!x.brk, unv: !!x.unv}}));
// Establishment timeline
const est = read("establishment.html"); literal(est, "TL").forEach(([d, k, t, u]) => add("establishment", "timeline", {date: d, text: t, url: u}));
// Money: pro-Israel rows
const mon = read("money.html"); literal(mon, "ISRAEL").rows.forEach(r => add("money", "pro-israel", {text: r.f + " - " + r.w, url: r.u}));

fs.writeFileSync(path.join(ROOT, "data/claims.json"), JSON.stringify(claims, null, 1));
const byHost = {};
claims.forEach(c => { const h = c.url ? (c.url.match(/^https?:\/\/([^/]+)/) || [,"local"])[1] : "none"; byHost[h] = (byHost[h] || 0) + 1; });
console.log(claims.length, "claims"); console.log(byHost);
