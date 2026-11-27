// Shared runtime for every page. Load it in <head>, before the page's own scripts:
//   1. TRACKER: reads tracker.config.json once and exposes the member's display values.
//      Page scripts run inside `TRACKER.ready.then(M => ...)` and use M.short, M.subj, M.chamberName, ... (see build()).
//   2. Templating: once the DOM is parsed, every {{key}} in text, <title>, meta content and common attributes is
//      replaced from M; [data-only="house"|"senate"] elements are hidden in the other chamber; [data-if="key"] is
//      hidden when M[key] is empty; every img.portrait gets M.portrait and its alt text (hidden if the file is missing).
//   3. Page chrome: sticky top bar with a "Jump to section" menu, and a floating back-to-top button.
// Still works when included at the end of <body> (templating and chrome run; inline scripts above it can't use TRACKER).
// Data files change with every rebuild: always revalidate them with the server (a cheap 304 when unchanged), so a returning
// visitor never mixes fresh pages with a stale cached data file.
(() => { const f = window.fetch.bind(window);
  window.fetch = (u, o) => f(u, typeof u === "string" && /(^|\/)data\/[^?#]*\.json/.test(u) ? Object.assign({cache: "no-cache"}, o) : o); })();
(function(){
  const STATES = {AL:"Alabama",AK:"Alaska",AZ:"Arizona",AR:"Arkansas",CA:"California",CO:"Colorado",CT:"Connecticut",DE:"Delaware",FL:"Florida",GA:"Georgia",HI:"Hawaii",ID:"Idaho",IL:"Illinois",IN:"Indiana",IA:"Iowa",KS:"Kansas",KY:"Kentucky",LA:"Louisiana",ME:"Maine",MD:"Maryland",MA:"Massachusetts",MI:"Michigan",MN:"Minnesota",MS:"Mississippi",MO:"Missouri",MT:"Montana",NE:"Nebraska",NV:"Nevada",NH:"New Hampshire",NJ:"New Jersey",NM:"New Mexico",NY:"New York",NC:"North Carolina",ND:"North Dakota",OH:"Ohio",OK:"Oklahoma",OR:"Oregon",PA:"Pennsylvania",RI:"Rhode Island",SC:"South Carolina",SD:"South Dakota",TN:"Tennessee",TX:"Texas",UT:"Utah",VT:"Vermont",VA:"Virginia",WA:"Washington",WV:"West Virginia",WI:"Wisconsin",WY:"Wyoming",DC:"District of Columbia",PR:"Puerto Rico",GU:"Guam",VI:"U.S. Virgin Islands",AS:"American Samoa",MP:"Northern Mariana Islands"};
  const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const ord = n => { n = +n; const s = ["th","st","nd","rd"], v = n % 100; return n + (s[(v-20)%10] || s[v] || s[0]); };
  const poss = s => /s$/i.test(s) ? s + "'" : s + "'s";
  const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const host = u => String(u || "").replace(/^https?:\/\/(www\.)?/, "").replace(/\/.*$/, "");

  // Every display value a page may use. Explicit config fields win; the rest are derived with fallbacks,
  // so an older config (name/short/title/district only) still renders.
  // Delegates (AS, DC, GU, MP, VI) and Puerto Rico's Resident Commissioner sit in the House but cannot vote on the floor.
  // A tracker config can say so with member.nonVoting; otherwise it follows from the seat's state code.
  const NONVOTING = {AS: "Delegate", DC: "Delegate", GU: "Delegate", MP: "Delegate", VI: "Delegate", PR: "Resident Commissioner"};
  function build(cfg){
    const m = cfg.member || {}, L = cfg.leader || {}, P = cfg.profile || {};
    const senate = String(m.chamber || "house").toLowerCase() === "senate";
    const name = m.name || "This member", parts = name.trim().split(/\s+/);
    const first = m.first || parts[0], last = m.last || parts[parts.length-1], short = m.short || last;
    const honorific = m.honorific || (senate ? "Sen." : "Rep.");
    const title = m.title || `${honorific} ${name}`;
    const pr = m.pronouns || {};
    const subj = pr.subj || "they", obj = pr.obj || "them", ps = pr.poss || "their";
    const stateName = m.stateName || STATES[m.state] || m.state || "";
    const d = String(m.district ?? "").replace(/^0+(?=\d)/, "");
    const atLarge = !senate && (!d || d === "0" || /^AL$/i.test(d));
    const districtLabel = senate ? (m.state || stateName) : (m.districtLabel || `${m.state}-${atLarge ? "AL" : d}`);
    const seatLabel = m.seatLabel || (senate ? stateName : atLarge ? `${stateName}'s at-large district` : `${stateName}'s ${ord(d)} District`);
    const site = (m.site || "").replace(/\/$/, ""), domain = m.domain || host(site);
    const isRep = /^r/i.test(m.party || "");   // Republican members: own-party wording and the Allegiance page replace the Democratic defaults
    const leaderName = L.name || (isRep ? (senate ? "John Thune" : "Mike Johnson") : senate ? "Chuck Schumer" : "Hakeem Jeffries");
    const leaderLast = leaderName.split(/\s+/).pop();
    const since = /^\d{4}-\d{2}/.test(m.inOfficeSince || "") ? `${MON[+m.inOfficeSince.slice(5,7)-1]} ${m.inOfficeSince.slice(0,4)}` : (m.inOfficeSince || "");
    const congress = +(m.congress || 119);
    const nvRole = !senate && (m.nonVotingRole || NONVOTING[m.state] || (m.nonVoting ? "Delegate" : "")), nonVoting = m.nonVoting === false ? "" : nvRole;
    const chamberName = senate ? "Senate" : "House";
    return {
      cfg, profile: P, chamber: senate ? "senate" : "house", senate, house: !senate,
      name, first, last, short, honorific, title, shortPoss: poss(short), namePoss: poss(name),
      subj, obj, poss: ps, Subj: cap(subj), Obj: cap(obj), Poss: cap(ps),
      status: cfg.status || null,
      party: m.party || "", isRep, partyLetter: isRep ? "R" : "D", ownParty: isRep ? "Republican" : "Democratic", ownPartyNoun: isRep ? "Republican" : "Democrat",
      ownPartyPl: isRep ? "Republicans" : "Democrats", ownCaucus: isRep ? "Republican conference" : "Democratic caucus",
      otherPartyPl: isRep ? "Democrats" : "Republicans", ownPartyShort: isRep ? "GOP" : "Dems",
      state: m.state || "", stateName, district: d, districtLabel, seatLabel,
      seatShort: senate ? stateName : districtLabel,
      siteName: senate ? `${short} Senate Tracker` : `${districtLabel} ${short} Tracker`,
      seatNoun: senate ? "state" : "district",
      area: m.area || (senate ? stateName : districtLabel),
      chamberName, chamberLong: `U.S. ${chamberName}`, memberNoun: senate ? "senator" : "representative",
      officeNoun: `${chamberName} office`,
      portrait: m.portrait || "assets/portrait.jpg", portraitAlt: `Official ${chamberName} portrait of ${title}`,
      site, domain, pressUrl: site + (m.pressPath || ""), campaignSite: m.campaignSite || "", campaignDomain: host(m.campaignSite),
      voteId: m.voteId || m.bioguide || "", bioguide: m.bioguide || "",
      voteSource: senate ? "Senate" : "House Clerk",
      voteSourceLong: senate ? "the Senate's official roll-call votes (senate.gov)" : "the House Clerk's official roll-call records",
      voteSourceUrl: senate ? "https://www.senate.gov/legislative/votes_new.htm" : "https://clerk.house.gov/Votes",
      voteXml: senate ? "senate.gov/legislative/LIS/roll_call_votes" : "clerk.house.gov/evs",
      leaderNA: L.compareVotes === false, leaderName, leaderLast, leaderPoss: poss(leaderLast), leaderTitle: L.title || `${chamberName} ${isRep ? "Republican" : "Democratic"} leader`,
      congress, congressOrd: ord(congress), since, inOfficeSince: m.inOfficeSince || "",
      committees: m.committees || [],
      nonVoting, nonVotingRole: nonVoting,
      nonVotingNote: nonVoting ? `${short} is a non-voting ${nonVoting} in the U.S. House. ${nonVoting === "Delegate" ? "Delegates" : "The Resident Commissioner"} can introduce bills, serve on committees and speak in debate, but cannot vote on the House floor, so vote-based figures on this tracker may be limited or missing.` : "",
    };
  }

  const fill = (s, M) => String(s).replace(/\{\{\s*(\w+)\s*\}\}/g, (all, k) => (M && M[k] != null && typeof M[k] !== "object") ? M[k] : all);
  // Tiny safe markup for profile text in tracker.config.json: [label](https://url), **bold**, {{tokens}}.
  const md = (s, M) => esc(fill(s || "", M))
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|[\w./#-]+)\)/g, (a, t, u) => `<a href="${u}"${/^https?:/.test(u) ? ' target="_blank" rel="noopener"' : ""}>${t}</a>`)
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  const pending = (title, body) => `<div class="pending"><b>${esc(title)}</b>${body || ""}</div>`;

  const ATTRS = ["alt","title","aria-label","placeholder","content","href","src"];
  function apply(M){
    const root = document.documentElement;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: n =>
      n.nodeValue.includes("{{") && !/^(SCRIPT|STYLE)$/.test(n.parentNode.nodeName) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT});
    const nodes = []; while(w.nextNode()) nodes.push(w.currentNode);
    nodes.forEach(n => n.nodeValue = fill(n.nodeValue, M));
    root.querySelectorAll("*").forEach(el => ATTRS.forEach(a => { const v = el.getAttribute(a); if(v && v.includes("{{")) el.setAttribute(a, fill(v, M)); }));
    document.title = fill(document.title, M);
    root.querySelectorAll("[data-only]").forEach(el => { if(el.dataset.only !== M.chamber) el.hidden = true; });
    root.querySelectorAll("[data-party]").forEach(el => { if(el.dataset.party !== M.partyLetter) el.hidden = true; });
    root.querySelectorAll("[data-if]").forEach(el => { const v = M[el.dataset.if]; if(!v || (Array.isArray(v) && !v.length)) el.hidden = true; });
    root.querySelectorAll("img.portrait").forEach(img => {
      img.addEventListener("error", () => { img.hidden = true; }, {once: true});
      img.alt = M.portraitAlt;
      if(img.getAttribute("src") !== M.portrait) img.src = M.portrait;
    });
  }


  // ---- Trump section, shared by every tracker (Allegiance for Republicans, Establishment for Democrats) ----
  // Mount: <div id="trumpMount"></div>. Data: data/trump.json, built by scripts/build_trump.py from one selection rule.
  function renderTrump(M, d){
    const mount = document.getElementById("trumpMount"); if(!mount || !d) return;
    const link = (t, u) => u ? `<a class="src" href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}</a>` : "";
    const vp = v => `<span class="pill ${v==="Yea"?"v-yea":v==="Nay"?"v-nay":"v-other"}">${esc(v)}</span>`;
    const n = d.nums, own = d.ownParty;
    const row = r => `<tr><td class="mono" style="white-space:nowrap;font-size:.78rem">${esc(r.date)}</td><td><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.bill)}</a> · ${esc(r.title)}<div class="qq">${esc(r.q)}</div><div class="qq">“${esc(r.quote)}${r.truncated?"…":""}”</div> ${link(r.statement||"White House statement", r.statementUrl)}</td><td>${vp(r.trump)}</td><td>${vp(r.vote)}${r.status==="against"?' <span class="pill s-break">Against</span>':""}<div class="qq">${esc(own)} against Trump: ${r.ownAgainst} of ${r.ownTotal}</div></td><td class="qq">${esc(r.result)} ${r.yea}–${r.nay}</td></tr>`;
    const head = `<thead><tr><th>Date</th><th>Bill, question and source</th><th>Trump</th><th>${esc(M.short)}</th><th>Result</th></tr></thead>`;
    const notable = d.rows.filter(r => r.status !== "with" || r.ownAgainst >= 3), routine = d.rows.filter(r => !(r.status !== "with" || r.ownAgainst >= 3));
    const tile = (a, b) => `<div class="tile"><span class="n" style="font-size:1.5rem">${esc(a)}</span><span class="l">${esc(b)}</span></div>`;
    mount.innerHTML = `<section id="trump"><div class="sec-head"><span class="eyebrow">President Trump</span><h2>Votes where the White House stated a position</h2>
      <p class="axis-note">${esc(d.rule)}</p></div>
      <div class="tally">${tile(n.trumpPct != null ? n.trumpPct + "%" : "—", `of ${n.trumpN} counted votes cast with the White House position`)}${tile(n.trumpAgainst, "votes against it")}${tile(n.trumpMissed, "missed")}</div>
      <p class="axis-note"><b>Verdict:</b> ${esc(verdict(d.headline))}. ${esc(d.why)}</p>
      <div class="handles"><table class="brk-t">${head}<tbody>${notable.map(row).join("") || '<tr><td colspan="5" class="muted">No counted vote where the member, or 3 or more of the member\'s party, went against the White House position.</td></tr>'}</tbody></table></div>
      ${routine.length ? `<details><summary>${routine.length} more counted votes where almost everyone in ${esc(M.short)}'s party sided the same way</summary><div class="handles"><table class="brk-t">${head}<tbody>${routine.map(row).join("")}</tbody></table></div></details>` : ""}
      <details><summary>${d.skipped.length} votes examined but not counted, and why</summary><p class="axis-note">${d.examined} final votes had a White House statement; ${d.counted} are counted. These were left out, for the reason shown:</p>
        <div class="handles"><table class="brk-t"><thead><tr><th>Roll</th><th>Measure</th><th>Why it is not counted</th></tr></thead><tbody>${d.skipped.map(s => `<tr><td class="mono" style="font-size:.78rem">${esc(s.roll)}</td><td>${esc(s.bill)} · ${esc(s.title)}</td><td class="qq">${esc(s.reason)} ${link("Statement", s.url)}</td></tr>`).join("")}</tbody></table></div></details>
      <p class="axis-note">Trump's column is the vote his side wanted (Yea or Nay), from the linked statement. Only final votes are counted, not amendments, procedural motions or rules. Most counted votes are routine bills that nearly everyone in either party's majority supports or opposes together.</p></section>`;
  }

  const root = document.documentElement;
  const domReady = new Promise(r => document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", r, {once: true}) : r());
  root.classList.add("tk-wait");   // hide raw {{tokens}} until they are filled (at most 2.5 s)
  const hideCss = document.createElement("style");
  hideCss.textContent = ".tk-wait body{visibility:hidden}";
  (document.head || root).appendChild(hideCss);
  const reveal = () => root.classList.remove("tk-wait");
  setTimeout(reveal, 2500);

  const cfgP = fetch("tracker.config.json", {cache: "no-cache"}).then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const ready = Promise.all([cfgP, domReady]).then(([cfg]) => {
    const M = build(cfg || {});
    try { apply(M); } catch(e) { console.error(e); }
    // Trackers that are published before they are finished carry "status" in tracker.config.json: {label, note}. Remove it when done.
    if(M.status && M.status.note){
      const b = document.createElement("div"); b.className = "inprogress"; b.setAttribute("role", "note");
      b.innerHTML = "<b>" + esc(M.status.label || "In progress") + ".</b> " + esc(fill(M.status.note, M));
      const w = document.querySelector(".wrap"); if(w) w.insertBefore(b, w.firstChild);
    }
    window.TRACKER.M = M; reveal();
    return M;
  });
  window.TRACKER = {ready, M: null, fill, md, esc, pending, ord, poss, renderTrump};

  domReady.then(chrome);
  function chrome(){
    const nav = document.querySelector(".sitenav");
    if(!nav) return;
    // One nav for every page: edit this list to add or rename a page.
    const PAGES = [["./","Overview"],["money.html","Money"],["establishment.html","Establishment"],["townhalls.html","Town halls"],["stances.html","Stances"],["votes.html","Every vote"],["statements.html","Statements"],["sources.html","Sources"]];
    if(!nav.children.length){
      const here = location.pathname.split("/").pop() || "index.html";
      nav.innerHTML = PAGES.map(([h,t]) => {
        const file = h === "./" ? "index.html" : h;
        return `<a href="${h}"${file === here ? ' aria-current="page"' : ""}>${t}</a>`;
      }).join("");
    }
    // Republican members have an Allegiance page (Trump, MAGA, Project 2025, party leadership) in place of Establishment.
    ready.then(M => { if(M.isRep) nav.querySelectorAll('a[href="establishment.html"]').forEach(a => { a.href = "allegiance.html"; a.textContent = "Allegiance"; if(/allegiance\.html$/.test(location.pathname)) a.setAttribute("aria-current", "page"); }); });
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const go = el => el.scrollIntoView({behavior: reduce ? "auto" : "smooth", block: "start"});

    // Wrap the nav in a sticky bar and add the section menu beside it
    const bar = document.createElement("div");
    bar.className = "topbar";
    nav.parentNode.insertBefore(bar, nav);
    bar.appendChild(nav);
    const menu = document.createElement("details");
    menu.className = "jump";
    menu.innerHTML = '<summary>Jump to section</summary><div class="jump-list" role="list"></div>';
    bar.appendChild(menu);
    const list = menu.querySelector(".jump-list");

    const slug = t => t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "section";
    function build(){
      const secs = [...document.querySelectorAll("section")].filter(s => s.offsetParent !== null && s.querySelector("h2"));
      list.innerHTML = "";
      secs.forEach(s => {
        if(!s.id) s.id = "s-" + slug(s.querySelector("h2").textContent);
        const b = document.createElement("button");
        b.type = "button"; b.setAttribute("role", "listitem");
        const eb = s.querySelector(".sec-head .eyebrow");
        b.innerHTML = (eb ? '<span class="jl-e"></span>' : "") + '<span class="jl-t"></span>';
        if(eb) b.querySelector(".jl-e").textContent = eb.textContent;
        b.querySelector(".jl-t").textContent = s.querySelector("h2").textContent;
        b.addEventListener("click", () => { menu.open = false; go(s); });
        list.appendChild(b);
      });
      menu.hidden = secs.length < 2;
    }
    document.addEventListener("click", e => { if(menu.open && !menu.contains(e.target)) menu.open = false; });
    document.addEventListener("keydown", e => { if(e.key === "Escape") menu.open = false; });
    addEventListener("hashchange", () => setTimeout(build, 0));
    ready.then(() => setTimeout(build, 0));   // section titles after {{tokens}} are filled
    build();
    setTimeout(build, 1500); // sections that render after data loads

    // Back-to-top button
    const top = document.createElement("button");
    top.type = "button"; top.className = "totop"; top.hidden = true;
    top.setAttribute("aria-label", "Back to top");
    top.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M12 5l-7 7m7-7l7 7M12 5v14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Top</span>';
    top.addEventListener("click", () => scrollTo({top: 0, behavior: reduce ? "auto" : "smooth"}));
    document.body.appendChild(top);
    const onScroll = () => { top.hidden = scrollY < 500; bar.classList.toggle("stuck", scrollY > 20); };
    addEventListener("scroll", onScroll, {passive: true});
    onScroll();
  }
})();

// A verdict that hasn't been decided yet is stored as "TBD"; visitors see "Coming soon" instead.
window.verdict = h => (!h || h === "TBD") ? "Coming soon" : h;
