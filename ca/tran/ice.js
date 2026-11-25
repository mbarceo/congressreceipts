// "Is he pro-ICE and pro-police?" evidence card, shared by the overview and the Stances tab.
// Renders into any element with id="iceCard". Items come from data/cards.json (built by scripts/build_cards.py from
// data/card_picks.json); vote wording, tallies and "Breaks with party" come from House Clerk roll calls in data/votes.json.
(function(){
  const load = window.__ttCards || (window.__ttCards = fetch("data/cards.json")
    .then(r => { if(!r.ok) throw new Error("data/cards.json " + r.status); return r.json(); })
    .then(d => Object.fromEntries(d.cards.map(c => [c.key, c]))));
  const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const fmt = d => /^\d{4}-\d{2}$/.test(d) ? `${MON[+d.slice(5)-1]} ${d.slice(0,4)}` : d;
  const esc = s => String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const TAG = {pro:"pp-isr", con:"pp-pal", mix:"pp-mix"};
  function group(g, compact){
    const n = k => g.items.filter(i=>i.s===k).length;
    const list = compact ? g.items.filter(i=>i.hi) : g.items;
    const lab = s => s==="pro" ? g.pro : s==="con" ? g.con : "Neither";
    return `<div class="ic-group">
      <div class="pp-head">
        <div class="pp-flag"><span class="pp-q">${esc(g.q)}</span><span class="pp-v">${esc(g.v)}</span></div>
        <p class="pp-sum">${esc(g.sum)}</p>
      </div>
      <div class="pp-count"><span><i class="pp-dot pp-isr"></i>${n("pro")} ${esc(g.pro)}</span><span><i class="pp-dot pp-pal"></i>${n("con")} ${esc(g.con)}</span>${n("mix")?`<span><i class="pp-dot pp-mix"></i>${n("mix")} neither</span>`:""}</div>
      <ul class="pp-list">${list.map(i=>`<li><span class="pp-date mono">${esc(fmt(i.d))}</span><span class="pp-tag ${TAG[i.s]}">${esc(lab(i.s))}</span><span class="pp-text">${esc(i.t)}${i.brk?' <span class="pill s-break">Breaks with party</span>':""}${i.unv?' <span class="pill s-unv">Unverified</span>':""} <a class="src" href="${esc(i.u)}"${i.u.startsWith("http")?' target="_blank" rel="noopener"':""}>Source</a></span></li>`).join("")}</ul>
    </div>`;
  }
  function render(GROUPS, el, compact){
    const total = GROUPS.reduce((s,g)=>s+g.items.length,0);
    el.innerHTML = GROUPS.map(g=>group(g, compact)).join("") +
      (compact ? `<a class="pp-more" href="stances.html#ice">See all ${total} items on the Stances tab →</a>` : "") +
      `<p class="muted" style="margin:0;font-size:.8rem">Votes are from House Clerk roll calls; statements from his press releases. "Breaks with party" means he voted against most House Democrats.</p>`;
  }
  // The Stances page builds its boxes on window load; if the data arrives later, rebuild them and honor the #hash.
  function refresh(keys){
    if(document.readyState !== "complete") return;
    if(typeof window.boxes === "function") window.boxes();
    const k = location.hash.slice(1), dlg = document.getElementById("detail");
    if(keys.includes(k) && typeof window.openDetail === "function" && !(dlg && dlg.open)) window.openDetail("flag", k);
  }
  load.then(all => {
    const GROUPS = ["ice", "police"].map(k => all[k]).filter(Boolean);
    window.TT = window.TT || {};
    GROUPS.forEach(g=>{ window.TT[g.key] = {q:g.q, v:g.v, sum:g.short, n:g.n, render:(el)=>{ el.innerHTML = group(g,false) + '<p class="muted" style="margin:0;font-size:.8rem">Votes are from House Clerk roll calls; statements from his press releases.</p>'; }}; });
    document.querySelectorAll("#iceCard").forEach(el=>render(GROUPS, el, el.dataset.compact==="1"));
    refresh(GROUPS.map(g => g.key));
  }).catch(e => console.error("ice card:", e));
})();
