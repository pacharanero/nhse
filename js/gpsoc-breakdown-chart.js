// Renders the EMIS/TPP "paying channel" stacked bar charts on the spending
// page from gpsoc-supplier-breakdown.json, using js/supplier-channel-chart.js.
(function () {
  "use strict";

  function init() {
    const emisContainer = document.getElementById("gpsoc-chart-emis");
    const tppContainer = document.getElementById("gpsoc-chart-tpp");
    if (!emisContainer && !tppContainer) {
      return;
    }
    fetch("gpsoc-supplier-breakdown.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("gpsoc-supplier-breakdown.json: " + response.status);
        }
        return response.json();
      })
      .then((summary) => {
        const bySupplier = Object.fromEntries(summary.suppliers.map((supplier) => [supplier.key, supplier]));
        [
          { key: "emis", chartId: "gpsoc-chart-emis", legendId: "gpsoc-legend-emis", tableId: "gpsoc-table-emis" },
          { key: "tpp", chartId: "gpsoc-chart-tpp", legendId: "gpsoc-legend-tpp", tableId: "gpsoc-table-tpp" },
        ].forEach(({ key, chartId, legendId, tableId }) => {
          const chartContainer = document.getElementById(chartId);
          const legendContainer = document.getElementById(legendId);
          const tableContainer = document.getElementById(tableId);
          const supplier = bySupplier[key];
          if (!chartContainer || !supplier) {
            return;
          }
          window.NhseSupplierChannelChart.render(chartContainer, supplier, summary.channels, { idPrefix: chartId });
          if (legendContainer) {
            window.NhseSupplierChannelChart.renderLegend(legendContainer, summary.channels);
          }
          if (tableContainer) {
            window.NhseSupplierChannelChart.renderTable(tableContainer, supplier, summary.channels);
          }
        });
      })
      .catch((error) => {
        [emisContainer, tppContainer].forEach((container) => {
          if (container) {
            container.textContent = "Chart unavailable (" + error.message + ").";
          }
        });
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
