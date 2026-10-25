// Renders the "NHS Digital / HSCIC spend (pre-merger)" bar chart on the
// spending page from nhsd-spend-by-year.json, using the shared renderer in
// js/bar-chart.js. This is a deliberately separate chart instance (own
// idPrefix, own containers, own fetch) from js/spend-chart.js: NHS Digital
// was a legally distinct body from NHS England until their 1 February 2023
// merger, so its totals are never summed into the NHS England chart.
(function () {
  "use strict";

  function init() {
    const chartContainer = document.getElementById("nhsd-spend-chart");
    const tableContainer = document.getElementById("nhsd-spend-chart-table");
    if (!chartContainer) {
      return;
    }
    fetch("nhsd-spend-by-year.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("nhsd-spend-by-year.json: " + response.status);
        }
        return response.json();
      })
      .then((summary) => {
        window.NhseBarChart.render(chartContainer, summary.years, {
          idPrefix: "nhsd-spend-chart",
          title: "NHS Digital / HSCIC payments by fiscal year, pre-merger",
          descSuffix: "All bars are fiscal years (April\u2013March), shown hatched since none is a full calendar year.",
        });
        if (tableContainer) {
          window.NhseBarChart.renderTable(tableContainer, summary.years);
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
