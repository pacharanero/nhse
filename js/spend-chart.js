// Renders the "Spend over time" bar chart on the spending page from
// spend-by-year.json, using the shared renderer in js/bar-chart.js.
(function () {
  "use strict";

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
        window.NhseBarChart.render(chartContainer, summary.years, {
          idPrefix: "spend-chart",
          title: "NHS England detailed payments by year",
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
