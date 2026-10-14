(function () {
  "use strict";

  // Renders fdp/index.json as a filterable timeline using DaisyUI's
  // timeline, badge, and modal components. See spec/fdp-timeline.md for
  // what each kind tag means.

  const KIND_LABELS = {
    scope: "Scope",
    contract: "Contract & procurement",
    official: "Official communication",
    media: "Media revelation",
    board: "Board meeting quote",
    legal: "Legal & parliamentary",
    civil: "Civil society",
  };

  // Left (timeline-start): what NHS England / government / the supplier
  // did or said. Right (timeline-end): how the outside world found out,
  // reacted, or pushed back.
  const KIND_SIDE = {
    scope: "start",
    contract: "start",
    official: "start",
    board: "start",
    media: "end",
    legal: "end",
    civil: "end",
  };

  const KIND_COLOR = {
    scope: "secondary",
    contract: "error",
    official: "success",
    media: "warning",
    board: "info",
    legal: "primary",
    civil: "accent",
  };

  // Unused at runtime. Tailwind's build-time scanner only generates CSS
  // for class names that appear as complete literal text somewhere in a
  // scanned file - it cannot see the `btn-${color}` etc. template
  // literals below, which silently produce no rule at all (confirmed:
  // none of KIND_COLOR's colours rendered before this array existed).
  // Every class built that way is spelled out here so the build picks
  // it up. Keep in sync with KIND_COLOR's values. `neutral` is kept for
  // the hardcoded year/today markers even though no KIND_COLOR uses it
  // (its near-black value reads poorly as the text/border colour of an
  // outlined button against the dark theme's sidebar background).
  const TAILWIND_DYNAMIC_CLASS_SAFELIST = [
    "btn-primary", "btn-secondary", "btn-error", "btn-success", "btn-warning", "btn-info", "btn-neutral", "btn-accent",
    "btn-outline",
    "badge-primary", "badge-secondary", "badge-error", "badge-success", "badge-warning", "badge-info", "badge-neutral", "badge-accent",
    "bg-primary", "bg-secondary", "bg-error", "bg-success", "bg-warning", "bg-info", "bg-neutral", "bg-accent",
    "border-l-primary", "border-l-secondary", "border-l-error", "border-l-success", "border-l-warning", "border-l-info", "border-l-neutral", "border-l-accent",
  ];

  const timelineEl = document.getElementById("timeline");
  const filtersEl = document.getElementById("tag-filters");
  const freeTagsEl = document.getElementById("tag-filters-free");
  const tagsDetailsEl = document.getElementById("tags-details");
  const searchEl = document.getElementById("search-box");
  const countEl = document.getElementById("result-count");
  const modalEl = document.getElementById("entry-modal");
  const modalBodyEl = document.getElementById("entry-modal-body");
  const sortBtns = Array.from(document.querySelectorAll(".sort-btn"));

  const entryCache = new Map(); // id -> parsed yaml
  const activeTags = new Set(); // empty = no filter; selecting tags ANDs them together
  let allOtherTags = []; // non-kind tags, discovered once the index loads
  let index = [];
  let sortOrder = "desc"; // "desc" = newest first (default), "asc" = oldest first
  let currentEntryId = null; // id of the entry whose card is open, if any

  // Cumulative-appearance trackers - see fdp/bartlett-appearances.yaml,
  // fdp/watson-appearances.yaml, and "Appearance trackers" in
  // CONTRIBUTING.md. Lightweight dots on the timeline, not full entries:
  // no tags, no filtering, no modal - just a numbered link out to the
  // source. Add a new { key, prefix, file, toggleId } here (plus the
  // matching YAML, build script, and toggle button in fdp/index.html) to
  // track another frequent voice the same way.
  const TRACKERS = [
    { key: "bartlett", prefix: "TB", label: "Tom Bartlett", file: "bartlett-appearances.json", toggleId: "bartlett-toggle" },
    { key: "watson", prefix: "TW", label: "Tom Watson", file: "watson-appearances.json", toggleId: "watson-toggle" },
  ];
  TRACKERS.forEach((t) => {
    t.el = document.getElementById(t.toggleId);
    t.items = [];
    t.shown = true;
  });

  // --- URL querystring state -------------------------------------------
  // Convention, meant to generalise to any topic site in this repo:
  //   ?tags=a,b,c   comma-separated, ANDed together
  //   ?q=text       free-text search
  //   ?sort=asc     only written when non-default ("desc" is default and omitted)
  //   ?entry=id     opens that entry's card on load; present only while its modal is open
  // Read once on load; written back (via replaceState, so filtering doesn't
  // spam browser history) whenever filters/search/sort/open card change.

  function readStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    const tags = params.get("tags");
    if (tags) tags.split(",").filter(Boolean).forEach((t) => activeTags.add(t));
    const q = params.get("q");
    if (q) searchEl.value = q;
    const sort = params.get("sort");
    if (sort === "asc" || sort === "desc") sortOrder = sort;
    TRACKERS.forEach((t) => { if (params.get(t.key) === "0") t.shown = false; });
    return params.get("entry");
  }

  function writeStateToURL() {
    const params = new URLSearchParams();
    if (activeTags.size) params.set("tags", Array.from(activeTags).join(","));
    if (searchEl.value.trim()) params.set("q", searchEl.value.trim());
    if (sortOrder !== "desc") params.set("sort", sortOrder);
    TRACKERS.forEach((t) => { if (!t.shown) params.set(t.key, "0"); });
    if (currentEntryId) params.set("entry", currentEntryId);
    const qs = params.toString();
    window.history.replaceState(null, "", window.location.pathname + (qs ? `?${qs}` : ""));
  }

  function primaryKind(tags) {
    return tags.find((t) => KIND_LABELS[t]) || null;
  }

  function fmtDate(entry) {
    const [y] = entry.date.split("-");
    if (entry.date_precision === "day") {
      return new Date(entry.date + "T00:00:00").toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "numeric" });
    }
    if (entry.date_precision === "month") {
      return new Date(entry.date + "T00:00:00").toLocaleDateString("en-GB", { year: "numeric", month: "long" });
    }
    return `Q? ${y}`; // quarter precision: refine once quarter data exists
  }

  function buildFilters() {
    filtersEl.innerHTML = "";
    freeTagsEl.innerHTML = "";

    Object.entries(KIND_LABELS).forEach(([key, label]) => {
      const color = KIND_COLOR[key];
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `btn btn-sm btn-block justify-start gap-2 ${activeTags.has(key) ? `btn-${color}` : `btn-outline btn-${color}`}`;
      btn.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-${color}"></span>${escapeHtml(label)}`;
      btn.addEventListener("click", () => toggleTag(key));
      filtersEl.appendChild(btn);
    });

    allOtherTags.forEach((tag) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `badge badge-sm cursor-pointer ${activeTags.has(tag) ? "badge-primary" : "badge-outline"}`;
      btn.textContent = `#${tag}`;
      btn.addEventListener("click", () => toggleTag(tag));
      freeTagsEl.appendChild(btn);
    });

    if (tagsDetailsEl && Array.from(activeTags).some((t) => !KIND_LABELS[t])) {
      tagsDetailsEl.open = true;
    }
  }

  function toggleTag(tag) {
    if (activeTags.has(tag)) activeTags.delete(tag); else activeTags.add(tag);
    buildFilters();
    render();
    writeStateToURL();
  }

  function matchesTags(entry) {
    if (activeTags.size === 0) return true;
    return Array.from(activeTags).every((t) => entry.tags.includes(t));
  }

  function matchesSearch(entry, q) {
    if (!q) return true;
    const hay = (entry.title + " " + (entry.summarySnippet || "")).toLowerCase();
    return hay.includes(q);
  }

  function sortedVisible() {
    const q = searchEl.value.trim().toLowerCase();
    const visible = index.filter((e) => matchesTags(e) && matchesSearch(e, q));
    const dir = sortOrder === "asc" ? 1 : -1;
    visible.sort((a, b) => dir * (a.date < b.date ? -1 : a.date > b.date ? 1 : a.id < b.id ? -1 : 1));
    return visible;
  }

  function markerLi(label, badgeClass) {
    const li = document.createElement("li");
    li.innerHTML = `<hr><div class="timeline-middle"></div><div class="timeline-end badge ${badgeClass} badge-sm">${label}</div><hr>`;
    return li;
  }

  // The "today" marker is a thin rule across the content column, not a
  // badge - distinct from year markers above, since it marks a single
  // instant rather than a span.
  function todayMarkerLi(label) {
    const li = document.createElement("li");
    li.innerHTML = `
      <hr>
      <div class="timeline-start flex items-center">
        <span class="h-px flex-1 bg-error/40"></span>
      </div>
      <div class="timeline-middle">
        <span class="inline-block w-2 h-2 rounded-full bg-error"></span>
      </div>
      <div class="timeline-end flex items-center gap-2 text-error min-w-[14rem]">
        <span class="h-px flex-1 bg-error/40"></span>
        <span class="text-[10px] uppercase tracking-wider font-semibold whitespace-nowrap">${escapeHtml(label)}</span>
        <span class="h-px flex-1 bg-error/40"></span>
      </div>
      <hr>
    `;
    return li;
  }

  // `self: true` = a channel the subject fully controls (own blog, own
  // LinkedIn) - no gatekeeping involved. `self: false` = third-party
  // press/media coverage (a trade press column, a quote in a national
  // newspaper) - the kind of access that's harder to get from a standing
  // start without some help. Styled differently so the pattern is
  // visible at a glance, not just in the data.
  function trackerLi(appearance, prefix) {
    const li = document.createElement("li");
    const dotClass = appearance.self ? "bg-base-content/30" : "bg-secondary";
    const badgeClass = appearance.self
      ? "badge-ghost hover:badge-outline"
      : "badge-secondary badge-outline hover:badge-secondary";
    li.innerHTML = `
      <hr>
      <div class="timeline-middle">
        <span class="inline-block w-1.5 h-1.5 rounded-full ${dotClass}"></span>
      </div>
      <div class="timeline-end">
        <a class="badge badge-xs gap-1 ${badgeClass}" href="${appearance.url}" target="_blank" rel="noopener" title="${escapeHtml(appearance.outlet)}: ${escapeHtml(appearance.title)}">
          <span class="font-semibold">${prefix}#${appearance.n}</span>
          <span class="max-w-[16rem] truncate">${escapeHtml(appearance.outlet)}: ${escapeHtml(appearance.title)}</span>
        </a>
      </div>
      <hr>
    `;
    return li;
  }

  // Merges the main (filtered, sorted) entries with every enabled
  // tracker's appearance dots into one date-ordered sequence, so markers
  // interleave correctly regardless of sort order. Tracker items are
  // never filtered by tag/search - each toggle is the only way to hide
  // its dots.
  function mergedTimelineItems() {
    const entries = sortedVisible().map((e) => ({ kind: "entry", date: e.date, id: e.id, data: e }));
    const dots = [];
    TRACKERS.forEach((t) => {
      if (!t.shown) return;
      t.items.forEach((item) => dots.push({ kind: "tracker", prefix: t.prefix, date: item.date, id: `${t.key}-${item.n}`, data: item }));
    });
    const merged = entries.concat(dots);
    const dir = sortOrder === "asc" ? 1 : -1;
    merged.sort((a, b) => dir * (a.date < b.date ? -1 : a.date > b.date ? 1 : a.id < b.id ? -1 : 1));
    return merged;
  }

  function render() {
    const items = mergedTimelineItems();
    const todayStr = new Date().toISOString().slice(0, 10);
    timelineEl.innerHTML = "";
    let lastYear = null;
    let todayInserted = false;

    items.forEach((item) => {
      // In "desc" (newest-first) order, an item dated today must sit
      // below this marker, not above it alongside future-dated items -
      // hence `<=` here but strict `>` for "asc", where today-dated
      // items correctly stay above (i.e. earlier than) the marker.
      const crossedToday = sortOrder === "asc" ? item.date > todayStr : item.date <= todayStr;
      if (!todayInserted && crossedToday) {
        timelineEl.appendChild(todayMarkerLi(`Today — ${todayStr}`));
        todayInserted = true;
      }

      const year = item.date.slice(0, 4);
      if (year !== lastYear) {
        timelineEl.appendChild(markerLi(year, "badge-neutral"));
        lastYear = year;
      }

      if (item.kind === "tracker") {
        timelineEl.appendChild(trackerLi(item.data, item.prefix));
        return;
      }

      const entry = item.data;
      const kind = primaryKind(entry.tags);
      const side = kind ? KIND_SIDE[kind] : "end";
      const color = kind ? KIND_COLOR[kind] : "neutral";
      const extraTags = entry.tags.filter((t) => t !== kind && !KIND_LABELS[t]);

      const li = document.createElement("li");
      const content = `
        <div class="timeline-box bg-base-100 border border-base-300 border-l-4 border-l-${color} cursor-pointer hover:shadow-md transition-shadow" data-entry-id="${entry.id}">
          <div class="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
            <span class="text-xs text-base-content/60">${fmtDate(entry)}</span>
            <span class="badge badge-${color} badge-sm whitespace-nowrap">${kind ? KIND_LABELS[kind] : "Uncategorised"}</span>
          </div>
          <div class="font-semibold text-sm mt-1">${escapeHtml(entry.title)}</div>
          ${extraTags.length ? `<div class="text-xs text-base-content/50 mt-1">${extraTags.map((t) => `#${t}`).join(" ")}</div>` : ""}
        </div>
      `;

      li.innerHTML = `
        <hr>
        <div class="timeline-middle">
          <span class="inline-block w-3 h-3 rounded-full bg-${color}"></span>
        </div>
        <div class="timeline-${side}">${content}</div>
        <hr>
      `;
      timelineEl.appendChild(li);

      li.querySelector("[data-entry-id]").addEventListener("click", () => showEntry(entry));
    });

    if (!todayInserted) {
      timelineEl.appendChild(todayMarkerLi(`Today — ${todayStr}`));
    }

    const visibleCount = items.filter((i) => i.kind === "entry").length;
    const trackerCounts = TRACKERS
      .filter((t) => t.shown && t.items.length)
      .map((t) => `${t.items.length} ${t.label} appearances`);
    countEl.textContent = `${visibleCount} of ${index.length} entries`
      + (trackerCounts.length ? ` · ${trackerCounts.join(" · ")}` : "");
  }

  async function loadEntry(id, file) {
    if (entryCache.has(id)) return entryCache.get(id);
    const res = await fetch(file);
    const text = await res.text();
    const data = jsyaml.load(text);
    entryCache.set(id, data);
    return data;
  }

  async function showEntry(summaryEntry) {
    const data = await loadEntry(summaryEntry.id, summaryEntry.file);
    const kind = primaryKind(data.tags);
    const color = kind ? KIND_COLOR[kind] : "neutral";
    const related = (data.related || []).map((id) => index.find((e) => e.id === id)).filter(Boolean);
    const tagChips = data.tags.map((t) => `<span class="badge badge-sm badge-outline">#${escapeHtml(t)}</span>`).join(" ");

    modalBodyEl.innerHTML = `
      <h3 class="font-bold text-lg">${escapeHtml(data.title)}</h3>
      <div class="text-xs text-base-content/60 mt-1">
        ${fmtDate(summaryEntry)} ·
        <span class="badge badge-${color} badge-xs align-middle">${kind ? KIND_LABELS[kind] : "Uncategorised"}</span>
        ${data.paywalled ? " · paywalled source" : ""}
        · <a class="link" href="?entry=${encodeURIComponent(data.id)}" title="Direct link to this card">permalink</a>
      </div>
      <div class="flex flex-wrap gap-1 mt-2">${tagChips}</div>
      <p class="text-sm mt-3">${linkifySummary(data.summary)}</p>
      ${data.quote ? `<blockquote class="border-l-4 border-base-300 pl-3 italic text-sm mt-3">${escapeHtml(data.quote)}<br><small class="text-base-content/60">verification: ${escapeHtml(data.quote_verified || "unverified")}</small></blockquote>` : ""}
      ${data.contested ? `<div class="alert alert-warning alert-soft mt-3 text-sm"><span><strong>Contested:</strong> ${escapeHtml(data.contested)}</span></div>` : ""}
      <div class="text-sm mt-3">
        <span>${escapeHtml(data.source_title)}</span>
        <a class="link link-primary ml-2" href="${data.source_url}" target="_blank" rel="noopener">web</a>
        <a class="link link-primary ml-1" href="${data.archive_url}" target="_blank" rel="noopener">wayback</a>
      </div>
      ${related.length ? `<div class="text-sm mt-3"><strong>Related:</strong> ${related.map((r) => `<a class="link link-primary" href="?entry=${encodeURIComponent(r.id)}" data-related-id="${escapeHtml(r.id)}">${escapeHtml(r.title)}</a>`).join("; ")}</div>` : ""}
      <div class="modal-action">
        <form method="dialog"><button class="btn btn-sm">Close</button></form>
      </div>
    `;

    // Plain navigable links (middle-click/ctrl-click to open in a new tab
    // still works) that also resolve instantly in-page on a normal click,
    // rather than forcing a full reload to jump between related cards.
    modalBodyEl.querySelectorAll("[data-related-id]").forEach((a) => {
      a.addEventListener("click", (ev) => {
        if (ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
        const target = index.find((e) => e.id === a.dataset.relatedId);
        if (!target) return;
        ev.preventDefault();
        showEntry(target);
      });
    });

    currentEntryId = data.id;
    writeStateToURL();
    if (!modalEl.open) modalEl.showModal();
  }

  // Renders `summary`'s inline markdown links - see "Inline source links"
  // in CONTRIBUTING.md. Matches against the raw string (not pre-escaped)
  // so a URL containing '&' isn't corrupted by HTML-escaping before the
  // link regex sees it; each text/URL piece is escaped individually
  // instead. s/build-index already rejects non-http(s) URLs at commit
  // time, but this still only linkifies http(s) targets as a second line
  // of defence.
  function linkifySummary(summary) {
    const text = String(summary);
    const re = /\[([^\]]+)\]\((https?:\/\/[^)]*)\)/g;
    let result = "";
    let lastIndex = 0;
    let match;
    while ((match = re.exec(text)) !== null) {
      result += escapeHtml(text.slice(lastIndex, match.index));
      result += `<a class="link link-primary" href="${escapeHtml(match[2])}" target="_blank" rel="noopener">${escapeHtml(match[1])}</a>`;
      lastIndex = re.lastIndex;
    }
    result += escapeHtml(text.slice(lastIndex));
    return result;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function setSortOrder(order) {
    sortOrder = order;
    sortBtns.forEach((b) => b.classList.toggle("btn-active", b.dataset.sort === order));
  }

  function setTrackerToggle(t, shown) {
    t.shown = shown;
    if (t.el) {
      t.el.classList.toggle("btn-active", shown);
      t.el.setAttribute("aria-pressed", String(shown));
    }
  }

  async function init() {
    const requestedEntryId = readStateFromURL();

    const res = await fetch("index.json");
    index = await res.json();

    await Promise.all(TRACKERS.map(async (t) => {
      const r = await fetch(t.file);
      t.items = await r.json();
    }));

    const otherTags = new Set();
    index.forEach((e) => e.tags.forEach((t) => { if (!KIND_LABELS[t]) otherTags.add(t); }));
    allOtherTags = Array.from(otherTags).sort();

    buildFilters();
    setSortOrder(sortOrder);
    TRACKERS.forEach((t) => setTrackerToggle(t, t.shown));

    sortBtns.forEach((btn) => btn.addEventListener("click", () => { setSortOrder(btn.dataset.sort); render(); writeStateToURL(); }));
    searchEl.addEventListener("input", () => { render(); writeStateToURL(); });
    TRACKERS.forEach((t) => {
      if (t.el) t.el.addEventListener("click", () => { setTrackerToggle(t, !t.shown); render(); writeStateToURL(); });
    });
    modalEl.addEventListener("close", () => { currentEntryId = null; writeStateToURL(); });

    // Mobile sidebar toggle - desktop always shows the sidebar via
    // layout.css and hides this button, see "Mobile:" comment there.
    const sidebarToggleBtn = document.getElementById("sidebar-toggle");
    const sidebarEl = document.getElementById("fdp-sidebar");
    if (sidebarToggleBtn && sidebarEl) {
      sidebarToggleBtn.addEventListener("click", () => {
        const open = sidebarEl.classList.toggle("is-open");
        sidebarToggleBtn.setAttribute("aria-expanded", String(open));
      });
    }

    render();

    const requestedEntry = requestedEntryId && index.find((e) => e.id === requestedEntryId);
    if (requestedEntry) showEntry(requestedEntry);

    // Pull summaries in for search once loaded, then re-render so search
    // covers summary text too.
    await Promise.all(index.map((entry) => loadEntry(entry.id, entry.file).then((data) => { entry.summarySnippet = data.summary; })));
    render();
  }

  init();
})();
