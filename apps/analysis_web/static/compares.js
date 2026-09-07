/**
 * Two-session picker on the Research runs list.
 * Selection survives fragment table swaps.
 */
(function () {
  "use strict";

  var btn = document.getElementById("compare-btn");
  var hint = document.getElementById("compare-hint");
  var results = document.getElementById("runs-results");
  if (!btn || !results) {
    return;
  }

  var selected = {};
  var bar = document.getElementById("compare-bar");

  function keys() {
    return Object.keys(selected);
  }

  function updateBar() {
    var ids = keys();
    results.querySelectorAll("input.compare-pick").forEach(function (cb) {
      cb.checked = !!selected[cb.value];
    });
    if (bar) {
      bar.classList.toggle("is-on", ids.length > 0);
    }
    if (ids.length === 0) {
      btn.disabled = true;
      hint.textContent = "Select two sessions of the same ticker.";
      hint.className = "muted";
      return;
    }
    if (ids.length === 1) {
      btn.disabled = true;
      hint.textContent = "Select one more session of ticker " + selected[ids[0]].ticker + ".";
      hint.className = "muted";
      return;
    }
    if (ids.length > 2) {
      btn.disabled = true;
      hint.textContent = "Select exactly two sessions.";
      hint.className = "muted";
      return;
    }
    var t0 = selected[ids[0]];
    var t1 = selected[ids[1]];
    if (t0.ticker !== t1.ticker) {
      btn.disabled = true;
      hint.textContent = "Select two sessions of the same ticker (got " + t0.ticker + " and " + t1.ticker + ").";
      hint.className = "muted";
      return;
    }
    btn.disabled = false;
    hint.textContent = "Compare " + t0.ticker + ": " + t0.session + " vs " + t1.session;
    hint.className = "muted";
  }

  results.addEventListener("change", function (ev) {
    var cb = ev.target && ev.target.closest ? ev.target.closest("input.compare-pick") : null;
    if (!cb || !results.contains(cb)) {
      return;
    }
    if (cb.checked) {
      selected[cb.value] = {
        ticker: cb.getAttribute("data-ticker") || "",
        session: cb.getAttribute("data-session-key") || "",
      };
    } else {
      delete selected[cb.value];
    }
    updateBar();
  });

  document.addEventListener("runs-table-updated", function () {
    window.setTimeout(updateBar, 0);
  });

  btn.addEventListener("click", function () {
    var ids = keys();
    if (ids.length !== 2) {
      return;
    }
    if (selected[ids[0]].ticker !== selected[ids[1]].ticker) {
      return;
    }
    var ok = window.confirm(
      "Start a Grok valuation audit of these two sessions? It can take 15–40 minutes and does not edit either research folder."
    );
    if (!ok) {
      return;
    }
    btn.disabled = true;
    hint.textContent = "Starting compare…";
    fetch("/api/compares", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ run_id_a: ids[0], run_id_b: ids[1] }),
    })
      .then(function (r) {
        return r.json().then(function (body) {
          return { ok: r.ok, status: r.status, body: body };
        });
      })
      .then(function (res) {
        if (res.ok && res.body && res.body.compare_id) {
          window.location.href = "/compares/" + encodeURIComponent(res.body.compare_id).replace(/%3A/gi, ":");
          return;
        }
        var detail = (res.body && (res.body.detail || res.body.error)) || "Compare failed";
        hint.textContent = typeof detail === "string" ? detail : JSON.stringify(detail);
        hint.className = "muted";
        btn.disabled = false;
      })
      .catch(function () {
        hint.textContent = "Network error starting compare.";
        btn.disabled = false;
      });
  });

  updateBar();
})();
