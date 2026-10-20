// Renders the "Spend over time" bar chart on the spending page from
// spend-by-year.json. Partial-year and fiscal-year bars (anything that
// does not cover a full calendar year) are drawn with a hatched fill and
// a dashed outline so an incomplete period can never be mistaken for a
// full one at a glance - see "never turn an absent month into zero
// spending" in spec/spending-data.md.
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const BAR_WIDTH = 40;
  const BAR_GAP = 14;
  const CHART_HEIGHT = 220;
  const LABEL_HEIGHT = 56;
  const VALUE_LABEL_HEIGHT = 20;
  const LEFT_PADDING = 8;
  const TOP_PADDING = 12;

  function formatBn(totalGbpString) {
    const bn = Number(totalGbpString) / 1e9;
    return "£" + bn.toFixed(2) + "bn";
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

  function coverageDescription(year) {
    if (year.coverage === "fiscal_year") {
      return "fiscal year (April\u2013March), not directly comparable to calendar-year bars";
    }
    if (year.coverage === "partial_calendar_year") {
      return year.months_covered === 1
        ? "1 month published so far, not a full year"
        : year.months_covered + " of 12 months published; the rest are not yet published";
    }
    return "full calendar year";
  }

  function renderChart(container, years) {
    const maxTotal = Math.max(...years.map((year) => Number(year.total_gbp)));
    const axisTopBn = Math.ceil(maxTotal / 1e9 / 5) * 5;
    const axisTop = axisTopBn * 1e9;
    const plotHeight = CHART_HEIGHT - TOP_PADDING;
    const width = LEFT_PADDING * 2 + years.length * (BAR_WIDTH + BAR_GAP) - BAR_GAP;
    const height = CHART_HEIGHT + LABEL_HEIGHT;

    const svg = el("svg", {
      viewBox: "0 0 " + width + " " + height,
      width: width,
      height: height,
      role: "img",
      "aria-labelledby": "spend-chart-title spend-chart-desc",
      class: "spend-chart-svg",
    });
    svg.appendChild(el("title", { id: "spend-chart-title" }, "NHS England detailed payments by year"));
    svg.appendChild(
      el(
        "desc",
        { id: "spend-chart-desc" },
        "Bar chart of total published payments over £25,000 per year, " +
          axisTopBn +
          "bn axis maximum. Hatched bars are partial or non-calendar-year periods; see the table below for exact figures."
      )
    );

    const defs = el("defs", {});
    const pattern = el("pattern", {
      id: "spend-chart-hatch",
      width: "6",
      height: "6",
      patternTransform: "rotate(45)",
      patternUnits: "userSpaceOnUse",
    });
    pattern.appendChild(
      el("rect", { width: "6", height: "6", fill: "var(--color-base-100)" })
    );
    pattern.appendChild(
      el("line", { x1: "0", y1: "0", x2: "0", y2: "6", stroke: "var(--color-base-content)", "stroke-width": "2", opacity: "0.45" })
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

    years.forEach((year, index) => {
      const x = LEFT_PADDING + index * (BAR_WIDTH + BAR_GAP);
      const totalGbp = Number(year.total_gbp);
      const barHeight = Math.max(2, (totalGbp / axisTop) * plotHeight);
      const y = TOP_PADDING + plotHeight - barHeight;
      const isFull = year.coverage === "full_calendar_year";

      const bar = el("rect", {
        x: x,
        y: y,
        width: BAR_WIDTH,
        height: barHeight,
        fill: isFull ? "var(--color-primary)" : "url(#spend-chart-hatch)",
        stroke: isFull ? "none" : "var(--color-base-content)",
        "stroke-width": isFull ? "0" : "1",
        "stroke-dasharray": isFull ? "none" : "3 2",
        rx: "2",
      });
      bar.appendChild(el("title", {}, year.label + ": " + formatBn(year.total_gbp) + " (" + coverageDescription(year) + ")"));
      svg.appendChild(bar);

      svg.appendChild(
        el(
          "text",
          {
            x: x + BAR_WIDTH / 2,
            y: y - 6,
            "text-anchor": "middle",
            class: "spend-chart-value-label",
          },
          formatBn(year.total_gbp).replace("£", "").replace("bn", "")
        )
      );

      const labelGroup = el("g", {
        transform:
          "translate(" + (x + BAR_WIDTH / 2) + "," + (TOP_PADDING + plotHeight + VALUE_LABEL_HEIGHT) + ") rotate(-40)",
      });
      labelGroup.appendChild(el("text", { "text-anchor": "end", class: "spend-chart-axis-label" }, year.label));
      svg.appendChild(labelGroup);
    });

    container.replaceChildren(svg);
  }

  function renderTable(container, years) {
    const table = document.createElement("table");
    table.className = "table table-sm mt-4";
    const thead = document.createElement("thead");
    thead.innerHTML = "<tr><th>Period</th><th>Coverage</th><th>Rows</th><th>Total (£)</th></tr>";
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    years.forEach((year) => {
      const row = document.createElement("tr");
      const rowsCell = Number(year.rows).toLocaleString("en-GB");
      const totalCell = Number(year.total_gbp).toLocaleString("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 });
      row.innerHTML =
        "<td>" +
        year.label +
        "</td><td>" +
        coverageDescription(year) +
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

  function init() {
    const chartContainer = document.getElementById("spend-chart");
    const tableContainer = document.getElementById("spend-chart-table");
    if (!chartContainer) {
      return;
    }
    fetch("spend-by-year.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("spend-by-year.json: " + response.status);
        }
        return response.json();
      })
      .then((summary) => {
        renderChart(chartContainer, summary.years);
        if (tableContainer) {
          renderTable(tableContainer, summary.years);
        }
      })
      .catch((error) => {
        chartContainer.textContent = "Chart unavailable (" + error.message + "). See the data table below.";
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
