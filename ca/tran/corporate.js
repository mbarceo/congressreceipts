// "Is he pro-corporate?" evidence card. Renders into id="corpCard"; registers TT.corporate for the Stances boxes.
// Items come from data/cards.json (built by scripts/build_cards.py from data/card_picks.json); votes come from
// data/votes.json and PAC totals from data/fec/establishment_calc.json, so neither is typed by hand.
(function(){
  const load = window.__ttCards || (window.__ttCards = fetch("data/cards.json")
    .then(r => { if(!r.ok) throw new Error("data/cards.json " + r.status); return r.json(); })
    .then(d => Object.fromEntries(d.cards.map(c => [c.key, c]))));
  const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const fmt = d => /^\d{4}-\d{2}$/.test(d) ? `${MON[+d.slice(5)-1]} ${d.slice(0,4)}` : d.replace("-", "–");
  const esc = s => String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const TAG = {pro:"pp-isr", con:"pp-pal"};
  function render(CARD, el, compact){
    const n = k => CARD.items.filter(i=>i.s===k).length;
    const list = compact ? CARD.items.filter(i=>i.hi) : CARD.items;
    el.innerHTML = `<div class="pp-head"><div class="pp-flag"><span class="pp-q">${esc(CARD.q)}</span><span class="pp-v">${esc(CARD.v)}</span></div><p class="pp-sum">${esc(CARD.sum)}</p></div>
      <div class="pp-count"><span><i class="pp-dot pp-isr"></i>${n("pro")} ${esc(CARD.pro)}</span><span><i class="pp-dot pp-pal"></i>${n("con")} ${esc(CARD.con)}</span></div>
      <ul class="pp-list">${list.map(i=>`<li><span class="pp-date mono">${esc(fmt(i.d))}</span><span class="pp-tag ${TAG[i.s]}">${i.s==="pro"?esc(CARD.pro):esc(CARD.con)}</span><span class="pp-text">${esc(i.t)}${i.brk?' <span class="pill s-break">Breaks with party</span>':""}${i.unv?' <span class="pill s-unv">Unverified</span>':""} <a class="src" href="${esc(i.u)}"${i.u.startsWith("http")?' target="_blank" rel="noopener"':""}>Source</a></span></li>`).join("")}</ul>
      ${compact?`<a class="pp-more" href="stances.html#corporate">See all ${CARD.items.length} items on the Stances tab →</a>`:""}
      <p class="muted" style="margin:0;font-size:.8rem">PAC money comes from FEC filings, sorted into corporate, trade, labor and other by each committee's FEC organization type, with names used where the FEC gives none (and to catch unions the FEC files as corporations). A few committees may still be misclassified.</p>`;
  }
  // The Stances page builds its boxes on window load; if the data arrives later, rebuild them and honor the #hash.
  function refresh(keys){
    if(document.readyState !== "complete") return;
    if(typeof window.boxes === "function") window.boxes();
    const k = location.hash.slice(1), dlg = document.getElementById("detail");
    if(keys.includes(k) && typeof window.openDetail === "function" && !(dlg && dlg.open)) window.openDetail("flag", k);
  }
  load.then(all => {
    const CARD = all.corporate; if(!CARD) return;
    window.TT = window.TT || {};
    window.TT.corporate = {q:CARD.q, v:CARD.v, sum:CARD.short, n:CARD.n, render:(el, compact)=>render(CARD, el, !!compact)};
    document.querySelectorAll("#corpCard").forEach(el=>render(CARD, el, el.dataset.compact==="1"));
    refresh(["corporate"]);
  }).catch(e => console.error("corporate card:", e));
})();
