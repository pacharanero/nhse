(function () {
  "use strict";

  // "Kind" tags are the old fixed categories, kept as a known vocabulary so
  // every entry still gets a colour and a left/right side. Any other tag on
  // an entry is free-form and just used for filtering/search - see
  // spec/fdp-timeline.md for what each kind means.
  const KIND_LABELS = {
    scope: "Scope",
    contract: "Contract & procurement",
    official: "Official communication",
    media: "Media revelation",
    board: "Board meeting quote",
    legal: "Legal & parliamentary",
    civil: "Civil society",
  };

  // Left: what NHS England / government / the supplier did or said.
  // Right: how the outside world found out, reacted, or pushed back.
  const KIND_SIDE = {
    scope: "left",
    contract: "left",
    official: "left",
    board: "left",
    media: "right",
    legal: "right",
    civil: "right",
  };

  const timelineEl = document.getElementById("timeline");
  const filtersEl = document.getElementById("tag-filters");
  const searchEl = document.getElementById("search-box");
  const countEl = document.getElementById("result-count");
  const cardEl = document.getElementById("entry-card");
  const backdropEl = document.getElementById("card-backdrop");
  const sortBtns = Array.from(document.querySelectorAll(".sort-btn"));

  const entryCache = new Map(); // id -> parsed yaml
  const activeTags = new Set(); // empty = no filter; selecting tags ANDs them together
  let allOtherTags = []; // non-kind tags, discovered once the index loads
  let index = [];
  let pinned = false;
  let hoverTimer = null;
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
    if (tags) {
      tags.split(",").filter(Boolean).forEach((t) => activeTags.add(t));
    }
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
    const url = window.location.pathname + (qs ? `?${qs}` : "");
    window.history.replaceState(null, "", url);
  }

  function primaryKind(tags) {
    return tags.find((t) => KIND_LABELS[t]) || null;
  }

  function fmtDate(entry) {
    const [y] = entry.date.split("-");
    if (entry.date_precision === "day") {
      return new Date(entry.date + "T00:00:00").toLocaleDateString("en-GB", {
        year: "numeric", month: "short", day: "numeric",
      });
    }
    if (entry.date_precision === "month") {
      return new Date(entry.date + "T00:00:00").toLocaleDateString("en-GB", {
        year: "numeric", month: "long",
      });
    }
    return `Q? ${y}`; // quarter precision: refine once quarter data exists
  }

  function buildFilters() {
    filtersEl.innerHTML = "";

    Object.entries(KIND_LABELS).forEach(([key, label]) => {
      const btn = document.createElement("button");
      btn.className = "filter-btn" + (activeTags.has(key) ? " active" : "");
      btn.type = "button";
      btn.dataset.tag = key;
      btn.innerHTML = `<span class="swatch" style="background:var(--cat-${key})"></span>${label}`;
      btn.addEventListener("click", () => toggleTag(key, btn));
      filtersEl.appendChild(btn);
    });

    if (allOtherTags.length) {
      const sep = document.createElement("span");
      sep.className = "filter-sep";
      filtersEl.appendChild(sep);

      allOtherTags.forEach((tag) => {
        const btn = document.createElement("button");
        btn.className = "filter-btn plain" + (activeTags.has(tag) ? " active" : "");
        btn.type = "button";
        btn.dataset.tag = tag;
        btn.textContent = tag;
        btn.addEventListener("click", () => toggleTag(tag, btn));
        filtersEl.appendChild(btn);
      });
    }
  }

  function toggleTag(tag, btn) {
    if (activeTags.has(tag)) {
      activeTags.delete(tag);
      btn.classList.remove("active");
    } else {
      activeTags.add(tag);
      btn.classList.add("active");
    }
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

  function render() {
    const visible = sortedVisible();
    const todayStr = new Date().toISOString().slice(0, 10);

    timelineEl.innerHTML = "";
    let lastYear = null;
    let todayInserted = false;

    visible.forEach((entry) => {
      const crossedToday = sortOrder === "asc" ? entry.date > todayStr : entry.date < todayStr;
      if (!todayInserted && crossedToday) {
        const marker = document.createElement("li");
        marker.className = "timeline-today";
        marker.innerHTML = `<span class="label">Today - ${todayStr}</span>`;
        timelineEl.appendChild(marker);
        todayInserted = true;
      }

      const year = entry.date.slice(0, 4);
      if (year !== lastYear) {
        const marker = document.createElement("li");
        marker.className = "timeline-year";
        marker.innerHTML = `<span class="label">${year}</span>`;
        timelineEl.appendChild(marker);
        lastYear = year;
      }

      const kind = primaryKind(entry.tags);
      const side = kind ? (KIND_SIDE[kind] || "left") : "left";
      const li = document.createElement("li");
      li.className = `timeline-item side-${side}`;
      if (kind) li.style.setProperty("--dot-color", `var(--cat-${kind})`);

      const dateSpan = document.createElement("span");
      dateSpan.className = "entry-date";
      dateSpan.textContent = fmtDate(entry);

      const catSpan = document.createElement("span");
      catSpan.className = "entry-category";
      catSpan.textContent = kind ? KIND_LABELS[kind] : "Uncategorised";

      const extraTags = entry.tags.filter((t) => t !== kind && !KIND_LABELS[t]);
      let extraSpan = null;
      if (extraTags.length) {
        extraSpan = document.createElement("span");
        extraSpan.className = "entry-extra-tags";
        extraSpan.textContent = extraTags.join(", ");
      }

      const titleBtn = document.createElement("button");
      titleBtn.className = "entry-title";
      titleBtn.type = "button";
      titleBtn.textContent = entry.title;
      titleBtn.setAttribute("aria-expanded", "false");
      titleBtn.addEventListener("mouseenter", () => scheduleShow(entry, titleBtn));
      titleBtn.addEventListener("mouseleave", scheduleHide);
      titleBtn.addEventListener("focus", () => showCard(entry, titleBtn));
      titleBtn.addEventListener("click", () => {
        pinned = true;
        showCard(entry, titleBtn);
      });

      li.appendChild(dateSpan);
      li.appendChild(catSpan);
      if (extraSpan) li.appendChild(extraSpan);
      li.appendChild(titleBtn);
      timelineEl.appendChild(li);
    });

    if (!todayInserted) {
      const marker = document.createElement("li");
      marker.className = "timeline-today";
      marker.innerHTML = `<span class="label">Today - ${todayStr}</span>`;
      timelineEl.appendChild(marker);
    }

    countEl.textContent = `${visible.length} of ${index.length} entries`;
  }

  function scheduleShow(entry, anchor) {
    clearTimeout(hoverTimer);
    hoverTimer = setTimeout(() => showCard(entry, anchor), 120);
  }

  function scheduleHide() {
    if (pinned) return;
    clearTimeout(hoverTimer);
    hoverTimer = setTimeout(hideCard, 250);
  }

  async function loadEntry(id, file) {
    if (entryCache.has(id)) return entryCache.get(id);
    const res = await fetch(file);
    const text = await res.text();
    const data = jsyaml.load(text);
    entryCache.set(id, data);
    return data;
  }

  async function showCard(summaryEntry, anchor) {
    clearTimeout(hoverTimer);
    const data = await loadEntry(summaryEntry.id, summaryEntry.file);

    const related = (data.related || [])
      .map((id) => index.find((e) => e.id === id))
      .filter(Boolean);

    const kind = primaryKind(data.tags);
    const tagChips = data.tags.map((t) => `<span class="tag-chip">${escapeHtml(t)}</span>`).join("");

    cardEl.innerHTML = `
      <button class="close-btn" type="button" aria-label="Close">×</button>
      <h3>${escapeHtml(data.title)}</h3>
      <div class="meta">${fmtDate(summaryEntry)} · ${kind ? KIND_LABELS[kind] : "Uncategorised"}${data.paywalled ? " · paywalled source" : ""}</div>
      <div class="tags">${tagChips}</div>
      <p>${escapeHtml(data.summary)}</p>
      ${data.quote ? `<blockquote>${escapeHtml(data.quote)}<br><small>verification: ${escapeHtml(data.quote_verified || "unverified")}</small></blockquote>` : ""}
      ${data.contested ? `<div class="contested"><strong>Contested:</strong> ${escapeHtml(data.contested)}</div>` : ""}
      <div class="sources">
        <div class="source-line">
          <span class="source-title">${escapeHtml(data.source_title)}</span>
          <span class="source-links">
            <a href="${data.source_url}" target="_blank" rel="noopener" title="Live source (may have moved or changed)">web</a>
            <a href="${data.archive_url}" target="_blank" rel="noopener" title="Archived copy, as captured">wayback</a>
          </span>
        </div>
      </div>
      ${related.length ? `<div class="sources"><strong>Related:</strong> ${related.map((r) => escapeHtml(r.title)).join("; ")}</div>` : ""}
    `;

    cardEl.hidden = false;
    // The backdrop exists to let a click-pinned card be dismissed by
    // clicking outside it. It must stay hidden for a passive hover
    // preview: showing it would sit on top of the hovered title (z-index
    // 20 vs the title's implicit 0), which triggers a spurious mouseleave
    // on the title the instant the card appears, closing it again.
    backdropEl.hidden = !pinned;
    positionCard(anchor);
    anchor.setAttribute("aria-expanded", "true");

    cardEl.querySelector(".close-btn").addEventListener("click", () => {
      pinned = false;
      hideCard();
    });
  }

  function positionCard(anchor) {
    const rect = anchor.getBoundingClientRect();
    const cardWidth = cardEl.offsetWidth;
    let left = rect.left + window.scrollX;
    if (left + cardWidth > window.scrollX + window.innerWidth - 16) {
      left = window.scrollX + window.innerWidth - cardWidth - 16;
    }
    cardEl.style.left = `${Math.max(16, left)}px`;
    cardEl.style.top = `${rect.bottom + window.scrollY + 6}px`;
  }

  function hideCard() {
    cardEl.hidden = true;
    backdropEl.hidden = true;
    document.querySelectorAll('.entry-title[aria-expanded="true"]').forEach((b) => b.setAttribute("aria-expanded", "false"));
  }

  backdropEl.addEventListener("click", () => {
    pinned = false;
    hideCard();
  });

  cardEl.addEventListener("mouseenter", () => clearTimeout(hoverTimer));
  cardEl.addEventListener("mouseleave", scheduleHide);

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function setSortOrder(order) {
    sortOrder = order;
    sortBtns.forEach((b) => b.classList.toggle("active", b.dataset.sort === order));
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

    sortBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        setSortOrder(btn.dataset.sort);
        render();
        writeStateToURL();
      });
    });

    searchEl.addEventListener("input", () => {
      render();
      writeStateToURL();
    });

    render();

    // Pull summaries in for search once loaded, then re-render so search
    // covers summary text too.
    await Promise.all(
      index.map((entry) =>
        loadEntry(entry.id, entry.file).then((data) => {
          entry.summarySnippet = data.summary;
        })
      )
    );
    render();
  }

  init();
})();
