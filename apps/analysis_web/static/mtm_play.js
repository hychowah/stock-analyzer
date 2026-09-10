/**
 * /portfolio Book: Live vs period mode and Play of reconstructed MTM.
 * Fetches GET /api/portfolio/mtm-path. Writes holding-pl-applied and
 * #mtm-tbody while mode is path. Does not write #quote-status.
 */
(function () {
  "use strict";

  var root = document.getElementById("book-pl-mode");
  if (!root) {
    return;
  }

  var playBtn = document.getElementById("book-pl-play");
  var pauseBtn = document.getElementById("book-pl-pause");
  var scrub = document.getElementById("book-pl-scrub");
  var dateEl = document.getElementById("book-pl-date");
  var statusEl = document.getElementById("book-pl-status");
  var heatCaption = document.getElementById("heatmap-caption");
  var mtmCaption = document.getElementById("mtm-caption");
  var mtmBody = document.getElementById("mtm-tbody");
  var liveHeatCaption = heatCaption ? heatCaption.textContent : "";
  var liveMtmCaption = mtmCaption ? mtmCaption.textContent : "";
  var liveMtmHtml = mtmBody ? mtmBody.innerHTML : "";

  var PATH_CAPTION =
    "Tile area is |P/L| since period start (Yahoo daily close × lots that day × statement FX). Stock % is the listing; NAV % is this holding’s P/L as % of starting NAV.";
  var PATH_MTM_CAPTION =
    "Reconstructed from Yahoo daily closes × lots as of each day, not the IB statement MTM file. Gains at top, losses at bottom.";

  var STEP_MS = 350;
  var frames = [];
  var index = 0;
  var timer = null;
  var period = "live";

  function setStatus(msg) {
    if (statusEl) {
      statusEl.textContent = msg || "";
    }
  }

  function mode() {
    return root.getAttribute("data-mode") || "live";
  }

  function setMode(next) {
    root.setAttribute("data-mode", next);
    var chips = root.querySelectorAll("[data-book-pl]");
    for (var i = 0; i < chips.length; i++) {
      var on = chips[i].getAttribute("data-book-pl") === next;
      chips[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
    document.dispatchEvent(new CustomEvent("book-pl-mode-changed"));
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

  function emitRows(rows) {
    document.dispatchEvent(
      new CustomEvent("holding-pl-applied", {
        detail: { rows: rows || [] },
      })
    );
  }

  function paintBars(bars) {
    if (!mtmBody) {
      return;
    }
    mtmBody.textContent = "";
    (bars || []).forEach(function (row) {
      var tr = document.createElement("tr");
      var name = document.createElement("td");
      name.className = "mono";
      name.textContent = row.name || "";
      var cell = document.createElement("td");
      cell.className = "perf-bar-cell";
      var bar = document.createElement("span");
      bar.className = "perf-bar " + (row.sign || "zero");
      bar.style.width = (row.bar_pct || 0).toFixed(1) + "%";
      cell.appendChild(bar);
      var pl = document.createElement("td");
      pl.className = "num";
      pl.textContent = fmtNum(row.pl);
      tr.appendChild(name);
      tr.appendChild(cell);
      tr.appendChild(pl);
      mtmBody.appendChild(tr);
    });
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
    emitRows(fr.rows || []);
    paintBars(fr.bars || []);
  }

  function restoreLive() {
    stopTimer();
    frames = [];
    period = "live";
    if (heatCaption) {
      heatCaption.textContent = liveHeatCaption;
    }
    if (mtmCaption) {
      mtmCaption.textContent = liveMtmCaption;
    }
    if (mtmBody) {
      mtmBody.innerHTML = liveMtmHtml;
    }
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
    setMode("live");
  }

  function loadPeriod(next) {
    stopTimer();
    period = next;
    setMode("path");
    emitRows([]);
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
        if (mode() !== "path" || period !== next) {
          return;
        }
        if (!payload.ok) {
          var detail =
            (payload.body && (payload.body.detail || payload.body.error)) ||
            "Period marks failed";
          setStatus(detail);
          frames = [];
          emitRows([]);
          return;
        }
        var body = payload.body || {};
        frames = body.frames || [];
        if (heatCaption) {
          heatCaption.textContent = PATH_CAPTION;
        }
        if (mtmCaption) {
          mtmCaption.textContent = PATH_MTM_CAPTION;
        }
        if (!frames.length) {
          setStatus(body.error || "No daily closes in this period");
          emitRows([]);
          if (mtmBody) {
            mtmBody.textContent = "";
          }
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
        if (mode() !== "path" || period !== next) {
          return;
        }
        setStatus("Period marks failed");
        frames = [];
        emitRows([]);
      });
  }

  function play() {
    if (frames.length < 2 || mode() !== "path") {
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
    if (!next || next === period) {
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
      if (mode() !== "path") {
        return;
      }
      stopTimer();
      showFrame(Number(scrub.value) || 0);
    });
  }
})();
