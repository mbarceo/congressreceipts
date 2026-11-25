// Congress Receipts: draws the shared header and footer on the hub pages, so the nav is written once.
// Each hub page sets <body data-page="home|find|attendance|leaders">. Member tracker pages load this script with
// data-base="../../" (added by scripts/publish.py): links then point back up to the hub, and the header scrolls away
// instead of sticking, because the tracker keeps its own sticky page tabs.
(() => {
  const base = (document.currentScript && document.currentScript.dataset.base) || "";
  const NAV = [["home", "index.html", "Home"], ["find", "find.html", "Find your rep"],
               ["attendance", "attendance.html", "Who's showing up"], ["leaders", "leaders.html", "Leaders tracker"]];
  const here = document.body.dataset.page;
  const head = document.createElement("header"); head.className = "cr-head" + (base ? " cr-static" : "");
  head.innerHTML = `<div class="in"><a class="cr-brand" href="${base}index.html" aria-label="Congress Receipts home">
      <img src="${base}assets/logo.svg" alt="" width="34" height="34"><b>Congress Receipts</b></a>
    <button class="cr-menu" aria-expanded="false" aria-controls="cr-nav">Menu</button>
    <nav class="cr-nav" id="cr-nav" aria-label="Main">${NAV.map(([k, h, l]) => `<a href="${base}${h}"${k === here ? ' aria-current="page"' : ""}>${l}</a>`).join("")}</nav></div>`;
  document.body.prepend(head);
  const btn = head.querySelector(".cr-menu");
  btn.addEventListener("click", () => { const o = head.classList.toggle("open"); btn.setAttribute("aria-expanded", o); btn.textContent = o ? "Close" : "Menu"; });
  const foot = document.querySelector("footer.cr-foot");
  if (foot && !foot.dataset.custom) foot.insertAdjacentHTML("beforeend",
    `<span>Congress Receipts is a nonpartisan project. Every claim links to its source; votes, tallies, quotes and dollar figures are checked against the official record.</span>
     <span><a href="index.html#how">How we check</a> · <a href="https://github.com/mbarceo/congressreceipts">Source code and data</a></span>`);
})();
