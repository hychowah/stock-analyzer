/**
 * Runs list working query.
 *
 * Last non-empty sort/filter is remembered so header Runs and run-detail
 * "← Runs" return to it. The address bar is the working set while you are
 * on a query URL. Empty `/` is the default list (storage is not replayed).
 * Reset is the only clear. Links are rewritten from the stored query.
 * `ticker` is URL-only (no form field). Default limit 50 is omitted.
 * localStorage quota / private-mode failures are ignored.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "analysis_web.runs.query";
  var DEFAULT_LIMIT = "50";
  var QUERY_KEYS = [
    "ticker",
    "ticker_prefix",
    "sector",
    "region",
    "experiment_id",
    "tech_signal",
    "harness_version",
    "session_date_from",
    "session_date_to",
    "mos_min",
    "mos_max",
    "price_min",
    "price_max",
    "fv_base_min",
    "fv_base_max",
    "sort",
    "dir",
    "audit_verdict",
    "limit",
  ];

  var NUMERIC_SORT = {
    session_date: true,
    asof_price: true,
    fv_base: true,
    margin_of_safety_pct: true,
    harness_version: true,
  };

  function trim(value) {
    return String(value == null ? "" : value).trim();
  }

  function readStored() {
    try {
      return localStorage.getItem(STORAGE_KEY) || "";
    } catch (err) {
      return "";
    }
  }

  function writeStored(qs) {
    try {
      if (qs) {
        localStorage.setItem(STORAGE_KEY, qs);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch (err) {
      /* quota / private mode: keep the list working */
    }
  }

  function canonicalize(sp) {
    var out = new URLSearchParams();
    var i;
    for (i = 0; i < QUERY_KEYS.length; i++) {
      var key = QUERY_KEYS[i];
      var v = trim(sp.get(key));
      if (!v) {
        continue;
      }
      if (key === "limit" && v === DEFAULT_LIMIT) {
        continue;
      }
      out.set(key, v);
    }
    return out;
  }

  function pathFromParams(sp) {
    var s = canonicalize(sp).toString();
    return s ? "/?" + s : "/";
  }

  function pathFromStored() {
    var raw = readStored();
    if (!raw) {
      return "/";
    }
    return pathFromParams(new URLSearchParams(raw));
  }

  function syncLinks() {
    var href = pathFromStored();
    var nav = document.getElementById("nav-runs");
    if (nav) {
      nav.setAttribute("href", href);
    }
    document.querySelectorAll("a.js-runs-back").forEach(function (a) {
      a.setAttribute("href", href);
    });
  }

  function remember(sp) {
    var s = canonicalize(sp).toString();
    if (s) {
      writeStored(s);
    }
    syncLinks();
  }

  function forget() {
    writeStored("");
    syncLinks();
  }

  syncLinks();

  function bindList() {
    syncLinks();
    var form = document.getElementById("runs-filters");
    var results = document.getElementById("runs-results");
    if (!form || !results) {
      return;
    }

    var timer = null;
    var abort = null;
    var DEBOUNCE_MS = 100;

    function paramsFromForm() {
      var fd = new FormData(form);
      var sp = new URLSearchParams();
      fd.forEach(function (value, key) {
        var v = trim(value);
        if (!v) {
          return;
        }
        sp.set(key, v);
      });
      if (!trim(sp.get("ticker_prefix") || "")) {
        var exact = trim(new URLSearchParams(window.location.search).get("ticker") || "");
        if (exact) {
          sp.set("ticker", exact);
        }
      } else {
        sp.delete("ticker");
      }
      return canonicalize(sp);
    }

    function fetchTable() {
      var sp = paramsFromForm();
      if (abort) {
        abort.abort();
      }
      abort = new AbortController();
      var qs = sp.toString();
      var url = "/fragments/runs" + (qs ? "?" + qs : "");
      fetch(url, {
        credentials: "same-origin",
        signal: abort.signal,
        headers: { Accept: "text/html" },
      })
        .then(function (r) {
          return r.text().then(function (html) {
            return { html: html, status: r.status };
          });
        })
        .then(function (payload) {
          results.innerHTML = payload.html;
          if (form.classList) {
            form.classList.toggle("is-abort", payload.status === 404);
          }
          history.replaceState(null, "", pathFromParams(sp));
          remember(sp);
          document.dispatchEvent(new CustomEvent("quotes-refresh"));
        })
        .catch(function (err) {
          if (err && err.name === "AbortError") {
            return;
          }
        });
    }

    function schedule() {
      if (timer) {
        clearTimeout(timer);
      }
      timer = setTimeout(fetchTable, DEBOUNCE_MS);
    }

    function clearForm() {
      form.querySelectorAll("[name]").forEach(function (el) {
        if (el.name === "limit") {
          el.value = DEFAULT_LIMIT;
        } else {
          el.value = "";
        }
      });
    }

    var urlQuery = canonicalize(new URLSearchParams(window.location.search));
    if (urlQuery.toString()) {
      remember(urlQuery);
    }

    results.addEventListener("click", function (ev) {
      var verLink = ev.target && ev.target.closest ? ev.target.closest("a.version-filter") : null;
      if (verLink && results.contains(verLink)) {
        ev.preventDefault();
        var sel = form.querySelector('[name="harness_version"]');
        if (sel) {
          sel.value = verLink.getAttribute("data-version") || "";
        }
        fetchTable();
        return;
      }
      var a = ev.target && ev.target.closest ? ev.target.closest("a.sort") : null;
      if (!a || !results.contains(a)) {
        return;
      }
      ev.preventDefault();
      var col = a.getAttribute("data-sort");
      if (!col) {
        return;
      }
      var sortInput = form.querySelector('[name="sort"]');
      var dirInput = form.querySelector('[name="dir"]');
      if (!sortInput || !dirInput) {
        return;
      }
      var curSort = sortInput.value;
      var curDir = dirInput.value || "asc";
      if (curSort === col) {
        dirInput.value = curDir === "desc" ? "asc" : "desc";
      } else {
        sortInput.value = col;
        dirInput.value = NUMERIC_SORT[col] ? "desc" : "asc";
      }
      fetchTable();
    });

    form.addEventListener("input", function (ev) {
      var t = ev.target;
      if (!t || t.tagName !== "INPUT" || t.type === "hidden") {
        return;
      }
      schedule();
    });

    form.addEventListener("change", function (ev) {
      var t = ev.target;
      if (!t) {
        return;
      }
      if (t.tagName === "SELECT" || t.name === "limit" || t.type === "date") {
        if (timer) {
          clearTimeout(timer);
        }
        fetchTable();
      }
    });

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (timer) {
        clearTimeout(timer);
      }
      fetchTable();
    });

    document.addEventListener("catalog-changed", function () {
      fetchTable();
    });

    var reset = document.getElementById("runs-reset");
    if (reset) {
      reset.addEventListener("click", function (ev) {
        forget();
        if (ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) {
          return;
        }
        ev.preventDefault();
        if (timer) {
          clearTimeout(timer);
        }
        clearForm();
        fetchTable();
      });
      reset.addEventListener("auxclick", function (ev) {
        if (ev.button === 1) {
          forget();
        }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindList);
  } else {
    bindList();
  }
})();
