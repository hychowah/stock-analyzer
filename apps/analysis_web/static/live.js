/**
 * Lightweight live reload for Archive Analysis.
 * - Prefer SSE /api/events (catalog_changed / portfolio_changed)
 * - Fallback: poll /api/fingerprint every 5s if EventSource fails
 * Opt-in: <body data-live-reload="1">
 */
(function () {
  "use strict";

  function wantsReload() {
    return document.body && document.body.getAttribute("data-live-reload") === "1";
  }

  function flash(msg) {
    var existing = document.getElementById("live-flash");
    if (existing) {
      existing.textContent = msg;
      return;
    }
    var p = document.createElement("p");
    p.id = "live-flash";
    p.className = "flash";
    p.textContent = msg;
    var main = document.querySelector("main");
    if (main) {
      main.insertBefore(p, main.firstChild);
    }
  }

  function reloadSoon() {
    if (!wantsReload()) return;
    if (document.body && document.body.getAttribute("data-live-partial") === "1") {
      document.dispatchEvent(new CustomEvent("catalog-changed"));
      return;
    }
    flash("Catalog updated — refreshing…");
    setTimeout(function () {
      window.location.reload();
    }, 400);
  }

  var lastToken = null;
  var sseOk = false;

  function onToken(token, kind) {
    if (!token) return;
    if (lastToken === null) {
      lastToken = token;
      return;
    }
    if (token !== lastToken) {
      lastToken = token;
      if (kind === "hello") return;
      reloadSoon();
    }
  }

  function startSSE() {
    if (!window.EventSource) return false;
    try {
      var es = new EventSource("/api/events");
      es.addEventListener("hello", function (ev) {
        sseOk = true;
        try {
          var data = JSON.parse(ev.data);
          onToken(data.token, "hello");
        } catch (e) {}
      });
      es.addEventListener("catalog_changed", function (ev) {
        sseOk = true;
        try {
          var data = JSON.parse(ev.data);
          onToken(data.token, "change");
        } catch (e) {
          reloadSoon();
        }
      });
      es.addEventListener("portfolio_changed", function (ev) {
        sseOk = true;
        try {
          var data = JSON.parse(ev.data);
          onToken(data.token, "change");
        } catch (e) {
          reloadSoon();
        }
      });
      es.onerror = function () {
        /* browser will retry; poll remains as backup */
      };
      return true;
    } catch (e) {
      return false;
    }
  }

  function startPoll() {
    function tick() {
      fetch("/api/fingerprint", { credentials: "same-origin" })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (sseOk) return; /* SSE is healthy; skip poll reload */
          onToken(data.token, lastToken === null ? "hello" : "change");
        })
        .catch(function () {});
    }
    tick();
    setInterval(tick, 5000);
  }

  if (!wantsReload()) {
    return;
  }
  startSSE();
  startPoll();
})();
