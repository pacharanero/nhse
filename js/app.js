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
    legal: "neutral",
    civil: "accent",
  };

  const timelineEl = document.getElementById("timeline");
  const filtersEl = document.getElementById("tag-filters");
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

  // --- URL querystring state -------------------------------------------
  // Convention, meant to generalise to any topic site in this repo:
  //   ?tags=a,b,c   comma-separated, ANDed together
  //   ?q=text       free-text search
  //   ?sort=asc     only written when non-default ("desc" is default and omitted)
  // Read once on load; written back (via replaceState, so filtering doesn't
  // spam browser history) whenever filters/search/sort change.

  function readStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    const tags = params.get("tags");
    if (tags) tags.split(",").filter(Boolean).forEach((t) => activeTags.add(t));
    const q = params.get("q");
    if (q) searchEl.value = q;
    const sort = params.get("sort");
    if (sort === "asc" || sort === "desc") sortOrder = sort;
  }

  function writeStateToURL() {
    const params = new URLSearchParams();
    if (activeTags.size) params.set("tags", Array.from(activeTags).join(","));
    if (searchEl.value.trim()) params.set("q", searchEl.value.trim());
    if (sortOrder !== "desc") params.set("sort", sortOrder);
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

    Object.entries(KIND_LABELS).forEach(([key, label]) => {
      const color = KIND_COLOR[key];
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `btn btn-xs ${activeTags.has(key) ? `btn-${color}` : `btn-outline btn-${color}`}`;
      btn.textContent = label;
      btn.addEventListener("click", () => toggleTag(key));
      filtersEl.appendChild(btn);
    });

    if (allOtherTags.length) {
      const sep = document.createElement("span");
      sep.className = "divider divider-horizontal mx-0";
      filtersEl.appendChild(sep);

      allOtherTags.forEach((tag) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `badge badge-sm cursor-pointer ${activeTags.has(tag) ? "badge-primary" : "badge-outline"}`;
        btn.textContent = `#${tag}`;
        btn.addEventListener("click", () => toggleTag(tag));
        filtersEl.appendChild(btn);
      });
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

  function render() {
    const visible = sortedVisible();
    const todayStr = new Date().toISOString().slice(0, 10);
    timelineEl.innerHTML = "";
    let lastYear = null;
    let todayInserted = false;

    visible.forEach((entry) => {
      const crossedToday = sortOrder === "asc" ? entry.date > todayStr : entry.date < todayStr;
      if (!todayInserted && crossedToday) {
        timelineEl.appendChild(markerLi(`Today — ${todayStr}`, "badge-error"));
        todayInserted = true;
      }

      const year = entry.date.slice(0, 4);
      if (year !== lastYear) {
        timelineEl.appendChild(markerLi(year, "badge-neutral"));
        lastYear = year;
      }

      const kind = primaryKind(entry.tags);
      const side = kind ? KIND_SIDE[kind] : "end";
      const color = kind ? KIND_COLOR[kind] : "neutral";
      const extraTags = entry.tags.filter((t) => t !== kind && !KIND_LABELS[t]);

      const li = document.createElement("li");
      const content = `
        <div class="timeline-box bg-base-100 border border-base-300 cursor-pointer hover:border-${color}" data-entry-id="${entry.id}">
          <div class="text-xs text-base-content/60">${fmtDate(entry)}</div>
          <div class="badge badge-${color} badge-xs mt-1">${kind ? KIND_LABELS[kind] : "Uncategorised"}</div>
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
      timelineEl.appendChild(markerLi(`Today — ${todayStr}`, "badge-error"));
    }

    countEl.textContent = `${visible.length} of ${index.length} entries`;
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
      ${related.length ? `<div class="text-sm mt-3"><strong>Related:</strong> ${related.map((r) => escapeHtml(r.title)).join("; ")}</div>` : ""}
      <div class="modal-action">
        <form method="dialog"><button class="btn btn-sm">Close</button></form>
      </div>
    `;
    modalEl.showModal();
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

  async function init() {
    readStateFromURL();

    const res = await fetch("index.json");
    index = await res.json();

    const otherTags = new Set();
    index.forEach((e) => e.tags.forEach((t) => { if (!KIND_LABELS[t]) otherTags.add(t); }));
    allOtherTags = Array.from(otherTags).sort();

    buildFilters();
    setSortOrder(sortOrder);

    sortBtns.forEach((btn) => btn.addEventListener("click", () => { setSortOrder(btn.dataset.sort); render(); writeStateToURL(); }));
    searchEl.addEventListener("input", () => { render(); writeStateToURL(); });

    render();

    // Pull summaries in for search once loaded, then re-render so search
    // covers summary text too.
    await Promise.all(index.map((entry) => loadEntry(entry.id, entry.file).then((data) => { entry.summarySnippet = data.summary; })));
    render();
  }

  init();
})();
