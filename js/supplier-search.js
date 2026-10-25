// "Search suppliers" tool on the spending page. Matches raw published
// supplier text only - no entity resolution, no merging of abbreviations
// or trading names into one row. supplier-spend.json is ~1MB gzipped, so
// it is fetched lazily on first interaction rather than on page load,
// unless a ?q= URL parameter means a result should already be showing.
// The `q` URL parameter follows CONTRIBUTING.md's "URL querystring
// convention" so a search (and its top result) is a shareable link.
(function () {
  "use strict";

  const MIN_QUERY_LENGTH = 2;
  const MAX_RESULTS = 50;

  let summary = null;
  let loadPromise = null;

  function loadSummary(statusEl) {
    if (loadPromise) {
      return loadPromise;
    }
    if (statusEl) {
      statusEl.textContent = "Loading supplier data (about 1MB, cached after first load)…";
    }
    loadPromise = fetch("supplier-spend.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("supplier-spend.json: " + response.status);
        }
        return response.json();
      })
      .then((data) => {
        summary = data;
        summary.periodsByCode = {};
        summary.periods.forEach((period) => {
          summary.periodsByCode[period.period] = period;
        });
        if (statusEl) {
          statusEl.textContent = "";
        }
        return summary;
      })
      .catch((error) => {
        loadPromise = null;
        if (statusEl) {
          statusEl.textContent = "Supplier data unavailable (" + error.message + ").";
        }
        throw error;
      });
    return loadPromise;
  }

  function matchingSuppliers(query) {
    const needle = query.trim().toLowerCase();
    const matches = summary.suppliers.filter((supplier) => supplier.supplier.toLowerCase().includes(needle));
    matches.sort((a, b) => Number(b.total_gbp) - Number(a.total_gbp));
    return matches;
  }

  function renderResults(resultsEl, statusEl, query) {
    resultsEl.replaceChildren();
    const trimmed = query.trim();
    if (trimmed.length < MIN_QUERY_LENGTH) {
      statusEl.textContent =
        trimmed.length === 0 ? "" : "Type at least " + MIN_QUERY_LENGTH + " characters to search.";
      return;
    }
    const matches = matchingSuppliers(trimmed);
    if (matches.length === 0) {
      statusEl.textContent = 'No published supplier contains "' + trimmed + '".';
      return;
    }
    const shown = matches.slice(0, MAX_RESULTS);
    statusEl.textContent =
      matches.length > shown.length
        ? shown.length + " of " + matches.length + " matches shown, by total spend - refine your search for more."
        : matches.length + " match" + (matches.length === 1 ? "" : "es") + ", by total spend.";
    shown.forEach((supplier) => {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "w-full text-left flex justify-between gap-3";
      button.innerHTML =
        "<span>" +
        supplier.supplier.replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c])) +
        "</span><span class=\"text-base-content/60 whitespace-nowrap\">" +
        window.NhseBarChart.formatMoney(supplier.total_gbp) +
        "</span>";
      button.addEventListener("click", () => selectSupplier(supplier));
      li.appendChild(button);
      resultsEl.appendChild(li);
    });
  }

  function selectSupplier(supplier) {
    const detailEl = document.getElementById("supplier-search-detail");
    const chartEl = document.createElement("div");
    const tableWrapper = document.createElement("details");
    tableWrapper.className = "mt-2";
    const summaryEl = document.createElement("summary");
    summaryEl.className = "text-sm link cursor-pointer";
    summaryEl.textContent = "View exact figures as a table";
    const tableEl = document.createElement("div");
    tableWrapper.appendChild(summaryEl);
    tableWrapper.appendChild(tableEl);

    const heading = document.createElement("h3");
    heading.className = "font-semibold mt-6";
    heading.textContent = supplier.supplier;
    const caption = document.createElement("p");
    caption.className = "text-sm text-base-content/70 mt-1";
    caption.textContent =
      supplier.total_rows +
      " payments over £25,000, " +
      window.NhseBarChart.formatMoney(supplier.total_gbp) +
      " total, under this exact published supplier name, 2013/14-2025.";

    detailEl.replaceChildren(heading, caption, chartEl, tableWrapper);

    const items = supplier.years.map((year) => {
      const period = summary.periodsByCode[year.period] || {};
      return {
        label: period.label || year.period,
        coverage: period.coverage,
        months_covered: period.months_covered,
        rows: year.rows,
        total_gbp: year.total_gbp,
      };
    });
    window.NhseBarChart.render(chartEl, items, {
      idPrefix: "supplier-chart",
      title: supplier.supplier + ": NHS England detailed payments by year",
      descSuffix:
        "Hatched bars are partial or non-calendar-year periods for the whole NHS England publication, not specific to this supplier; see the table below for exact figures.",
    });
    window.NhseBarChart.renderTable(tableEl, items);
    detailEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function writeQueryToURL(query) {
    const params = new URLSearchParams(window.location.search);
    if (query.trim()) {
      params.set("q", query.trim());
    } else {
      params.delete("q");
    }
    const qs = params.toString();
    window.history.replaceState(null, "", window.location.pathname + (qs ? "?" + qs : ""));
  }

  function init() {
    const inputEl = document.getElementById("supplier-search-input");
    const resultsEl = document.getElementById("supplier-search-results");
    const statusEl = document.getElementById("supplier-search-status");
    if (!inputEl || !resultsEl || !statusEl) {
      return;
    }

    let debounceTimer = null;
    function handleInput(writeURL) {
      if (debounceTimer) {
        window.clearTimeout(debounceTimer);
      }
      debounceTimer = window.setTimeout(() => {
        const query = inputEl.value;
        if (writeURL) {
          writeQueryToURL(query);
        }
        if (query.trim().length < MIN_QUERY_LENGTH) {
          renderResults(resultsEl, statusEl, query);
          return;
        }
        loadSummary(statusEl)
          .then(() => renderResults(resultsEl, statusEl, query))
          .catch(() => {});
      }, 150);
    }

    inputEl.addEventListener("input", () => handleInput(true));
    inputEl.addEventListener("focus", () => loadSummary(statusEl).catch(() => {}), { once: true });

    const initialQuery = new URLSearchParams(window.location.search).get("q");
    if (initialQuery) {
      inputEl.value = initialQuery;
      loadSummary(statusEl).then(() => {
        renderResults(resultsEl, statusEl, initialQuery);
        const matches = matchingSuppliers(initialQuery.trim());
        if (matches.length > 0) {
          selectSupplier(matches[0]);
        }
      }).catch(() => {});
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
