// Congress Receipts: draws the shared header and the site-wide footer on the hub pages and every tracker page, so the nav is written once.
// Each hub page sets <body data-page="home|find|attendance|leaders">. Member tracker pages load this script with
// data-base="../../" (added by scripts/publish.py): links then point back up to the hub, and the header scrolls away
// instead of sticking, because the tracker keeps its own sticky page tabs.
// Data files change with every rebuild: always revalidate them with the server (a cheap 304 when unchanged), so a returning
// visitor never mixes fresh pages with a stale cached data file.
(() => { const f = window.fetch.bind(window);
  window.fetch = (u, o) => f(u, typeof u === "string" && /(^|\/)data\/[^?#]*\.json/.test(u) ? Object.assign({cache: "no-cache"}, o) : o); })();
(() => {
  const base = (document.currentScript && document.currentScript.dataset.base) || "";
  const NAV = [["home", "index.html", "Home"], ["find", "find.html", "Find your rep"],
               ["attendance", "attendance.html", "Who's showing up"], ["leaders", "leaders.html", "Leaders tracker"], ["backlog", "backlog.html", "Backlog Queue"]];
  const here = document.body.dataset.page;
  if (!document.querySelector('link[rel~="icon"]')) { const ic = document.createElement("link"); ic.rel = "icon"; ic.type = "image/png"; ic.href = base + "assets/favicon.png"; document.head.appendChild(ic); }
  const head = document.createElement("header"); head.className = "cr-head" + (base ? " cr-static" : "");
  head.innerHTML = `<div class="in"><a class="cr-brand" href="${base}index.html" aria-label="Congress Receipts home">
      <img class="cr-logo" src="${base}assets/logo.png" alt="Congress Receipts" width="114" height="44"></a>
    <button class="cr-menu" aria-expanded="false" aria-controls="cr-nav">Menu</button>
    <nav class="cr-nav" id="cr-nav" aria-label="Main">${NAV.map(([k, h, l]) => `<a href="${base}${h}"${k === here ? ' aria-current="page"' : ""}>${l}</a>`).join("")}</nav></div>`;
  document.body.prepend(head);
  const btn = head.querySelector(".cr-menu");
  btn.addEventListener("click", () => { const o = head.classList.toggle("open"); btn.setAttribute("aria-expanded", o); btn.textContent = o ? "Close" : "Menu"; });
  // Site-wide footer, on hub pages and every tracker page (page-specific source notes stay in each page's own footer)
  const year = new Date().getFullYear();
  const sf = document.createElement("footer"); sf.className = "cr-site-foot";
  const links = NAV.concat([["about", "about.html", "About"]]).map(([k, h, l]) => `<a href="${base}${h}">${l}</a>`).join("") + `<a href="${base}index.html#how">How we check</a>`;
  sf.innerHTML = `<div class="in top"><a class="cr-brand" href="${base}index.html"><img class="cr-logo sm" src="${base}assets/logo.png" alt="Congress Receipts" width="88" height="34"></a>
    <nav aria-label="Footer">${links}</nav></div>
  <div class="in"><p class="src"><b>Sources</b> <a href="https://clerk.house.gov/Votes">House Clerk roll calls</a> <a href="https://www.senate.gov/legislative/votes_new.htm">Senate roll calls</a> <a href="https://www.fec.gov/data/">FEC filings</a> <a href="https://www.govinfo.gov/">govinfo bill records</a> <a href="https://www.census.gov/">Census Bureau</a></p>
  <p>An independent, nonpartisan project researched, built and maintained by one person. Not affiliated with any party, campaign, member of Congress or advocacy group, and not an endorsement of anyone. Every claim links to its source.</p>
  <p class="disclaimer"><b>Disclaimer:</b> Congress Receipts is built entirely from publicly available information: official government records (House and Senate roll-call votes, Federal Election Commission filings, congress.gov and govinfo bill records, Census data), members' own public statements, websites and archived campaign sites, and published news reports. It uses no private, leaked or purchased data. Summaries and verdicts are this project's reading of those public records, each with its stated rule; the linked source is always the official record. Information is provided as-is for public education and may lag the latest filings.</p>
  <p class="legal">© ${year} Congress Receipts · No ads. No tracking cookies. Donor names and addresses are never published.</p></div>`;
  (document.querySelector(".wrap") || document.body).insertAdjacentElement("afterend", sf);
})();
