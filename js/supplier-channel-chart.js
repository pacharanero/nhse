// Stacked bar chart showing one tracked supplier's total spend per calendar
// year, broken down by paying channel (NHS England centrally, a regional
// Commissioning Support Unit, or NHS Digital/HSCIC pre-merger). Reads
// gpsoc-supplier-breakdown.json, built by `s/build-gpsoc-breakdown`. A
// dedicated renderer rather than an extension of js/bar-chart.js: that
// renderer's shape (one value per bar) does not fit stacked segments, and
// this view is deliberately scoped to the two suppliers investigated in
// spec/spending-data.md, not a generic multi-supplier tool.
window.NhseSupplierChannelChart = (function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const BAR_WIDTH = 34;
  const BAR_GAP = 10;
  const CHART_HEIGHT = 220;
  const LABEL_HEIGHT = 36;
  const VALUE_LABEL_HEIGHT = 18;
  const LEFT_PADDING = 8;
  const TOP_PADDING = 12;

  const CHANNEL_COLOR = {
    "NHS England": "var(--color-primary)",
    CSU: "var(--color-secondary)",
    "NHS Digital / HSCIC": "var(--color-accent)",
  };

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

  function niceAxisTop(maxValue) {
    if (!(maxValue > 0)) {
      return 1;
    }
    const exponent = Math.floor(Math.log10(maxValue));
    const magnitude = Math.pow(10, exponent);
    const normalized = maxValue / magnitude;
    let step;
    if (normalized <= 1) step = 1;
    else if (normalized <= 2) step = 2;
    else if (normalized <= 5) step = 5;
    else step = 10;
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

  function render(container, supplier, channels, options) {
    options = options || {};
    const idPrefix = options.idPrefix || "supplier-channel-chart";
    const years = supplier.years;

    const maxTotal = Math.max(...years.map((year) => Number(year.total_gbp)));
    const axisTop = niceAxisTop(maxTotal);
    const plotHeight = CHART_HEIGHT - TOP_PADDING;
    const width = LEFT_PADDING * 2 + years.length * (BAR_WIDTH + BAR_GAP) - BAR_GAP;
    const height = CHART_HEIGHT + LABEL_HEIGHT;
    const titleId = idPrefix + "-title";
    const descId = idPrefix + "-desc";

    const svg = el("svg", {
      viewBox: "0 0 " + width + " " + height,
      width: width,
      height: height,
      role: "img",
      "aria-labelledby": titleId + " " + descId,
      class: "spend-chart-svg",
    });
    svg.appendChild(el("title", { id: titleId }, supplier.label + " by paying channel, per calendar year"));
    svg.appendChild(
      el(
        "desc",
        { id: descId },
        "Stacked bar chart, " + formatMoney(axisTop) + " axis maximum, segments are " + channels.join(", ") + "."
      )
    );

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
      let cumulative = 0;
      const titleParts = [year.year + ": " + formatMoney(year.total_gbp) + " total"];
      channels.forEach((channel) => {
        const channelValue = Number(year.channels[channel] || "0");
        if (channelValue <= 0) {
          return;
        }
        titleParts.push(channel + ": " + formatMoney(channelValue));
        const segmentHeight = (channelValue / axisTop) * plotHeight;
        const y = TOP_PADDING + plotHeight - cumulative - segmentHeight;
        const rect = el("rect", {
          x: x,
          y: y,
          width: BAR_WIDTH,
          height: Math.max(0.5, segmentHeight),
          fill: CHANNEL_COLOR[channel] || "var(--color-neutral)",
        });
        svg.appendChild(rect);
        cumulative += segmentHeight;
      });

      const bar = el("rect", { x: x, y: TOP_PADDING, width: BAR_WIDTH, height: plotHeight, fill: "transparent" });
      bar.appendChild(el("title", {}, titleParts.join("; ")));
      svg.appendChild(bar);

      const totalParts = formatMoneyParts(year.total_gbp);
      const topY = TOP_PADDING + plotHeight - cumulative;
      svg.appendChild(
        el(
          "text",
          { x: x + BAR_WIDTH / 2, y: Math.max(TOP_PADDING + 10, topY - 6), "text-anchor": "middle", class: "spend-chart-value-label" },
          totalParts.number + totalParts.unit
        )
      );

      const labelGroup = el("g", {
        transform: "translate(" + (x + BAR_WIDTH / 2) + "," + (TOP_PADDING + plotHeight + VALUE_LABEL_HEIGHT) + ") rotate(-40)",
      });
      labelGroup.appendChild(el("text", { "text-anchor": "end", class: "spend-chart-axis-label" }, String(year.year)));
      svg.appendChild(labelGroup);
    });

    container.replaceChildren(svg);
  }

  function renderLegend(container, channels) {
    const list = document.createElement("ul");
    list.className = "flex flex-wrap gap-4 text-sm mt-2";
    channels.forEach((channel) => {
      const item = document.createElement("li");
      item.className = "flex items-center gap-2";
      const swatch = document.createElement("span");
      swatch.className = "inline-block w-3 h-3 rounded-sm";
      swatch.style.backgroundColor = CHANNEL_COLOR[channel] || "var(--color-neutral)";
      item.appendChild(swatch);
      item.appendChild(document.createTextNode(channel));
      list.appendChild(item);
    });
    container.replaceChildren(list);
  }

  function renderTable(container, supplier, channels) {
    const table = document.createElement("table");
    table.className = "table table-sm mt-4";
    const thead = document.createElement("thead");
    thead.innerHTML = "<tr><th>Year</th>" + channels.map((c) => "<th>" + c + " (£)</th>").join("") + "<th>Total (£)</th></tr>";
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    supplier.years.forEach((year) => {
      const row = document.createElement("tr");
      const cells = channels
        .map((channel) => "<td>" + Number(year.channels[channel] || "0").toLocaleString("en-GB", { maximumFractionDigits: 0 }) + "</td>")
        .join("");
      row.innerHTML =
        "<td>" + year.year + "</td>" + cells + "<td>" + Number(year.total_gbp).toLocaleString("en-GB", { maximumFractionDigits: 0 }) + "</td>";
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    container.replaceChildren(table);
  }

  return { render: render, renderLegend: renderLegend, renderTable: renderTable };
})();
