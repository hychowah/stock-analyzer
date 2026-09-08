/**
 * What-if page helpers. Page works without this file.
 * Loads the NAV path after first paint; date change fetches holdings only.
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

  function fmt(n, digits) {
    if (n == null || n !== n) {
      return "—";
    }
    var d = digits == null ? 2 : digits;
    return Number(n).toLocaleString(undefined, {
      minimumFractionDigits: d,
      maximumFractionDigits: d,
    });
  }

  function setDeltaClass(el, delta) {
    if (!el) {
      return;
    }
    el.classList.remove("delta-pos", "delta-neg");
    if (delta > 0) {
      el.classList.add("delta-pos");
    } else if (delta < 0) {
      el.classList.add("delta-neg");
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var card = document.getElementById("hist-holdings-card");
  var historyId = card ? card.getAttribute("data-history-id") : "";
  var holdingsUrl = card ? card.getAttribute("data-holdings-url") : "";
  var pathUrl = card ? card.getAttribute("data-path-url") : "";

  function setAsOf(day) {
    var inputs = document.querySelectorAll('#hist-holdings-card input[name="as_of"], #hist-universe input[name="as_of"]');
    for (var i = 0; i < inputs.length; i++) {
      inputs[i].value = day;
    }
  }

  function renderHeld(held, viewDate) {
    var wrap = document.getElementById("hist-held-table");
    var caption = document.getElementById("hist-held-caption");
    if (caption) {
      caption.textContent =
        "What the paper book held on " +
        viewDate +
        ". Names marked “sold later” are gone from today’s copied actual — not from a live IB walk.";
    }
    if (!wrap) {
      return;
    }
    if (!held || !held.length) {
      wrap.innerHTML = '<p class="muted">No stock lots on this date.</p>';
      return;
    }
    var rows = [];
    for (var i = 0; i < held.length; i++) {
      var lot = held[i];
      var listing = String(lot.listing || "");
      var extra = "";
      if (lot.ib_symbol && lot.ib_symbol !== listing) {
        extra += ' <span class="muted">' + escapeHtml(lot.ib_symbol) + "</span>";
      }
      if (lot.deceased) {
        extra += ' <span class="badge">sold later</span>';
      }
      rows.push(
        "<tr>" +
          '<td class="mono">' +
          escapeHtml(listing) +
          extra +
          "</td>" +
          '<td class="num">' +
          fmt(lot.qty, 2) +
          "</td>" +
          '<td class="num">' +
          fmt(lot.close) +
          "</td>" +
          '<td class="num">' +
          fmt(lot.value_base) +
          "</td>" +
          "<td>" +
          '<form method="post" action="/portfolio/histories/' +
          encodeURIComponent(historyId) +
          '/decisions" class="hist-sell-row">' +
          '<input type="hidden" name="side" value="sell"/>' +
          '<input type="hidden" name="listing" value="' +
          escapeHtml(listing) +
          '"/>' +
          '<input type="hidden" name="as_of" value="' +
          escapeHtml(viewDate) +
          '"/>' +
          "<label>Qty <input name=\"quantity\" type=\"number\" step=\"any\" min=\"0\" max=\"" +
          escapeHtml(lot.qty) +
          '" value="' +
          escapeHtml(lot.qty) +
          '" required/></label>' +
          '<button type="submit">Sell</button>' +
          "</form></td></tr>"
      );
    }
    wrap.innerHTML =
      '<div class="table-freeze"><table>' +
      "<thead><tr><th>Listing</th><th>Qty</th><th>Close</th><th>Value</th><th>Sell</th></tr></thead>" +
      "<tbody>" +
      rows.join("") +
      "</tbody></table></div>";
  }

  function loadHoldings(day) {
    if (!holdingsUrl) {
      return;
    }
    var url = holdingsUrl + (day ? "?date=" + encodeURIComponent(day) : "");
    fetch(url, { headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) {
          throw new Error("holdings " + r.status);
        }
        return r.json();
      })
      .then(function (body) {
        var view = body.view_date || day;
        renderHeld(body.held || [], view);
        setAsOf(view);
        if (card) {
          card.setAttribute("data-view-date", view);
        }
        var dateInput = document.getElementById("hist-view-date");
        if (dateInput && view) {
          dateInput.value = view;
        }
        var buySummary = document.getElementById("hist-buy-summary");
        if (buySummary && view) {
          buySummary.textContent = "Buy a researched name on " + view;
        }
      })
      .catch(function () {
        /* keep the server-rendered table */
      });
  }

  var dateForm = document.getElementById("hist-date-form");
  if (dateForm) {
    dateForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var dateInput = document.getElementById("hist-view-date");
      var day = dateInput ? String(dateInput.value || "").trim() : "";
      loadHoldings(day);
      try {
        var next = new URL(window.location.href);
        if (day) {
          next.searchParams.set("date", day);
        }
        window.history.replaceState({}, "", next.toString());
      } catch (e) {
        /* ignore */
      }
    });
  }

  function bindChart(points) {
    var readout = document.getElementById("hist-chart-readout");
    var svg = document.querySelector("#hist-chart svg");
    if (!readout || !svg || !points || !points.length) {
      return;
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
  }

  if (pathUrl) {
    fetch(pathUrl, { headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) {
          throw new Error("path " + r.status);
        }
        return r.json();
      })
      .then(function (body) {
        var altEl = document.getElementById("hist-alt-nav");
        var actEl = document.getElementById("hist-actual-nav");
        var deltaEl = document.getElementById("hist-delta");
        if (altEl) {
          altEl.textContent = fmt(body.alt_nav);
        }
        if (actEl) {
          actEl.textContent = fmt(body.actual_nav);
        }
        if (deltaEl) {
          deltaEl.textContent = fmt(body.delta);
          setDeltaClass(deltaEl, body.delta);
        }
        var chart = document.getElementById("hist-chart");
        if (chart && body.svg) {
          chart.innerHTML = body.svg;
        }
        bindChart(body.path || []);
      })
      .catch(function () {
        /* noscript img remains if JS failed before replacing */
      });
  }

  if (holdingsUrl) {
    loadHoldings(card ? card.getAttribute("data-view-date") : "");
  }
})();
