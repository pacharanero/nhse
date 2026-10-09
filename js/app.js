(function () {
  "use strict";

  const CATEGORY_LABELS = {
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
  const CATEGORY_SIDE = {
    scope: "left",
    contract: "left",
    official: "left",
    board: "left",
    media: "right",
    legal: "right",
    civil: "right",
  };

  const timelineEl = document.getElementById("timeline");
  const filtersEl = document.getElementById("category-filters");
  const searchEl = document.getElementById("search-box");
  const countEl = document.getElementById("result-count");
  const cardEl = document.getElementById("entry-card");
  const backdropEl = document.getElementById("card-backdrop");

  const entryCache = new Map(); // id -> parsed yaml
  const activeCategories = new Set(Object.keys(CATEGORY_LABELS));
  let index = [];
  let pinned = false;
  let hoverTimer = null;

  function fmtDate(entry) {
    const [y, m, d] = entry.date.split("-");
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
    Object.entries(CATEGORY_LABELS).forEach(([key, label]) => {
      const btn = document.createElement("button");
      btn.className = "filter-btn active";
      btn.type = "button";
      btn.dataset.category = key;
      btn.innerHTML = `<span class="swatch" style="background:var(--cat-${key})"></span>${label}`;
      btn.addEventListener("click", () => {
        if (activeCategories.has(key)) {
          activeCategories.delete(key);
          btn.classList.remove("active");
        } else {
          activeCategories.add(key);
          btn.classList.add("active");
        }
        render();
      });
      filtersEl.appendChild(btn);
    });
  }

  function matchesSearch(entry, q) {
    if (!q) return true;
    const hay = (entry.title + " " + (entry.summarySnippet || "")).toLowerCase();
    return hay.includes(q);
  }

  function render() {
    const q = searchEl.value.trim().toLowerCase();
    const visible = index.filter(
      (e) => activeCategories.has(e.category) && matchesSearch(e, q)
    );
    timelineEl.innerHTML = "";
    let lastYear = null;
    visible.forEach((entry) => {
      const year = entry.date.slice(0, 4);
      if (year !== lastYear) {
        const marker = document.createElement("li");
        marker.className = "timeline-year";
        marker.innerHTML = `<span class="label">${year}</span>`;
        timelineEl.appendChild(marker);
        lastYear = year;
      }

      const side = CATEGORY_SIDE[entry.category] || "left";
      const li = document.createElement("li");
      li.className = `timeline-item side-${side}`;
      li.style.setProperty("--dot-color", `var(--cat-${entry.category})`);

      const dateSpan = document.createElement("span");
      dateSpan.className = "entry-date";
      dateSpan.textContent = fmtDate(entry);

      const catSpan = document.createElement("span");
      catSpan.className = "entry-category";
      catSpan.textContent = CATEGORY_LABELS[entry.category] || entry.category;

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
      li.appendChild(titleBtn);
      timelineEl.appendChild(li);
    });
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

    cardEl.innerHTML = `
      <button class="close-btn" type="button" aria-label="Close">×</button>
      <h3>${escapeHtml(data.title)}</h3>
      <div class="meta">${fmtDate(summaryEntry)} · ${CATEGORY_LABELS[data.category] || data.category}${data.paywalled ? " · paywalled source" : ""}</div>
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

  async function init() {
    buildFilters();
    const res = await fetch("fdp/index.json");
    index = await res.json();

    searchEl.addEventListener("input", render);
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
