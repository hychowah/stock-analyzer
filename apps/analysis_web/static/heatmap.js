/**
 * /portfolio heatmap card. Size, time-base, and SVG.
 * Live rows come from holding-pl-applied. A window fetches
 * GET /api/portfolio/mtm-interval (one still). Does not write MTM bars.
 * Rows and heading commit together. Loading is a status line on the
 * current map, not an empty stage.
 * Fill screen is a CSS class on #heatmap-card; Escape exits.
 * Tile area is |pl|. Gainers and losers occupy separate regions.
 */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var PAD = 3;
  var GAP = 6;
  var CHG_CAP = 8;
  var MIN_LABEL_W = 52;
  var MIN_LABEL_H = 32;
  var MIN_CHG_H = 44;
  var MIN_NAV_H = 58;
  var LIVE_HEADING = "Day move";
  var RANGE_HEADING = "Holding influence";
  var LIVE_LABEL = "Portfolio day-move heatmap";
  var RANGE_LABEL = "Portfolio holding-influence heatmap";
  var RANGE_CAPTION =
    "Tile area is the |period change| of that holding (mark change plus IB fill cash). Stock % is the listing move over the window; NAV % is this holding’s P/L as % of NAV at the start of the window. Gainers left, losers right (stacked on a narrow screen).";

  var root = document.getElementById("heatmap");
  var svg = document.getElementById("heatmap-svg");
  var statusEl = document.getElementById("heatmap-status");
  var card = document.getElementById("heatmap-card");
  var fillBtn = document.getElementById("heatmap-fill");
  var rangeRoot = document.getElementById("heatmap-range");
  var heading = document.getElementById("heatmap-heading");
  var caption = document.getElementById("heatmap-caption");
  var fromEl = document.getElementById("heatmap-from");
  var toEl = document.getElementById("heatmap-to");
  var showBtn = document.getElementById("heatmap-show");
  var liveCaption = caption ? caption.textContent : "";
  if (!root || !svg) {
    return;
  }

  var lastRows = [];
  var lastLiveRows = [];
  var lastIntervalByUrl = Object.create(null);
  var hasPaint = false;
  var req = 0;

  function isRange() {
    return !!(card && card.getAttribute("data-heatmap-period") === "range");
  }

  function fillOn() {
    return !!(card && card.classList.contains("heatmap-fill"));
  }

  function setToken(period) {
    if (card) {
      card.setAttribute("data-heatmap-period", period);
    }
  }

  function setWindowPressed(name) {
    if (!rangeRoot) {
      return;
    }
    var chips = rangeRoot.querySelectorAll("[data-heatmap-window]");
    for (var i = 0; i < chips.length; i++) {
      var on = chips[i].getAttribute("data-heatmap-window") === name;
      chips[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  function setStatus(msg) {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = msg || "";
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

  function fmtSigned(n) {
    if (!isNum(n)) {
      return "—";
    }
    return (n > 0 ? "+" : "") + fmtNum(n);
  }

  function fmtPct(n) {
    if (!isNum(n)) {
      return "—";
    }
    return (n > 0 ? "+" : "") + n.toFixed(1) + "%";
  }

  function fmtNavPct(n) {
    if (!isNum(n)) {
      return "—";
    }
    var digits = Math.abs(n) >= 1 ? 1 : 2;
    return "NAV " + (n > 0 ? "+" : "") + n.toFixed(digits) + "%";
  }

  function sumAbs(items) {
    var s = 0;
    for (var i = 0; i < items.length; i++) {
      s += Math.abs(items[i].pl);
    }
    return s;
  }

  function lerp(a, b, t) {
    return Math.round(a + (b - a) * t);
  }

  function hexToRgb(hex) {
    return [
      parseInt(hex.slice(1, 3), 16),
      parseInt(hex.slice(3, 5), 16),
      parseInt(hex.slice(5, 7), 16),
    ];
  }

  function rgbToHex(rgb) {
    return (
      "#" +
      rgb
        .map(function (n) {
          var s = Math.max(0, Math.min(255, n)).toString(16);
          return s.length === 1 ? "0" + s : s;
        })
        .join("")
    );
  }

  function mixHex(a, b, t) {
    var aa = hexToRgb(a);
    var bb = hexToRgb(b);
    return rgbToHex([lerp(aa[0], bb[0], t), lerp(aa[1], bb[1], t), lerp(aa[2], bb[2], t)]);
  }

  function fillFor(sign, changePct) {
    var t = Math.min(1, Math.abs(isNum(changePct) ? changePct : 0) / CHG_CAP);
    if (sign === "up") {
      return mixHex("#dcfce7", "#16a34a", t);
    }
    return mixHex("#fee2e2", "#dc2626", t);
  }

  function inkFor(sign, changePct) {
    var t = Math.min(1, Math.abs(isNum(changePct) ? changePct : 0) / CHG_CAP);
    if (t >= 0.45) {
      return "#fff";
    }
    return sign === "up" ? "#14532d" : "#7f1d1d";
  }

  function worstRatio(row, side) {
    var s = 0;
    var maxA = 0;
    var minA = Infinity;
    for (var i = 0; i < row.length; i++) {
      var a = row[i].area;
      s += a;
      if (a > maxA) {
        maxA = a;
      }
      if (a < minA) {
        minA = a;
      }
    }
    var s2 = s * s;
    var w2 = side * side;
    if (s2 === 0 || w2 === 0 || minA === 0) {
      return Infinity;
    }
    return Math.max((w2 * maxA) / s2, s2 / (w2 * minA));
  }

  function squarify(nodes, x, y, w, h) {
    if (!nodes.length || w <= 0 || h <= 0) {
      return;
    }
    var total = 0;
    var i;
    for (i = 0; i < nodes.length; i++) {
      total += nodes[i].area;
    }
    if (total <= 0) {
      return;
    }
    var scale = (w * h) / total;
    for (i = 0; i < nodes.length; i++) {
      nodes[i].area *= scale;
    }
    place(nodes, x, y, w, h);
  }

  function place(items, x, y, w, h) {
    if (!items.length || w <= 0 || h <= 0) {
      return;
    }
    if (items.length === 1) {
      items[0].x = x;
      items[0].y = y;
      items[0].w = w;
      items[0].h = h;
      return;
    }
    var vertical = w >= h;
    var side = vertical ? h : w;
    var row = [items[0]];
    var i = 1;
    while (i < items.length) {
      var next = items[i];
      if (worstRatio(row, side) >= worstRatio(row.concat([next]), side)) {
        row.push(next);
        i += 1;
      } else {
        break;
      }
    }
    var rest = items.slice(i);
    var rowArea = 0;
    for (var j = 0; j < row.length; j++) {
      rowArea += row[j].area;
    }
    if (vertical) {
      var rw = h > 0 ? rowArea / h : 0;
      var cy = y;
      for (j = 0; j < row.length; j++) {
        var rh = rw > 0 ? row[j].area / rw : 0;
        row[j].x = x;
        row[j].y = cy;
        row[j].w = rw;
        row[j].h = rh;
        cy += rh;
      }
      place(rest, x + rw, y, Math.max(0, w - rw), h);
    } else {
      var rh2 = w > 0 ? rowArea / w : 0;
      var cx = x;
      for (j = 0; j < row.length; j++) {
        var rw2 = rh2 > 0 ? row[j].area / rh2 : 0;
        row[j].x = cx;
        row[j].y = y;
        row[j].w = rw2;
        row[j].h = rh2;
        cx += rw2;
      }
      place(rest, x, y + rh2, w, Math.max(0, h - rh2));
    }
  }

  function toNodes(items) {
    return items.map(function (it) {
      return {
        item: it,
        area: Math.abs(it.pl),
        x: 0,
        y: 0,
        w: 0,
        h: 0,
      };
    });
  }

  function byAbsDesc(a, b) {
    return Math.abs(b.pl) - Math.abs(a.pl);
  }

  function layoutHeatmap(rows, width, height) {
    var up = [];
    var down = [];
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      if (!r || !isNum(r.pl) || r.pl === 0) {
        continue;
      }
      if (r.pl > 0) {
        up.push(r);
      } else {
        down.push(r);
      }
    }
    up.sort(byAbsDesc);
    down.sort(byAbsDesc);
    var innerW = Math.max(0, width - PAD * 2);
    var innerH = Math.max(0, height - PAD * 2);
    var originX = PAD;
    var originY = PAD;
    if (!up.length && !down.length) {
      return [];
    }
    if (!down.length) {
      var onlyUp = toNodes(up);
      squarify(onlyUp, originX, originY, innerW, innerH);
      return onlyUp;
    }
    if (!up.length) {
      var onlyDown = toNodes(down);
      squarify(onlyDown, originX, originY, innerW, innerH);
      return onlyDown;
    }
    var sumUp = sumAbs(up);
    var sumDown = sumAbs(down);
    var total = sumUp + sumDown;
    // Page phone contract is max-width: 1100px, not stage aspect
    // (the stage stays landscape on a phone).
    var wide = !window.matchMedia("(max-width: 1100px)").matches;
    var upNodes = toNodes(up);
    var downNodes = toNodes(down);
    if (wide) {
      var upW = innerW * (sumUp / total);
      squarify(upNodes, originX, originY, Math.max(0, upW - GAP / 2), innerH);
      squarify(
        downNodes,
        originX + upW + GAP / 2,
        originY,
        Math.max(0, innerW - upW - GAP / 2),
        innerH
      );
    } else {
      var upH = innerH * (sumUp / total);
      squarify(upNodes, originX, originY, innerW, Math.max(0, upH - GAP / 2));
      squarify(
        downNodes,
        originX,
        originY + upH + GAP / 2,
        innerW,
        Math.max(0, innerH - upH - GAP / 2)
      );
    }
    return upNodes.concat(downNodes);
  }

  function svgEl(name, attrs) {
    var el = document.createElementNS(NS, name);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        el.setAttribute(k, String(attrs[k]));
      });
    }
    return el;
  }

  function clearSvg() {
    while (svg.firstChild) {
      svg.removeChild(svg.firstChild);
    }
  }

  function paint(rows) {
    var box = root.getBoundingClientRect();
    var width = Math.max(0, box.width);
    var height = Math.max(0, box.height);
    if (width < 8 || height < 8) {
      return;
    }
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("width", String(width));
    svg.setAttribute("height", String(height));
    var nodes = layoutHeatmap(rows || [], width, height);
    clearSvg();
    hasPaint = true;
    if (!nodes.length) {
      if (!isRange()) {
        setStatus("No day moves yet");
      }
      return;
    }
    if (!isRange()) {
      setStatus("");
    }
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var it = n.item;
      var sign = it.pl > 0 ? "up" : "down";
      var g = svgEl("g", {
        class: "heatmap-tile heatmap-" + sign,
        "data-sign": sign,
        "data-ib-symbol": it.ib_symbol || "",
        "data-pl": String(it.pl),
      });
      var titleBits = [
        it.ib_symbol || "",
        fmtPct(it.change_pct),
        fmtNavPct(it.contrib_pct),
        fmtSigned(it.pl),
      ];
      var title = svgEl("title");
      title.textContent = titleBits.join(" · ");
      g.appendChild(title);
      g.appendChild(
        svgEl("rect", {
          x: n.x,
          y: n.y,
          width: Math.max(0, n.w),
          height: Math.max(0, n.h),
          fill: fillFor(sign, it.change_pct),
          class: "heatmap-rect",
        })
      );
      if (n.w >= MIN_LABEL_W && n.h >= MIN_LABEL_H) {
        var ink = inkFor(sign, it.change_pct);
        var tx = n.x + 6;
        var name = svgEl("text", {
          x: tx,
          y: n.y + 16,
          fill: ink,
          class: "heatmap-label",
        });
        name.textContent = it.ib_symbol || "";
        g.appendChild(name);
        if (n.h >= MIN_CHG_H) {
          var chg = svgEl("text", {
            x: tx,
            y: n.y + 32,
            fill: ink,
            class: "heatmap-chg",
          });
          chg.textContent = fmtPct(it.change_pct);
          g.appendChild(chg);
        }
        if (n.h >= MIN_NAV_H && isNum(it.contrib_pct)) {
          var nav = svgEl("text", {
            x: tx,
            y: n.y + 46,
            fill: ink,
            class: "heatmap-nav",
          });
          nav.textContent = fmtNavPct(it.contrib_pct);
          g.appendChild(nav);
        }
      }
      svg.appendChild(g);
    }
  }

  function showRows(rows) {
    lastRows = rows || [];
    paint(lastRows);
  }

  function onLiveApplied(ev) {
    lastLiveRows = (ev && ev.detail && ev.detail.rows) || [];
    if (isRange()) {
      return;
    }
    showRows(lastLiveRows);
  }

  function restoreLive(statusMsg) {
    req += 1;
    setToken("live");
    if (heading) {
      heading.textContent = LIVE_HEADING;
    }
    if (caption) {
      caption.textContent = liveCaption;
    }
    svg.setAttribute("aria-label", LIVE_LABEL);
    setWindowPressed("live");
    showRows(lastLiveRows);
    if (statusMsg) {
      setStatus(statusMsg);
    }
  }

  function rowMap(rows) {
    return (rows || []).map(function (r) {
      return {
        ib_symbol: r && r.ib_symbol,
        pl: r && r.pl,
        change_pct: r && r.change_pct,
        contrib_pct: r && r.contrib_pct,
      };
    });
  }

  function applyRangeChrome(body) {
    setToken("range");
    if (heading) {
      heading.textContent = RANGE_HEADING;
    }
    if (caption) {
      var text = RANGE_CAPTION;
      if (body && body.start && body.end) {
        text += " Window " + body.start + " to " + body.end + ".";
      }
      caption.textContent = text;
    }
    svg.setAttribute("aria-label", RANGE_LABEL);
    if (body && body.start && fromEl) {
      fromEl.value = body.start;
    }
    if (body && body.end && toEl) {
      toEl.value = body.end;
    }
  }

  function applyBody(body, windowName) {
    applyRangeChrome(body);
    setWindowPressed(windowName);
    var rows = (body && body.rows) || [];
    if (!rows.length) {
      showRows([]);
      setStatus((body && body.error) || "No daily closes in this period");
      return;
    }
    showRows(rowMap(rows));
    setStatus((body && body.error) || "");
  }

  function loadUrl(url, windowName) {
    var cached = lastIntervalByUrl[url];
    if (cached) {
      req += 1;
      applyBody(cached, windowName);
      return;
    }
    var my = ++req;
    setStatus("Loading period marks…");
    fetch(url, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (res) {
        return res.json().then(function (body) {
          return { ok: res.ok, body: body };
        });
      })
      .then(function (payload) {
        if (my !== req) {
          return;
        }
        if (!payload.ok) {
          var detail =
            (payload.body && (payload.body.detail || payload.body.error)) ||
            "Period marks failed";
          restoreLive(detail);
          return;
        }
        var body = payload.body || {};
        if ((body.rows || []).length) {
          lastIntervalByUrl[url] = body;
        }
        applyBody(body, windowName);
      })
      .catch(function () {
        if (my !== req) {
          return;
        }
        restoreLive("Period marks failed");
      });
  }

  function setFill(on) {
    if (!card) {
      return;
    }
    if (on) {
      card.classList.add("heatmap-fill");
      document.body.classList.add("heatmap-fill-open");
    } else {
      card.classList.remove("heatmap-fill");
      document.body.classList.remove("heatmap-fill-open");
    }
    if (fillBtn) {
      fillBtn.setAttribute("aria-pressed", on ? "true" : "false");
      fillBtn.textContent = on ? "Exit" : "Fill screen";
    }
    if (hasPaint || lastRows.length) {
      paint(lastRows);
    }
  }

  document.addEventListener("holding-pl-applied", onLiveApplied);
  if (fillBtn) {
    fillBtn.addEventListener("click", function () {
      setFill(!fillOn());
    });
  }
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape" || !fillOn()) {
      return;
    }
    ev.preventDefault();
    setFill(false);
  });
  if (rangeRoot) {
    var pf = card ? card.getAttribute("data-period-from") || "" : "";
    var pt = card ? card.getAttribute("data-period-to") || "" : "";
    if (fromEl && pf) {
      fromEl.title = "Statement from " + pf;
    }
    if (toEl && pt) {
      toEl.title = "Statement to " + pt;
    }
    rangeRoot.addEventListener("click", function (ev) {
      var btn =
        ev.target && ev.target.closest
          ? ev.target.closest("[data-heatmap-window]")
          : null;
      if (!btn || !rangeRoot.contains(btn)) {
        return;
      }
      var next = btn.getAttribute("data-heatmap-window");
      if (!next) {
        return;
      }
      if (next === "live") {
        restoreLive("");
        return;
      }
      loadUrl(
        "/api/portfolio/mtm-interval?period=" + encodeURIComponent(next),
        next
      );
    });
  }
  if (showBtn) {
    showBtn.addEventListener("click", function () {
      var a = fromEl && fromEl.value;
      var b = toEl && toEl.value;
      if (!a || !b) {
        setStatus("Choose from and to dates");
        return;
      }
      if (a > b) {
        setStatus("From must be on or before to");
        return;
      }
      loadUrl(
        "/api/portfolio/mtm-interval?start=" +
          encodeURIComponent(a) +
          "&end=" +
          encodeURIComponent(b),
        "custom"
      );
    });
  }
  if (typeof ResizeObserver === "function") {
    new ResizeObserver(function () {
      if (hasPaint || lastRows.length) {
        paint(lastRows);
      }
    }).observe(root);
  }
  window.addEventListener("resize", function () {
    if (hasPaint || lastRows.length) {
      paint(lastRows);
    }
  });
  if (typeof window.matchMedia === "function") {
    var mq = window.matchMedia("(max-width: 1100px)");
    var onBreak = function () {
      if (hasPaint || lastRows.length) {
        paint(lastRows);
      }
    };
    if (typeof mq.addEventListener === "function") {
      mq.addEventListener("change", onBreak);
    } else if (typeof mq.addListener === "function") {
      mq.addListener(onBreak);
    }
  }
})();
