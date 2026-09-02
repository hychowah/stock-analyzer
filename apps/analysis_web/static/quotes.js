/**
 * Fill [data-quote-cell][data-quote-symbol] from GET /api/quotes.
 * Listing symbols only. Rebind after #runs-results swap via quotes-refresh.
 * Pause when the tab is hidden.
 */
(function () {
  "use strict";

  var MAX_SYMBOLS = 50;
  var DEFAULT_TTL_MS = 120000;
  var timer = null;
  var ttlMs = DEFAULT_TTL_MS;

  function uniqueSymbols() {
    var nodes = document.querySelectorAll("[data-quote-symbol]");
    var seen = Object.create(null);
    var out = [];
    for (var i = 0; i < nodes.length; i++) {
      var s = String(nodes[i].getAttribute("data-quote-symbol") || "")
        .trim()
        .toUpperCase();
      if (!s || seen[s]) {
        continue;
      }
      seen[s] = 1;
      out.push(s);
    }
    return out;
  }

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

  function clearCell(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  function fillCell(el, q) {
    clearCell(el);
    if (!q || q.error) {
      el.textContent = "—";
      el.title = (q && q.error) || "no quote";
      return;
    }
    var price = document.createElement("span");
    price.textContent = fmtNum(q.price);
    el.appendChild(price);
    if (q.change_pct != null) {
      el.appendChild(document.createTextNode(" "));
      var chg = document.createElement("span");
      var up = q.change_pct > 0;
      var down = q.change_pct < 0;
      chg.className = up ? "chg-up" : down ? "chg-down" : "muted";
      var sign = up ? "+" : "";
      chg.textContent = sign + q.change_pct.toFixed(1) + "%";
      el.appendChild(chg);
    }
    if (q.currency) {
      el.appendChild(document.createTextNode(" "));
      var cur = document.createElement("span");
      cur.className = "muted";
      cur.textContent = q.currency;
      el.appendChild(cur);
    }
    if (q.print_kind === "daily_close") {
      var kind = document.createElement("span");
      kind.className = "quote-kind";
      kind.textContent = "daily close";
      el.appendChild(kind);
    }
    var bits = [];
    if (q.as_of) {
      bits.push(q.as_of);
    }
    if (q.market_state) {
      bits.push(q.market_state);
    }
    if (bits.length) {
      el.title = bits.join(" · ");
    }
  }

  function applyQuotes(quotes) {
    var by = Object.create(null);
    (quotes || []).forEach(function (q) {
      if (q && q.symbol) {
        by[String(q.symbol).toUpperCase()] = q;
      }
    });
    var cells = document.querySelectorAll("[data-quote-cell]");
    for (var i = 0; i < cells.length; i++) {
      var el = cells[i];
      var s = String(el.getAttribute("data-quote-symbol") || "")
        .trim()
        .toUpperCase();
      if (!s) {
        el.textContent = "—";
        el.title = "unstamped";
        continue;
      }
      fillCell(el, by[s] || { error: "unavailable", symbol: s });
    }
  }

  function poll() {
    if (document.visibilityState !== "visible") {
      return;
    }
    var syms = uniqueSymbols();
    if (!syms.length) {
      setStatus("");
      return;
    }
    if (syms.length > MAX_SYMBOLS) {
      setStatus(
        "Live quotes: " +
          syms.length +
          " unique listings on this page; cap is " +
          MAX_SYMBOLS +
          ". Narrow the list."
      );
      return;
    }
    setStatus("");
    var url = "/api/quotes?symbols=" + encodeURIComponent(syms.join(","));
    fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) {
        return r.json().then(function (body) {
          return { ok: r.ok, body: body };
        });
      })
      .then(function (payload) {
        if (!payload.ok) {
          setStatus((payload.body && payload.body.detail) || "Live quotes failed");
          return;
        }
        if (payload.body && payload.body.ttl_sec) {
          var next = Number(payload.body.ttl_sec) * 1000;
          if (next >= 1000 && next !== ttlMs) {
            ttlMs = next;
            armTimer();
          }
        }
        applyQuotes(payload.body.quotes);
      })
      .catch(function () {
        setStatus("Live quotes failed");
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

  document.addEventListener("quotes-refresh", function () {
    poll();
  });
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
