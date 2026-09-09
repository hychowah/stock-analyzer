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

  var card = document.getElementById("hist-holdings-card");
  var heldUrl = card ? card.getAttribute("data-held-url") : "";
  var pathUrl = card ? card.getAttribute("data-path-url") : "";

  function setAsOf(day) {
    var inputs = document.querySelectorAll('#hist-holdings-card input[name="as_of"], #hist-universe input[name="as_of"]');
    for (var i = 0; i < inputs.length; i++) {
      inputs[i].value = day;
    }
  }

  function applyViewDate(view) {
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
    var caption = document.getElementById("hist-held-caption");
    if (caption) {
      caption.textContent =
        "What the paper book held on " +
        view +
        ". Names marked “sold later” are gone from today’s copied actual — not from a live IB walk.";
    }
  }

  /* Holdings cash is as of D in the table fragment. Do not copy it into header cash. */
  function loadHoldings(day) {
    if (!heldUrl) {
      return;
    }
    var url = heldUrl + (day ? "?date=" + encodeURIComponent(day) : "");
    fetch(url, { headers: { Accept: "text/html" } })
      .then(function (r) {
        if (!r.ok) {
          throw new Error("held " + r.status);
        }
        return r.text();
      })
      .then(function (html) {
        var wrap = document.getElementById("hist-held-table");
        if (!wrap) {
          return;
        }
        wrap.innerHTML = html;
        var root = wrap.querySelector("[data-view-date]");
        var view = (root && root.getAttribute("data-view-date")) || day;
        applyViewDate(view);
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

  if (heldUrl) {
    loadHoldings(card ? card.getAttribute("data-view-date") : "");
  }
})();
