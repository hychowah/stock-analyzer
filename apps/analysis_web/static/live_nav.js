/**
 * /portfolio only: poll GET /api/portfolio/live-nav, paint Live NAV / day
 * P/L / live values, then dispatch quotes-applied (Live cells, Downside)
 * and holding-pl-applied (heatmap rows). Sole writer of #quote-status.
 * Does not call /api/quotes. Does not read the MTM period strip.
 */
(function () {
  "use strict";

  var DEFAULT_TTL_MS = 120000;
  var timer = null;
  var ttlMs = DEFAULT_TTL_MS;

  function statusEl() {
    return document.getElementById("quote-status");
  }

  function setStatus(msg) {
    var el = statusEl();
    if (!el) {
      return;
    }
    if (!msg) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = msg;
  }

  function fmtNum(n) {
    if (n == null || n !== n) {
      return "—";
    }
    var abs = Math.abs(n);
    var digits = abs >= 1000 ? 2 : abs >= 1 ? 2 : 4;
    return n.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function fmtSigned(n) {
    if (n == null || n !== n) {
      return "—";
    }
    var sign = n > 0 ? "+" : "";
    return sign + fmtNum(n);
  }

  function clearEl(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  function paintNav(body) {
    var el = document.getElementById("live-nav");
    if (!el) {
      return;
    }
    var live = body && body.live_nav;
    var vintage = (body && body.vintage) || "";
    var cur = (body && body.base_currency) || el.getAttribute("data-base-currency") || "";
    clearEl(el);
    el.removeAttribute("data-vintage");
    if (live == null || live !== live) {
      el.appendChild(document.createTextNode("—"));
      return;
    }
    el.setAttribute("data-vintage", vintage);
    var num = document.createElement("span");
    num.textContent = fmtNum(live);
    el.appendChild(num);
    if (cur) {
      el.appendChild(document.createTextNode(" " + cur));
    }
    if (vintage) {
      el.appendChild(document.createTextNode(" "));
      var chip = document.createElement("span");
      chip.className = "live-nav-vintage muted";
      chip.textContent = vintage;
      el.appendChild(chip);
    }
  }

  function paintDay(body) {
    var el = document.getElementById("live-nav-day");
    if (!el) {
      return;
    }
    var day = body && body.day_pl;
    if (day == null || day !== day) {
      el.textContent = "—";
      el.title = "vs prior daily close";
      return;
    }
    el.textContent = fmtSigned(day);
    el.title = "vs prior daily close";
  }

  function holdingRows(rows) {
    return (rows || []).map(function (r) {
      return {
        ib_symbol: r && r.ib_symbol,
        pl: r && r.day_pl,
        change_pct: r && r.change_pct,
        contrib_pct: r && r.contrib_pct,
      };
    });
  }

  function emitHoldingPl(rows) {
    document.dispatchEvent(
      new CustomEvent("holding-pl-applied", {
        detail: { rows: holdingRows(rows) },
      })
    );
  }

  function paintLiveValues(rows) {
    var by = Object.create(null);
    (rows || []).forEach(function (r) {
      if (r && r.ib_symbol) {
        by[String(r.ib_symbol).toUpperCase()] = r;
      }
    });
    var cells = document.querySelectorAll("[data-live-value]");
    for (var i = 0; i < cells.length; i++) {
      var el = cells[i];
      var id = String(el.getAttribute("data-ib-symbol") || "")
        .trim()
        .toUpperCase();
      var row = id ? by[id] : null;
      if (row && row.live_value_base != null && row.live_value_base === row.live_value_base) {
        el.textContent = fmtNum(row.live_value_base);
      } else {
        el.textContent = "—";
      }
    }
  }

  function statusLine(body) {
    var n = (body && body.n_positions) || 0;
    var r = (body && body.n_repriced) || 0;
    var ttl = (body && body.ttl_sec) || 120;
    var mins = Math.max(1, Math.round(Number(ttl) / 60));
    var fx = body && body.period_to ? "FX as of " + body.period_to : "FX as of statement";
    return (
      "Yahoo last print · " +
      mins +
      " min · " +
      fx +
      " · " +
      r +
      "/" +
      n +
      " stocks marked"
    );
  }

  function poll() {
    if (document.visibilityState !== "visible") {
      return;
    }
    fetch("/api/portfolio/live-nav", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (res) {
        return res.json().then(function (body) {
          return { ok: res.ok, body: body };
        });
      })
      .then(function (payload) {
        if (!payload.ok) {
          setStatus(
            (payload.body && (payload.body.detail || payload.body.error)) ||
              "Live NAV failed"
          );
          return;
        }
        var body = payload.body || {};
        if (body.error && !body.n_positions) {
          setStatus(body.error);
          paintNav(body);
          paintDay(body);
          emitHoldingPl([]);
          return;
        }
        if (body.ttl_sec) {
          var next = Number(body.ttl_sec) * 1000;
          if (next >= 1000 && next !== ttlMs) {
            ttlMs = next;
            armTimer();
          }
        }
        paintNav(body);
        paintDay(body);
        paintLiveValues(body.rows);
        document.dispatchEvent(
          new CustomEvent("quotes-applied", {
            detail: { quotes: body.quotes || [] },
          })
        );
        emitHoldingPl(body.rows || []);
        setStatus(statusLine(body));
      })
      .catch(function () {
        setStatus("Live NAV failed");
      });
  }

  function armTimer() {
    if (timer) {
      clearInterval(timer);
    }
    timer = setInterval(poll, ttlMs);
  }

  function start() {
    poll();
    armTimer();
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      poll();
    }
  });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
