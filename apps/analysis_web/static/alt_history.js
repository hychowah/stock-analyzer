/**
 * What-if page helpers. Page works without this file.
 * Loads the NAV path after first paint. A date change fetches the held
 * fragment, universe closes, and (if a ticker is selected) the ticket
 * preview — not the path.
 */
(function () {
  "use strict";

  document.documentElement.classList.add("is-js");

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

  function paintBreakdown(rows) {
    var table = document.getElementById("hist-breakdown");
    var card = document.getElementById("hist-breakdown-card");
    var tbody = table ? table.querySelector("tbody") : null;
    if (!tbody) {
      return;
    }
    tbody.textContent = "";
    if (!rows || !rows.length) {
      if (card) {
        card.hidden = true;
      }
      return;
    }
    if (card) {
      card.hidden = false;
    }
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i] || {};
      var tr = document.createElement("tr");
      var name = document.createElement("td");
      name.className = "mono";
      name.textContent = row.name || "";
      var barCell = document.createElement("td");
      barCell.className = "perf-bar-cell";
      var bar = document.createElement("span");
      bar.className = "perf-bar " + (row.sign || "zero");
      bar.style.width = Number(row.bar_pct || 0).toFixed(1) + "%";
      barCell.appendChild(bar);
      var pl = document.createElement("td");
      pl.className = "num";
      pl.textContent = fmt(row.pl);
      tr.appendChild(name);
      tr.appendChild(barCell);
      tr.appendChild(pl);
      tbody.appendChild(tr);
    }
  }

  var card = document.getElementById("hist-holdings-card");
  var heldUrl = card ? card.getAttribute("data-held-url") : "";
  var pathUrl = card ? card.getAttribute("data-path-url") : "";
  var universeUrl = card ? card.getAttribute("data-universe-url") : "";
  var ticketUrl = card ? card.getAttribute("data-ticket-url") : "";
  var baseCcy = card ? card.getAttribute("data-base-currency") || "" : "";

  var showBtn = document.getElementById("hist-show-holdings");
  if (showBtn) {
    showBtn.hidden = true;
  }

  function currentDate() {
    var dateInput = document.getElementById("hist-view-date");
    return dateInput ? String(dateInput.value || "").trim() : "";
  }

  function setAsOf(day) {
    var inputs = document.querySelectorAll(
      '#hist-holdings-card input[name="as_of"], #hist-universe input[name="as_of"], #hist-ticket-asof'
    );
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

  function markHeldBusy(busy) {
    var wrap = document.getElementById("hist-held-table");
    if (!wrap) {
      return;
    }
    wrap.classList.toggle("is-loading", !!busy);
    if (busy) {
      wrap.setAttribute("aria-busy", "true");
    } else {
      wrap.removeAttribute("aria-busy");
    }
  }

  /* Holdings cash is as of D in the table fragment. Do not copy it into header cash. */
  function loadHoldings(day) {
    if (!heldUrl) {
      return;
    }
    markHeldBusy(true);
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
        markHeldBusy(false);
        refreshTicket();
      })
      .catch(function () {
        markHeldBusy(false);
        var wrap = document.getElementById("hist-held-table");
        if (!wrap) {
          return;
        }
        var note = wrap.querySelector(".hist-held-fetch-error");
        if (!note) {
          note = document.createElement("p");
          note.className = "err hist-held-fetch-error";
          note.setAttribute("role", "alert");
          wrap.insertBefore(note, wrap.firstChild);
        }
        note.innerHTML =
          'Could not load closes for this date. <button type="button" class="secondary hist-retry-marks">Retry prices</button>';
      });
  }

  function closeLabel(mark, view) {
    if (!mark) {
      return "Loading closes for " + view + "…";
    }
    if (mark.status === "unavailable") {
      return "Yahoo failed";
    }
    if (mark.status !== "quoted" || mark.close == null) {
      return "No close on or before " + view;
    }
    var text = fmt(mark.close);
    if (mark.bar_date && mark.bar_date !== view) {
      text += " · " + mark.bar_date;
    }
    return text;
  }

  function loadUniverse(day) {
    if (!universeUrl || !table) {
      return;
    }
    var url = universeUrl + (day ? "?date=" + encodeURIComponent(day) : "");
    fetch(url, { headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) {
          throw new Error("universe " + r.status);
        }
        return r.json();
      })
      .then(function (body) {
        var rows = body.universe || [];
        var byTicker = {};
        for (var i = 0; i < rows.length; i++) {
          byTicker[String(rows[i].ticker || "").toUpperCase()] = rows[i];
        }
        var trs = table.querySelectorAll("tbody tr");
        var view = body.view_date || day;
        for (var j = 0; j < trs.length; j++) {
          var ticker = String(trs[j].getAttribute("data-ticker") || "").toUpperCase();
          var row = byTicker[ticker];
          var closeCell = trs[j].querySelector(".hist-buy-close");
          var pick = trs[j].querySelector(".hist-buy-pick");
          if (closeCell) {
            closeCell.textContent = closeLabel(row && row.mark, view);
          }
          if (pick) {
            pick.disabled = !(row && row.pickable);
            if (row && row.listing) {
              pick.setAttribute("data-listing", row.listing);
            }
            if (row && row.currency) {
              pick.setAttribute("data-currency", row.currency);
            }
          }
        }
      })
      .catch(function () {
        var cells = table.querySelectorAll(".hist-buy-close");
        for (var i = 0; i < cells.length; i++) {
          cells[i].textContent = "Yahoo failed";
        }
      });
  }

  function onDateChanged(day) {
    loadHoldings(day);
    loadUniverse(day);
    try {
      var next = new URL(window.location.href);
      if (day) {
        next.searchParams.set("date", day);
      }
      window.history.replaceState({}, "", next.toString());
    } catch (e) {
      /* ignore */
    }
  }

  var dateForm = document.getElementById("hist-date-form");
  var dateInput = document.getElementById("hist-view-date");
  if (dateForm) {
    dateForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      onDateChanged(currentDate());
    });
  }
  if (dateInput) {
    dateInput.addEventListener("change", function () {
      onDateChanged(currentDate());
    });
  }

  var heldWrap = document.getElementById("hist-held-table");
  if (heldWrap) {
    heldWrap.addEventListener("click", function (ev) {
      var btn = ev.target.closest ? ev.target.closest(".hist-retry-marks") : null;
      if (!btn) {
        return;
      }
      ev.preventDefault();
      loadHoldings(currentDate());
      loadUniverse(currentDate());
    });
  }

  var ticketForm = document.getElementById("hist-ticket-form");
  var ticketTicker = document.getElementById("hist-ticket-ticker");
  var ticketListing = document.getElementById("hist-ticket-listing");
  var ticketSide = document.getElementById("hist-ticket-side");
  var ticketQty = document.getElementById("hist-ticket-qty");
  var ticketFill = document.getElementById("hist-ticket-fill");
  var ticketEstimate = document.getElementById("hist-ticket-estimate");
  var ticketAfter = document.getElementById("hist-ticket-after");
  var ticketError = document.getElementById("hist-ticket-error");
  var ticketConfirm = document.getElementById("hist-ticket-confirm");
  var ticketEmpty = document.getElementById("hist-ticket-empty");
  var ticketCurrency = "";

  function setTicketError(msg) {
    if (!ticketError) {
      return;
    }
    if (msg) {
      ticketError.hidden = false;
      ticketError.textContent = msg;
    } else {
      ticketError.hidden = true;
      ticketError.textContent = "";
    }
  }

  function refreshTicket() {
    if (!ticketUrl || !ticketForm || !ticketTicker) {
      return;
    }
    var ticker = String(ticketTicker.value || "").trim().toUpperCase();
    var listing = ticketListing ? String(ticketListing.value || "").trim().toUpperCase() : "";
    var qty = ticketQty ? String(ticketQty.value || "").trim() : "";
    if (!ticker && !listing) {
      if (ticketFill) {
        ticketFill.textContent = "";
      }
      if (ticketEstimate) {
        ticketEstimate.textContent = "";
      }
      if (ticketAfter) {
        ticketAfter.textContent = "";
      }
      if (ticketConfirm) {
        ticketConfirm.disabled = true;
      }
      setTicketError("");
      return;
    }
    var day = currentDate();
    var url =
      ticketUrl +
      "?date=" +
      encodeURIComponent(day) +
      "&side=" +
      encodeURIComponent((ticketSide && ticketSide.value) || "buy") +
      "&listing=" +
      encodeURIComponent(listing || ticker) +
      "&ticker=" +
      encodeURIComponent(ticker) +
      "&quantity=" +
      encodeURIComponent(qty) +
      "&currency=" +
      encodeURIComponent(ticketCurrency);
    fetch(url, { headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) {
          throw new Error("ticket " + r.status);
        }
        return r.json();
      })
      .then(function (body) {
        var mark = body.mark || {};
        var view = body.view_date || day;
        if (ticketFill) {
          if (mark.status === "quoted" && mark.close != null) {
            ticketFill.textContent =
              "Yahoo daily close on " +
              (mark.bar_date || view) +
              ": " +
              fmt(mark.close);
          } else {
            ticketFill.textContent = closeLabel(mark, view);
          }
        }
        if (ticketEstimate) {
          if (body.cost_base != null) {
            ticketEstimate.textContent =
              "Estimated cost " + fmt(body.cost_base) + (baseCcy ? " " + baseCcy : "");
          } else {
            ticketEstimate.textContent = "";
          }
        }
        if (ticketAfter && body.after) {
          var a = body.after;
          ticketAfter.textContent =
            "After: cash " +
            fmt(a.cash) +
            " · loan " +
            fmt(a.loan) +
            " · excess " +
            fmt(a.excess) +
            " · buying power " +
            fmt(a.buying_power);
        } else if (ticketAfter) {
          ticketAfter.textContent = "";
        }
        var quoted = mark.status === "quoted" && mark.close != null;
        var hasQty = qty !== "" && Number(qty) > 0;
        if (ticketConfirm) {
          ticketConfirm.disabled = !(quoted && hasQty);
        }
        if (!quoted) {
          setTicketError(
            mark.status === "unavailable"
              ? "Yahoo failed for this listing on " + view + "."
              : "No close on or before " + view + "."
          );
        } else {
          setTicketError("");
        }
      })
      .catch(function () {
        setTicketError("Could not preview this ticket.");
        if (ticketConfirm) {
          ticketConfirm.disabled = true;
        }
      });
  }

  function pickBuy(ticker, listing, currency) {
    ticketCurrency = currency || "";
    if (ticketEmpty) {
      ticketEmpty.textContent = "Buy " + ticker + " on " + currentDate() + ".";
    }
    if (ticketSide) {
      ticketSide.value = "buy";
    }
    if (ticketTicker) {
      ticketTicker.value = ticker;
    }
    if (ticketListing) {
      ticketListing.value = listing || ticker;
    }
    if (ticketConfirm) {
      ticketConfirm.textContent = "Confirm buy";
    }
    if (ticketQty && !ticketQty.value) {
      ticketQty.focus();
    }
    refreshTicket();
  }

  if (table) {
    table.addEventListener("click", function (ev) {
      var btn = ev.target.closest ? ev.target.closest(".hist-buy-pick") : null;
      if (!btn || btn.disabled) {
        return;
      }
      ev.preventDefault();
      pickBuy(
        String(btn.getAttribute("data-ticker") || ""),
        String(btn.getAttribute("data-listing") || ""),
        String(btn.getAttribute("data-currency") || "")
      );
    });
  }
  if (ticketTicker) {
    ticketTicker.addEventListener("change", refreshTicket);
    ticketTicker.addEventListener("input", function () {
      if (ticketListing) {
        ticketListing.value = String(ticketTicker.value || "").trim().toUpperCase();
      }
    });
  }
  if (ticketQty) {
    ticketQty.addEventListener("input", refreshTicket);
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
        paintBreakdown(body.breakdown || []);
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
  if (universeUrl) {
    loadUniverse(card ? card.getAttribute("data-view-date") : "");
  }
})();
