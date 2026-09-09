/**
 * Patch analyze job status in place. Reload only on terminal status.
 * Artifact list is server HTML (meta refresh or terminal reload).
 */
(function () {
  "use strict";

  var TERMINAL = { complete: 1, failed: 1, cancelled: 1, abandoned: 1 };
  var body = document.body;
  if (!body) {
    return;
  }
  var cid = body.getAttribute("data-analyze-id");
  var status = body.getAttribute("data-analyze-status");
  if (!cid || (status !== "running" && status !== "queued" && status !== "starting")) {
    return;
  }

  function setText(id, text, hiddenIfEmpty) {
    var el = document.getElementById(id);
    if (!el) {
      return;
    }
    el.textContent = text || "";
    if (hiddenIfEmpty) {
      el.hidden = !text;
    }
  }

  function hidePhaseWhenHint(hint) {
    var wrap = document.getElementById("job-phase-wrap");
    if (wrap) {
      wrap.hidden = !!(hint || "").trim();
    }
  }

  function patch(job) {
    var badge = document.getElementById("job-status");
    if (badge && job.status) {
      badge.textContent = job.status;
      badge.className = "badge status-" + job.status;
    }
    setText("job-phase", job.phase_current || "—");
    setText("job-resume-hint", job.resume_hint || "");
    hidePhaseWhenHint(job.resume_hint);
    var err = document.getElementById("job-error");
    if (err) {
      if (job.error) {
        err.hidden = false;
        err.textContent = job.error;
        var loud =
          job.status === "failed" ||
          job.status === "cancelled" ||
          job.status === "abandoned" ||
          job.abandoned;
        err.className = loud ? "err" : "muted";
      }
    }
  }

  function tick() {
    fetch("/api/analyze/" + encodeURIComponent(cid).replace(/%3A/gi, ":"), {
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

  window.setInterval(tick, 5000);
})();
