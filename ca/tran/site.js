// Shared page chrome: sticky top bar with a "Jump to section" menu, and a floating back-to-top button.
(function(){
  const nav = document.querySelector(".sitenav");
  if(!nav) return;
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
})();
