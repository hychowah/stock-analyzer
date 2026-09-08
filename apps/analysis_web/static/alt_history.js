/**
 * What-if page helpers. Page works without this file.
 * Search-filters the researched table; hover readout on the NAV path.
 */
(function () {
  "use strict";

  var filter = document.getElementById("hist-universe-filter");
  var table = document.getElementById("hist-universe");
  if (filter && table) {
    filter.addEventListener("input", function () {
      var q = String(filter.value || "").trim().toUpperCase();
      var rows = table.querySelectorAll("tbody tr");
      for (var i = 0; i < rows.length; i++) {
        var ticker = String(rows[i].getAttribute("data-ticker") || "").toUpperCase();
        rows[i].hidden = q.length > 0 && ticker.indexOf(q) < 0;
      }
    });
  }

  var pathEl = document.getElementById("hist-path");
  var readout = document.getElementById("hist-chart-readout");
  var svg = document.querySelector("#hist-chart svg");
  if (!pathEl || !readout || !svg) {
    return;
  }
  var points = [];
  try {
    points = JSON.parse(pathEl.textContent || "[]") || [];
  } catch (e) {
    points = [];
  }
  if (!points.length) {
    return;
  }

  function fmt(n) {
    if (n == null || n !== n) {
      return "—";
    }
    return Number(n).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function show(i) {
    if (i < 0 || i >= points.length) {
      readout.textContent = "";
      return;
    }
    var p = points[i];
    readout.textContent =
      p.t +
      " · alt " +
      fmt(p.alt_nav) +
      " · actual " +
      fmt(p.actual_nav) +
      " · Δ " +
      fmt(p.delta);
  }

  show(points.length - 1);
  svg.addEventListener("mousemove", function (ev) {
    var rect = svg.getBoundingClientRect();
    if (!rect.width) {
      return;
    }
    var x = (ev.clientX - rect.left) / rect.width;
    var i = Math.round(x * (points.length - 1));
    if (i < 0) {
      i = 0;
    }
    if (i >= points.length) {
      i = points.length - 1;
    }
    show(i);
  });
  svg.addEventListener("mouseleave", function () {
    show(points.length - 1);
  });
})();
