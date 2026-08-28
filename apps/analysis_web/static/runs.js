/**
 * Instant filter/sort for the Research runs list.
 * Fetches /fragments/runs and swaps #runs-results; URL stays shareable.
 */
(function () {
  "use strict";

  var form = document.getElementById("runs-filters");
  var results = document.getElementById("runs-results");
  if (!form || !results) {
    return;
  }

  var timer = null;
  var abort = null;
  var DEBOUNCE_MS = 100;
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
      var current = new URLSearchParams(window.location.search);
      var exact = trim(current.get("ticker") || "");
      if (exact) {
        sp.set("ticker", exact);
      }
    } else {
      sp.delete("ticker");
    }
    return sp;
  }

  function shareablePath(sp) {
    var s = sp.toString();
    return s ? "/?" + s : "/";
  }

  function bindDone() {
    /* sort clicks are delegated on #runs-results */
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
        history.replaceState(null, "", shareablePath(sp));
        bindDone();
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
})();
