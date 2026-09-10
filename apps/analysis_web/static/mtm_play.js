/**
 * /portfolio Book: period Play of reconstructed MTM on #mtm-tbody.
 * Fetches GET /api/portfolio/mtm-path. Does not paint the heatmap.
 * Does not write #quote-status.
 */
(function () {
  "use strict";

  var root = document.getElementById("book-pl-mode");
  var mtmBody = document.getElementById("mtm-tbody");
  if (!root || !mtmBody) {
    return;
  }

  var playBtn = document.getElementById("book-pl-play");
  var pauseBtn = document.getElementById("book-pl-pause");
  var scrub = document.getElementById("book-pl-scrub");
  var dateEl = document.getElementById("book-pl-date");
  var statusEl = document.getElementById("book-pl-status");
  var mtmCaption = document.getElementById("mtm-caption");
  var liveMtmCaption = mtmCaption ? mtmCaption.textContent : "";
  var liveMtmHtml = mtmBody.innerHTML;

  var PATH_CAPTION =
    "Reconstructed MTM: Yahoo closes on lots plus IB fill cash, so buys and sells are not fake P/L. Statement FX. Not the IB MTM file. Gains at top, losses at bottom.";

  var STEP_MS = 350;
  var frames = [];
  var index = 0;
  var timer = null;

  function setStatus(msg) {
    if (statusEl) {
      statusEl.textContent = msg || "";
    }
  }

  function period() {
    return root.getAttribute("data-period") || "live";
  }

  function setPeriod(next) {
    root.setAttribute("data-period", next);
    var chips = root.querySelectorAll("[data-book-pl]");
    for (var i = 0; i < chips.length; i++) {
      var on = chips[i].getAttribute("data-book-pl") === next;
      chips[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  function isNum(v) {
    return typeof v === "number" && v === v && v !== Infinity && v !== -Infinity;
  }

  function fmtNum(n) {
    if (!isNum(n)) {
      return "—";
    }
    var abs = Math.abs(n);
    var digits = abs >= 1000 ? 2 : abs >= 1 ? 2 : 4;
    return n.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function stopTimer() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (playBtn) {
      playBtn.hidden = false;
    }
    if (pauseBtn) {
      pauseBtn.hidden = true;
    }
  }

  function makeRow(row) {
    var tr = document.createElement("tr");
    tr.setAttribute("data-name", row.name || "");
    var name = document.createElement("td");
    name.className = "mono";
    name.textContent = row.name || "";
    var cell = document.createElement("td");
    cell.className = "perf-bar-cell";
    var bar = document.createElement("span");
    bar.className = "perf-bar " + (row.sign || "zero");
    cell.appendChild(bar);
    var pl = document.createElement("td");
    pl.className = "num";
    tr.appendChild(name);
    tr.appendChild(cell);
    tr.appendChild(pl);
    return tr;
  }

  function updateRow(tr, row) {
    var bar = tr.querySelector(".perf-bar");
    var pl = tr.querySelector("td.num");
    if (bar) {
      bar.className = "perf-bar " + (row.sign || "zero");
      bar.style.width = (row.bar_pct || 0).toFixed(1) + "%";
    }
    if (pl) {
      pl.textContent = fmtNum(row.pl);
    }
  }

  function paintBars(bars) {
    var list = bars || [];
    while (mtmBody.children.length > list.length) {
      mtmBody.removeChild(mtmBody.lastChild);
    }
    for (var i = 0; i < list.length; i++) {
      var row = list[i];
      var tr = mtmBody.children[i];
      if (!tr) {
        tr = makeRow(row);
        mtmBody.appendChild(tr);
      }
      tr.setAttribute("data-name", row.name || "");
      var nameCell = tr.querySelector("td.mono");
      if (nameCell) {
        nameCell.textContent = row.name || "";
      }
      updateRow(tr, row);
    }
  }

  function showFrame(i) {
    if (!frames.length) {
      return;
    }
    index = Math.max(0, Math.min(frames.length - 1, i));
    var fr = frames[index];
    if (scrub) {
      scrub.value = String(index);
    }
    if (dateEl) {
      dateEl.textContent = fr.t || "";
    }
    paintBars(fr.bars || []);
  }

  function restoreLive() {
    stopTimer();
    frames = [];
    setPeriod("live");
    if (mtmCaption) {
      mtmCaption.textContent = liveMtmCaption;
    }
    mtmBody.innerHTML = liveMtmHtml;
    if (dateEl) {
      dateEl.textContent = "";
    }
    if (scrub) {
      scrub.disabled = true;
      scrub.value = "0";
      scrub.max = "0";
    }
    if (playBtn) {
      playBtn.disabled = true;
    }
    setStatus("");
  }

  function loadPeriod(next) {
    stopTimer();
    setPeriod(next);
    if (playBtn) {
      playBtn.disabled = true;
    }
    if (scrub) {
      scrub.disabled = true;
    }
    setStatus("Loading period marks…");
    fetch("/api/portfolio/mtm-path?period=" + encodeURIComponent(next), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (res) {
        return res.json().then(function (body) {
          return { ok: res.ok, body: body };
        });
      })
      .then(function (payload) {
        if (period() !== next) {
          return;
        }
        if (!payload.ok) {
          var detail =
            (payload.body && (payload.body.detail || payload.body.error)) ||
            "Period marks failed";
          setStatus(detail);
          frames = [];
          return;
        }
        var body = payload.body || {};
        frames = body.frames || [];
        if (mtmCaption) {
          mtmCaption.textContent = PATH_CAPTION;
        }
        if (!frames.length) {
          setStatus(body.error || "No daily closes in this period");
          mtmBody.textContent = "";
          return;
        }
        setStatus("");
        if (scrub) {
          scrub.disabled = false;
          scrub.min = "0";
          scrub.max = String(frames.length - 1);
        }
        if (playBtn) {
          playBtn.disabled = frames.length < 2;
        }
        showFrame(frames.length - 1);
      })
      .catch(function () {
        if (period() !== next) {
          return;
        }
        setStatus("Period marks failed");
        frames = [];
      });
  }

  function play() {
    if (frames.length < 2 || period() === "live") {
      return;
    }
    if (index >= frames.length - 1) {
      showFrame(0);
    }
    if (playBtn) {
      playBtn.hidden = true;
    }
    if (pauseBtn) {
      pauseBtn.hidden = false;
    }
    timer = setInterval(function () {
      if (index >= frames.length - 1) {
        stopTimer();
        return;
      }
      showFrame(index + 1);
    }, STEP_MS);
  }

  root.addEventListener("click", function (ev) {
    var btn = ev.target && ev.target.closest ? ev.target.closest("[data-book-pl]") : null;
    if (!btn || !root.contains(btn)) {
      return;
    }
    var next = btn.getAttribute("data-book-pl");
    if (!next || next === period()) {
      return;
    }
    if (next === "live") {
      restoreLive();
      return;
    }
    loadPeriod(next);
  });

  if (playBtn) {
    playBtn.addEventListener("click", play);
  }
  if (pauseBtn) {
    pauseBtn.addEventListener("click", stopTimer);
  }
  if (scrub) {
    scrub.addEventListener("input", function () {
      if (period() === "live") {
        return;
      }
      stopTimer();
      showFrame(Number(scrub.value) || 0);
    });
  }
})();
