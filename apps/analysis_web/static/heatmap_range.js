/**
 * /portfolio heatmap time-base. Owns Live vs a named/custom window.
 * Named chips GET /api/portfolio/mtm-path?period= (server resolve_period).
 * Show GET start=&end=. Last frame paints tiles. Does not write MTM bars.
 * Live restores cached live tiles immediately (heatmap-live), no poll wait.
 */
(function () {
  "use strict";

  var card = document.getElementById("heatmap-card");
  var rangeRoot = document.getElementById("heatmap-range");
  if (!card || !rangeRoot) {
    return;
  }

  var heading = document.getElementById("heatmap-heading");
  var caption = document.getElementById("heatmap-caption");
  var statusEl = document.getElementById("heatmap-status");
  var fromEl = document.getElementById("heatmap-from");
  var toEl = document.getElementById("heatmap-to");
  var showBtn = document.getElementById("heatmap-show");
  var svg = document.getElementById("heatmap-svg");
  var liveCaption = caption ? caption.textContent : "";
  var LIVE_HEADING = "Day move";
  var RANGE_HEADING = "Holding influence";
  var LIVE_LABEL = "Portfolio day-move heatmap";
  var RANGE_LABEL = "Portfolio holding-influence heatmap";
  var RANGE_CAPTION =
    "Tile area is the |period change| of that holding (mark change plus IB fill cash). Stock % is the listing move over the window; NAV % is this holding’s P/L as % of NAV at the start of the window. Gainers left, losers right (stacked on a narrow screen).";

  var req = 0;

  function setStatus(msg) {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = msg || "";
  }

  function setToken(period) {
    card.setAttribute("data-heatmap-period", period);
  }

  function setWindowPressed(name) {
    var chips = rangeRoot.querySelectorAll("[data-heatmap-window]");
    for (var i = 0; i < chips.length; i++) {
      var on = chips[i].getAttribute("data-heatmap-window") === name;
      chips[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  function emitRange(rows) {
    document.dispatchEvent(
      new CustomEvent("heatmap-range-applied", { detail: { rows: rows || [] } })
    );
  }

  function emitLive() {
    document.dispatchEvent(new Event("heatmap-live"));
  }

  function restoreLive(statusMsg) {
    req += 1;
    setToken("live");
    if (heading) {
      heading.textContent = LIVE_HEADING;
    }
    if (caption) {
      caption.textContent = liveCaption;
    }
    if (svg) {
      svg.setAttribute("aria-label", LIVE_LABEL);
    }
    setWindowPressed("live");
    emitLive();
    setStatus(statusMsg || "");
  }

  function beginRange() {
    setToken("range");
    if (heading) {
      heading.textContent = RANGE_HEADING;
    }
    if (caption) {
      caption.textContent = RANGE_CAPTION;
    }
    if (svg) {
      svg.setAttribute("aria-label", RANGE_LABEL);
    }
    emitRange([]);
    setStatus("Loading period marks…");
  }

  function rowMap(rows) {
    return (rows || []).map(function (r) {
      return {
        ib_symbol: r && r.ib_symbol,
        pl: r && r.pl,
        change_pct: r && r.change_pct,
        contrib_pct: r && r.contrib_pct,
      };
    });
  }

  function applyBody(body, windowName) {
    var frames = (body && body.frames) || [];
    if (body && body.start && fromEl) {
      fromEl.value = body.start;
    }
    if (body && body.end && toEl) {
      toEl.value = body.end;
    }
    if (caption) {
      var text = RANGE_CAPTION;
      if (body && body.start && body.end) {
        text += " Window " + body.start + " to " + body.end + ".";
      }
      caption.textContent = text;
    }
    setWindowPressed(windowName);
    if (!frames.length) {
      emitRange([]);
      setStatus((body && body.error) || "No daily closes in this period");
      return;
    }
    var last = frames[frames.length - 1];
    emitRange(rowMap(last.rows));
    setStatus("");
  }

  function loadUrl(url, windowName) {
    var my = ++req;
    beginRange();
    fetch(url, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (res) {
        return res.json().then(function (body) {
          return { ok: res.ok, body: body };
        });
      })
      .then(function (payload) {
        if (my !== req) {
          return;
        }
        if (!payload.ok) {
          var detail =
            (payload.body && (payload.body.detail || payload.body.error)) ||
            "Period marks failed";
          restoreLive(detail);
          return;
        }
        applyBody(payload.body || {}, windowName);
      })
      .catch(function () {
        if (my !== req) {
          return;
        }
        restoreLive("Period marks failed");
      });
  }

  var pf = card.getAttribute("data-period-from") || "";
  var pt = card.getAttribute("data-period-to") || "";
  if (fromEl && pf) {
    fromEl.title = "Statement from " + pf;
  }
  if (toEl && pt) {
    toEl.title = "Statement to " + pt;
  }

  rangeRoot.addEventListener("click", function (ev) {
    var btn =
      ev.target && ev.target.closest
        ? ev.target.closest("[data-heatmap-window]")
        : null;
    if (!btn || !rangeRoot.contains(btn)) {
      return;
    }
    var next = btn.getAttribute("data-heatmap-window");
    if (!next) {
      return;
    }
    if (next === "live") {
      restoreLive("");
      return;
    }
    loadUrl(
      "/api/portfolio/mtm-path?period=" + encodeURIComponent(next),
      next
    );
  });

  if (showBtn) {
    showBtn.addEventListener("click", function () {
      var a = fromEl && fromEl.value;
      var b = toEl && toEl.value;
      if (!a || !b) {
        setStatus("Choose from and to dates");
        return;
      }
      if (a > b) {
        setStatus("From must be on or before to");
        return;
      }
      loadUrl(
        "/api/portfolio/mtm-path?start=" +
          encodeURIComponent(a) +
          "&end=" +
          encodeURIComponent(b),
        "custom"
      );
    });
  }
})();
