/**
 * Poll analyze job status and reload when it leaves running/queued.
 */
(function () {
  "use strict";

  var body = document.body;
  if (!body) {
    return;
  }
  var cid = body.getAttribute("data-analyze-id");
  var status = body.getAttribute("data-analyze-status");
  if (!cid || (status !== "running" && status !== "queued")) {
    return;
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
        if (job.status !== status) {
          window.location.reload();
        }
      })
      .catch(function () {});
  }

  window.setInterval(tick, 5000);
})();
