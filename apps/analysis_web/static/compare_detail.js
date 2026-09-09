/**
 * Patch compare job status in place. Reload only on terminal status.
 * Packet file table is server HTML (meta refresh or terminal reload).
 */
(function () {
  "use strict";

  var TERMINAL = { complete: 1, failed: 1, cancelled: 1, abandoned: 1 };
  var body = document.body;
  if (!body) {
    return;
  }
  var cid = body.getAttribute("data-compare-id");
  var status = body.getAttribute("data-compare-status");
  if (!cid || (status !== "running" && status !== "queued" && status !== "starting")) {
    return;
  }

  function patch(job) {
    var badge = document.getElementById("job-status");
    if (badge && job.status) {
      badge.textContent = job.status;
      badge.className = "badge status-" + job.status;
    }
    var hint = document.getElementById("job-resume-hint");
    if (hint) {
      hint.textContent = job.resume_hint || "";
    }
    var err = document.getElementById("job-error");
    if (err && job.error) {
      err.textContent = job.error;
      var row = document.getElementById("job-error-row");
      if (row) {
        row.hidden = false;
      }
    }
  }

  function tick() {
    fetch("/api/compares/" + encodeURIComponent(cid).replace(/%3A/gi, ":"), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (job) {
        if (!job || !job.status) {
          return;
        }
        if (TERMINAL[job.status]) {
          window.location.reload();
          return;
        }
        patch(job);
        status = job.status;
      })
      .catch(function () {});
  }

  window.setInterval(tick, 3000);
})();
