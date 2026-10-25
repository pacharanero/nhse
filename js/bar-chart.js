// Shared SVG bar-chart renderer used by the "Spend over time" chart
// (js/spend-chart.js) and the per-supplier chart in the "Search suppliers"
// tool (js/supplier-search.js). Items that do not cover a full calendar
// year (coverage !== "full_calendar_year") are drawn with a hatched fill
// and a dashed outline so an incomplete period can never be mistaken for
// a full one at a glance - see "never turn an absent month into zero
// spending" in spec/spending-data.md. Each chart instance needs its own
// idPrefix so more than one chart can exist on the page at once without
// colliding SVG ids (patterns, <title>/<desc> ids).
window.NhseBarChart = (function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const BAR_WIDTH = 40;
  const BAR_GAP = 14;
  const CHART_HEIGHT = 220;
  const LABEL_HEIGHT = 56;
  const VALUE_LABEL_HEIGHT = 20;
  const LEFT_PADDING = 8;
  const TOP_PADDING = 12;

  // Scale-aware formatting: a single supplier's totals are typically
  // thousands-to-millions, while the whole-page chart is billions: always
  // showing "bn" would round small suppliers to "£0.00bn" on every bar.
  function formatMoneyParts(totalGbpString) {
    const value = Number(totalGbpString);
    const abs = Math.abs(value);
    if (abs >= 1e9) return { number: (value / 1e9).toFixed(2), unit: "bn" };
    if (abs >= 1e6) return { number: (value / 1e6).toFixed(2), unit: "m" };
    if (abs >= 1e3) return { number: (value / 1e3).toFixed(1), unit: "k" };
    return { number: value.toFixed(0), unit: "" };
  }

  function formatMoney(totalGbpString) {
    const parts = formatMoneyParts(totalGbpString);
    return "£" + parts.number + parts.unit;
  }

  // A "nice" round axis ceiling (1/2/5 \u00d7 a power of ten) scaled to
  // whatever magnitude the data is in, so a small supplier's bars are not
  // scaled against the same 5bn-stepped axis as the whole-page chart.
  function niceAxisTop(maxValue) {
    if (!(maxValue > 0)) {
      return 1;
    }
    const exponent = Math.floor(Math.log10(maxValue));
    const magnitude = Math.pow(10, exponent);
    const normalized = maxValue / magnitude;
    let step;
    if (normalized <= 1) {
      step = 1;
    } else if (normalized <= 2) {
      step = 2;
    } else if (normalized <= 5) {
      step = 5;
    } else {
      step = 10;
    }
    return step * magnitude;
  }

  function el(tag, attrs, text) {
    const node = document.createElementNS(NS, tag);
    for (const key in attrs) {
      node.setAttribute(key, attrs[key]);
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function coverageDescription(item) {
    if (item.coverage === "fiscal_year") {
      return "fiscal year (April\u2013March), not directly comparable to calendar-year bars";
    }
    if (item.coverage === "partial_calendar_year") {
      return item.months_covered === 1
        ? "1 month published so far, not a full year"
        : item.months_covered + " of 12 months published; the rest are not yet published";
    }
    return "full calendar year";
  }

  function render(container, items, options) {
    options = options || {};
    const idPrefix = options.idPrefix || "bar-chart";
    const title = options.title || "NHS England detailed payments";
    const descSuffix =
      options.descSuffix ||
      "Hatched bars are partial or non-calendar-year periods; see the table below for exact figures.";

    const maxTotal = Math.max(...items.map((item) => Number(item.total_gbp)));
    const axisTop = niceAxisTop(maxTotal);
    const plotHeight = CHART_HEIGHT - TOP_PADDING;
    const width = LEFT_PADDING * 2 + items.length * (BAR_WIDTH + BAR_GAP) - BAR_GAP;
    const height = CHART_HEIGHT + LABEL_HEIGHT;
    const titleId = idPrefix + "-title";
    const descId = idPrefix + "-desc";
    const hatchId = idPrefix + "-hatch";

    const svg = el("svg", {
      viewBox: "0 0 " + width + " " + height,
      width: width,
      height: height,
      role: "img",
      "aria-labelledby": titleId + " " + descId,
      class: "spend-chart-svg",
    });
    svg.appendChild(el("title", { id: titleId }, title));
    svg.appendChild(
      el(
        "desc",
        { id: descId },
        "Bar chart of total published payments over £25,000, " + formatMoney(axisTop) + " axis maximum. " + descSuffix
      )
    );

    const defs = el("defs", {});
    const pattern = el("pattern", {
      id: hatchId,
      width: "6",
      height: "6",
      patternTransform: "rotate(45)",
      patternUnits: "userSpaceOnUse",
    });
    pattern.appendChild(el("rect", { width: "6", height: "6", fill: "var(--color-base-100)" }));
    pattern.appendChild(
      el("line", {
        x1: "0",
        y1: "0",
        x2: "0",
        y2: "6",
        stroke: "var(--color-base-content)",
        "stroke-width": "2",
        opacity: "0.45",
      })
    );
    defs.appendChild(pattern);
    svg.appendChild(defs);

    svg.appendChild(
      el("line", {
        x1: LEFT_PADDING,
        y1: TOP_PADDING,
        x2: LEFT_PADDING,
        y2: TOP_PADDING + plotHeight,
        stroke: "var(--color-base-300)",
        "stroke-width": "1",
      })
    );

    items.forEach((item, index) => {
      const x = LEFT_PADDING + index * (BAR_WIDTH + BAR_GAP);
      const totalGbp = Number(item.total_gbp);
      const barHeight = Math.max(2, (totalGbp / axisTop) * plotHeight);
      const y = TOP_PADDING + plotHeight - barHeight;
      const isFull = item.coverage === "full_calendar_year";

      const bar = el("rect", {
        x: x,
        y: y,
        width: BAR_WIDTH,
        height: barHeight,
        fill: isFull ? "var(--color-primary)" : "url(#" + hatchId + ")",
        stroke: isFull ? "none" : "var(--color-base-content)",
        "stroke-width": isFull ? "0" : "1",
        "stroke-dasharray": isFull ? "none" : "3 2",
        rx: "2",
      });
      bar.appendChild(
        el("title", {}, item.label + ": " + formatMoney(item.total_gbp) + " (" + coverageDescription(item) + ")")
      );
      svg.appendChild(bar);

      const valueParts = formatMoneyParts(item.total_gbp);
      svg.appendChild(
        el(
          "text",
          { x: x + BAR_WIDTH / 2, y: y - 6, "text-anchor": "middle", class: "spend-chart-value-label" },
          valueParts.number + valueParts.unit
        )
      );

      const labelGroup = el("g", {
        transform:
          "translate(" + (x + BAR_WIDTH / 2) + "," + (TOP_PADDING + plotHeight + VALUE_LABEL_HEIGHT) + ") rotate(-40)",
      });
      labelGroup.appendChild(el("text", { "text-anchor": "end", class: "spend-chart-axis-label" }, item.label));
      svg.appendChild(labelGroup);
    });

    container.replaceChildren(svg);
  }

  function renderTable(container, items) {
    const table = document.createElement("table");
    table.className = "table table-sm mt-4";
    const thead = document.createElement("thead");
    thead.innerHTML = "<tr><th>Period</th><th>Coverage</th><th>Rows</th><th>Total (£)</th></tr>";
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    items.forEach((item) => {
      const row = document.createElement("tr");
      const rowsCell = Number(item.rows).toLocaleString("en-GB");
      const totalCell = Number(item.total_gbp).toLocaleString("en-GB", {
        style: "currency",
        currency: "GBP",
        maximumFractionDigits: 0,
      });
      row.innerHTML =
        "<td>" +
        item.label +
        "</td><td>" +
        coverageDescription(item) +
        "</td><td>" +
        rowsCell +
        "</td><td>" +
        totalCell +
        "</td>";
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    container.replaceChildren(table);
  }

  return {
    render: render,
    renderTable: renderTable,
    formatMoney: formatMoney,
    coverageDescription: coverageDescription,
  };
})();
