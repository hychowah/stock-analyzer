/**
 * Fill [data-quote-cell][data-quote-symbol] from GET /api/quotes.
 * After prints land, recompute [data-downside-pct] from live (else as-of) vs data-fv-bear.
 * data-quote-symbol is catalog quote_listing; chart-name repair is server-side.
 * Rebind after #runs-results swap via quotes-refresh. Pause when the tab is hidden.
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
    el.classList.remove("chg-up", "chg-down");
    el.removeAttribute("aria-busy");
    clearCell(el);
    if (!q || q.error) {
      el.appendChild(document.createTextNode("—"));
      el.title = (q && q.error) || "no quote";
      return;
    }
    var price = document.createElement("span");
    price.textContent = fmtNum(q.price);
    el.appendChild(price);
    if (q.change_pct != null) {
      el.appendChild(document.createTextNode(" "));
      var chg = document.createElement("span");
      var sign = q.change_pct > 0 ? "+" : "";
      chg.className = "quote-chip";
      if (q.change_pct > 0) {
        chg.className += " chg-up";
      } else if (q.change_pct < 0) {
        chg.className += " chg-down";
      }
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

  function parseAttrNum(el, name) {
    var raw = el.getAttribute(name);
    if (raw == null || String(raw).trim() === "") {
      return null;
    }
    var n = Number(raw);
    return n === n ? n : null;
  }

  function downsidePct(price, fvBear) {
    if (price == null || fvBear == null || price === 0) {
      return null;
    }
    return ((price - fvBear) / price) * 100;
  }

  function fmtDownside(n) {
    if (n == null || n !== n) {
      return "—";
    }
    return n.toLocaleString(undefined, {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });
  }

  function quoteSymbolFor(el) {
    var row = el.closest("tr");
    var live = row ? row.querySelector("[data-quote-cell][data-quote-symbol]") : null;
    if (!live) {
      var table = el.closest("table");
      live = table ? table.querySelector("[data-quote-cell][data-quote-symbol]") : null;
    }
    if (!live) {
      return "";
    }
    return String(live.getAttribute("data-quote-symbol") || "")
      .trim()
      .toUpperCase();
  }

  function fillDownside(by) {
    var cells = document.querySelectorAll("[data-downside-pct]");
    for (var i = 0; i < cells.length; i++) {
      var el = cells[i];
      var fvBear = parseAttrNum(el, "data-fv-bear");
      var asof = parseAttrNum(el, "data-asof-price");
      var s = quoteSymbolFor(el);
      var q = s ? by[s] : null;
      var liveOk = q && q.price != null && !q.error;
      var price = liveOk ? q.price : asof;
      var vintage = liveOk ? "live" : "as-of";
      var value = downsidePct(price, fvBear);
      el.setAttribute("data-vintage", vintage);
      el.classList.toggle("below-bear", value != null && value < 0);
      el.textContent = fmtDownside(value);
      var vintageEl = document.createElement("span");
      vintageEl.className = "downside-vintage muted";
      vintageEl.textContent = " " + vintage;
      el.appendChild(vintageEl);
      if (value == null || price == null || fvBear == null) {
        el.removeAttribute("title");
        continue;
      }
      el.title = vintage + " · " + fmtNum(price) + " → bear " + fmtNum(fvBear);
    }
  }

  function applyQuotes(quotes, requested) {
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
        el.classList.remove("chg-up", "chg-down");
        el.removeAttribute("aria-busy");
        el.textContent = "—";
        el.title = "unstamped";
        continue;
      }
      if (requested && !requested[s]) {
        el.classList.remove("chg-up", "chg-down");
        el.removeAttribute("aria-busy");
        el.textContent = "—";
        el.title = "over quote cap";
        continue;
      }
      fillCell(el, by[s] || { error: "unavailable", symbol: s });
    }
    fillDownside(by);
  }

  function markLoading(syms) {
    var want = Object.create(null);
    var i;
    for (i = 0; i < syms.length; i++) {
      want[syms[i]] = 1;
    }
    var cells = document.querySelectorAll("[data-quote-cell][data-quote-symbol]");
    for (i = 0; i < cells.length; i++) {
      var el = cells[i];
      var s = String(el.getAttribute("data-quote-symbol") || "")
        .trim()
        .toUpperCase();
      if (!s || !want[s]) {
        continue;
      }
      el.setAttribute("aria-busy", "true");
      el.textContent = "…";
    }
  }

  function poll() {
    if (document.visibilityState !== "visible") {
      return;
    }
    var all = uniqueSymbols();
    if (!all.length) {
      setStatus("");
      return;
    }
    var syms = all.slice(0, MAX_SYMBOLS);
    var requested = Object.create(null);
    var i;
    for (i = 0; i < syms.length; i++) {
      requested[syms[i]] = 1;
    }
    if (all.length > MAX_SYMBOLS) {
      setStatus(
        "Live quotes: first " +
          MAX_SYMBOLS +
          " of " +
          all.length +
          " listings on this page."
      );
    } else {
      setStatus("");
    }
    markLoading(syms);
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
          applyQuotes([], requested);
          return;
        }
        if (payload.body && payload.body.ttl_sec) {
          var next = Number(payload.body.ttl_sec) * 1000;
          if (next >= 1000 && next !== ttlMs) {
            ttlMs = next;
            armTimer();
          }
        }
        applyQuotes(payload.body.quotes, requested);
      })
      .catch(function () {
        setStatus("Live quotes failed");
        applyQuotes([], requested);
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
