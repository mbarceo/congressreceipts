// "Is he pro-Palestine?" evidence card, shared by the overview and the Stances tab.
// Renders into any element with id="palestineCard". Items come from data/cards.json (built by scripts/build_cards.py
// from data/card_picks.json; votes and money figures are generated from the data files). Each item is sourced.
(function(){
  const load = window.__ttCards || (window.__ttCards = fetch("data/cards.json")
    .then(r => { if(!r.ok) throw new Error("data/cards.json " + r.status); return r.json(); })
    .then(d => Object.fromEntries(d.cards.map(c => [c.key, c]))));
  const DIR = {pal:["Toward Palestinians / conditions on aid","pp-pal"], isr:["Toward Israel","pp-isr"], mixed:["Both","pp-mix"]};
  const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const fmt = d => /^\d{4}-\d{2}$/.test(d) ? `${MON[+d.slice(5)-1]} ${d.slice(0,4)}` : d;
  const esc = s => String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  function render(C, el, compact){
    const ITEMS = C.items;
    const n = k => ITEMS.filter(i=>i.s===k).length;
    const list = compact ? ITEMS.slice(0,5) : ITEMS;
    el.innerHTML = `
      <div class="pp-head">
        <div class="pp-flag" role="img" aria-label="Pro-Palestine: ${esc(C.v.toLowerCase())} record"><span class="pp-q">${esc(C.q)}</span><span class="pp-v">${esc(C.v)}</span></div>
        <p class="pp-sum">${esc(C.sum)}</p>
      </div>
      <div class="pp-count"><span><i class="pp-dot pp-pal"></i>${n("pal")} toward Palestinians or conditions on aid</span><span><i class="pp-dot pp-isr"></i>${n("isr")} toward Israel</span><span><i class="pp-dot pp-mix"></i>${n("mixed")} both</span></div>
      <ul class="pp-list">${list.map(i=>`<li><span class="pp-date mono">${esc(fmt(i.d))}</span><span class="pp-tag ${DIR[i.s][1]}">${DIR[i.s][0]}</span><span class="pp-text">${esc(i.t)}${i.brk?' <span class="pill s-break">Breaks with party</span>':""}${i.unv?' <span class="pill s-unv">Unverified</span>':""} <a class="src" href="${esc(i.u)}"${i.u.startsWith("http")?' target="_blank" rel="noopener"':""}>Source</a></span></li>`).join("")}</ul>
      ${compact?`<a class="pp-more" href="stances.html#palestine">See all ${ITEMS.length} items on the Stances tab →</a>`:""}
      <p class="muted" style="margin:0;font-size:.8rem">This is a summary of his record, not a judgment. "Toward Palestinians / conditions on aid" covers votes and statements that limit military aid, protect Gaza aid access or oppose penalties for investigating Israel. It does not mean opposition to Israel.</p>`;
  }
  // The Stances page builds its boxes on window load; if the data arrives later, rebuild them and honor the #hash.
  function refresh(keys){
    if(document.readyState !== "complete") return;
    if(typeof window.boxes === "function") window.boxes();
    const k = location.hash.slice(1), dlg = document.getElementById("detail");
    if(keys.includes(k) && typeof window.openDetail === "function" && !(dlg && dlg.open)) window.openDetail("flag", k);
  }
  load.then(all => {
    const C = all.palestine; if(!C) return;
    window.TT = window.TT || {};
    window.TT.palestine = {q:C.q, v:C.v, sum:C.short, n:C.n, render:(el)=>render(C, el, false)};
    document.querySelectorAll("#palestineCard").forEach(el=>render(C, el, el.dataset.compact==="1"));
    refresh(["palestine"]);
  }).catch(e => console.error("palestine card:", e));
})();
