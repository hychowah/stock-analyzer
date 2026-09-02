/**
 * Run-detail price chart: Yahoo daily close + catalog bear/base/bull overlay.
 * Range buttons refetch GET /api/price-history. Overlay JSON is catalog-only.
 */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";

  var root = document.getElementById("price-chart");
  if (!root) {
    return;
  }

  var svg = document.getElementById("price-chart-svg");
  var tooltip = document.getElementById("price-chart-tooltip");
  var readout = document.getElementById("price-chart-readout");
  var statusEl = document.getElementById("price-chart-status");
  var overlay = readOverlay();
  var symbol = String(root.getAttribute("data-symbol") || "").trim().toUpperCase();
  var state = {
    range: "",
    bars: [],
    hover: -1,
    width: 0,
    height: 0,
    loadGen: 0,
  };

  function readOverlay() {
    var el = document.getElementById("price-chart-overlay");
    if (!el) {
      return {};
    }
    try {
      return JSON.parse(el.textContent || "{}") || {};
    } catch (e) {
      return {};
    }
  }

  function setStatus(msg) {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = msg || "";
  }

  function fmtNum(n, digits) {
    if (n == null || n !== n) {
      return "—";
    }
    var d = digits == null ? (Math.abs(n) >= 1 ? 2 : 4) : digits;
    return n.toLocaleString(undefined, {
      minimumFractionDigits: d,
      maximumFractionDigits: d,
    });
  }

  function isNum(v) {
    return typeof v === "number" && v === v;
  }

  function parseDay(s) {
    if (!s) {
      return NaN;
    }
    var t = Date.parse(String(s).slice(0, 10) + "T00:00:00Z");
    return t;
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

  function yTicks(min, max, n) {
    var span = max - min;
    if (!(span > 0)) {
      return [min];
    }
    var raw = span / (n || 4);
    var pow = Math.pow(10, Math.floor(Math.log10(raw)));
    var err = raw / pow;
    var step = pow;
    if (err >= 5) {
      step = 5 * pow;
    } else if (err >= 2) {
      step = 2 * pow;
    }
    var start = Math.ceil(min / step) * step;
    var out = [];
    for (var v = start; v <= max + step * 0.001; v += step) {
      out.push(v);
    }
    return out;
  }

  function domainY(bars) {
    // Price is the scale. Base and as-of are anchors. Bear/bull/weighted clip.
    var vals = [];
    bars.forEach(function (b) {
      if (isNum(b.close)) {
        vals.push(b.close);
      }
    });
    ["fv_base", "asof_price"].forEach(function (k) {
      if (isNum(overlay[k])) {
        vals.push(overlay[k]);
      }
    });
    if (!vals.length) {
      return { min: 0, max: 1 };
    }
    var lo = Math.min.apply(null, vals);
    var hi = Math.max.apply(null, vals);
    if (hi === lo) {
      lo -= Math.abs(lo) * 0.05 || 1;
      hi += Math.abs(hi) * 0.05 || 1;
    }
    var pad = (hi - lo) * 0.08;
    return { min: lo - pad, max: hi + pad };
  }

  function layout() {
    var rect = svg.getBoundingClientRect();
    var width = Math.max(320, Math.floor(rect.width) || root.clientWidth || 640);
    var height = Math.max(200, Math.floor(rect.height) || 280);
    state.width = width;
    state.height = height;
    var pad = { l: 56, r: 14, t: 14, b: 28 };
    var innerW = Math.max(10, width - pad.l - pad.r);
    var innerH = Math.max(10, height - pad.t - pad.b);
    var bars = state.bars;
    var t0;
    var t1;
    if (bars.length) {
      t0 = parseDay(bars[0].t);
      t1 = parseDay(bars[bars.length - 1].t);
    } else {
      var asof = parseDay(overlay.asof_date);
      var now = Date.now();
      t0 = isNaN(asof) ? now - 365 * 86400000 : Math.min(asof, now) - 30 * 86400000;
      t1 = now;
    }
    if (!(t1 > t0)) {
      t1 = t0 + 86400000;
    }
    var ydom = domainY(bars);
    function x(ts) {
      var t = typeof ts === "number" ? ts : parseDay(ts);
      if (isNaN(t)) {
        return pad.l;
      }
      return pad.l + ((t - t0) / (t1 - t0)) * innerW;
    }
    function y(p) {
      return pad.t + (1 - (p - ydom.min) / (ydom.max - ydom.min)) * innerH;
    }
    return { pad: pad, innerW: innerW, innerH: innerH, x: x, y: y, t0: t0, t1: t1, ydom: ydom };
  }

  function nearestBar(lay, clientX) {
    var rect = svg.getBoundingClientRect();
    var px = ((clientX - rect.left) / rect.width) * state.width;
    var bars = state.bars;
    if (!bars.length) {
      return -1;
    }
    var lo = 0;
    var hi = bars.length - 1;
    while (lo < hi) {
      var mid = (lo + hi) >> 1;
      if (lay.x(bars[mid].t) < px) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }
    var i = lo;
    if (i > 0 && Math.abs(lay.x(bars[i - 1].t) - px) < Math.abs(lay.x(bars[i].t) - px)) {
      i -= 1;
    }
    return i;
  }

  function fillReadout(bar) {
    if (!readout) {
      return;
    }
    var close = bar && isNum(bar.close) ? bar.close : null;
    var date = bar && bar.t ? bar.t : "";
    var bits = [];
    if (date) {
      bits.push(date);
    }
    bits.push("Close " + fmtNum(close));
    if (isNum(overlay.fv_bear)) {
      bits.push("Bear " + fmtNum(overlay.fv_bear));
    }
    if (isNum(overlay.fv_base)) {
      bits.push("Base " + fmtNum(overlay.fv_base));
    }
    if (isNum(overlay.fv_bull)) {
      bits.push("Bull " + fmtNum(overlay.fv_bull));
    }
    if (overlay.currency) {
      bits.push(overlay.currency);
    }
    readout.textContent = bits.join("  ·  ");
  }

  function showTooltip(lay, i, evt) {
    if (!tooltip || i < 0 || !state.bars[i]) {
      if (tooltip) {
        tooltip.hidden = true;
      }
      return;
    }
    var bar = state.bars[i];
    var lines = [bar.t, "Close  " + fmtNum(bar.close)];
    if (isNum(overlay.fv_base)) {
      lines.push("Base   " + fmtNum(overlay.fv_base));
    }
    tooltip.textContent = lines.join("\n");
    tooltip.hidden = false;
    var stage = svg.parentNode;
    var sr = stage.getBoundingClientRect();
    var left = evt.clientX - sr.left + 12;
    var top = evt.clientY - sr.top + 12;
    if (left + tooltip.offsetWidth > sr.width - 8) {
      left = evt.clientX - sr.left - tooltip.offsetWidth - 12;
    }
    if (top + tooltip.offsetHeight > sr.height - 8) {
      top = evt.clientY - sr.top - tooltip.offsetHeight - 12;
    }
    tooltip.style.left = Math.max(8, left) + "px";
    tooltip.style.top = Math.max(8, top) + "px";
  }

  function drawHover(lay, g, i) {
    while (g.firstChild) {
      g.removeChild(g.firstChild);
    }
    if (i < 0 || !state.bars[i]) {
      return;
    }
    var bar = state.bars[i];
    var x = lay.x(bar.t);
    g.appendChild(
      svgEl("line", {
        x1: x,
        x2: x,
        y1: lay.pad.t,
        y2: lay.pad.t + lay.innerH,
        class: "chart-hover-x",
      })
    );
    g.appendChild(
      svgEl("line", {
        x1: lay.pad.l,
        x2: lay.pad.l + lay.innerW,
        y1: lay.y(bar.close),
        y2: lay.y(bar.close),
        class: "chart-hover-y",
      })
    );
    g.appendChild(
      svgEl("circle", {
        cx: x,
        cy: lay.y(bar.close),
        r: 3.5,
        class: "chart-hover-dot",
      })
    );
  }

  function levelLine(lay, plot, value, cls, label) {
    if (!isNum(value)) {
      return;
    }
    var y = lay.y(value);
    plot.appendChild(
      svgEl("line", {
        x1: lay.pad.l,
        x2: lay.pad.l + lay.innerW,
        y1: y,
        y2: y,
        class: cls,
      })
    );
    if (label) {
      plot.appendChild(
        svgEl("text", {
          x: lay.pad.l + lay.innerW - 2,
          y: y - 3,
          class: cls + "-label",
          "text-anchor": "end",
        })
      ).textContent = label;
    }
  }

  function rangeBar(lay, plot, date, bear, base, bull, cls, href, title) {
    var ts = parseDay(date);
    if (isNaN(ts) || ts < lay.t0 || ts > lay.t1) {
      return;
    }
    var x = lay.x(ts);
    var g = svgEl("g", { class: cls, "data-href": href || "" });
    if (isNum(bear) && isNum(bull)) {
      g.appendChild(
        svgEl("line", {
          x1: x,
          x2: x,
          y1: lay.y(bear),
          y2: lay.y(bull),
        })
      );
    }
    if (isNum(base)) {
      g.appendChild(svgEl("circle", { cx: x, cy: lay.y(base), r: href ? 4.5 : 5 }));
    }
    if (title) {
      var t = svgEl("title");
      t.textContent = title;
      g.appendChild(t);
    }
    if (href) {
      g.style.cursor = "pointer";
      g.addEventListener("click", function () {
        window.location.href = href;
      });
    }
    plot.appendChild(g);
  }

  function draw() {
    while (svg.firstChild) {
      svg.removeChild(svg.firstChild);
    }
    var lay = layout();
    svg.setAttribute("viewBox", "0 0 " + state.width + " " + state.height);
    svg.setAttribute("preserveAspectRatio", "none");

    var clip = svgEl("clipPath", { id: "price-chart-clip" });
    clip.appendChild(
      svgEl("rect", {
        x: lay.pad.l,
        y: lay.pad.t,
        width: lay.innerW,
        height: lay.innerH,
      })
    );
    var defs = svgEl("defs");
    defs.appendChild(clip);
    svg.appendChild(defs);

    var grid = svgEl("g", { class: "chart-grid" });
    yTicks(lay.ydom.min, lay.ydom.max, 4).forEach(function (v) {
      var y = lay.y(v);
      grid.appendChild(
        svgEl("line", {
          x1: lay.pad.l,
          x2: lay.pad.l + lay.innerW,
          y1: y,
          y2: y,
        })
      );
      var lab = svgEl("text", {
        x: lay.pad.l - 6,
        y: y + 3,
        "text-anchor": "end",
      });
      lab.textContent = fmtNum(v, v >= 100 ? 0 : 2);
      grid.appendChild(lab);
    });
    var xCount = 4;
    for (var i = 0; i <= xCount; i++) {
      var ts = lay.t0 + ((lay.t1 - lay.t0) * i) / xCount;
      var x = lay.x(ts);
      var d = new Date(ts);
      var lab = svgEl("text", {
        x: x,
        y: lay.pad.t + lay.innerH + 16,
        "text-anchor": i === 0 ? "start" : i === xCount ? "end" : "middle",
      });
      lab.textContent =
        d.getUTCFullYear() +
        "-" +
        String(d.getUTCMonth() + 1).padStart(2, "0") +
        "-" +
        String(d.getUTCDate()).padStart(2, "0");
      grid.appendChild(lab);
    }
    svg.appendChild(grid);

    var plot = svgEl("g", { "clip-path": "url(#price-chart-clip)" });
    if (isNum(overlay.fv_bear) && isNum(overlay.fv_bull)) {
      var yb = lay.y(overlay.fv_bull);
      var ye = lay.y(overlay.fv_bear);
      var top = Math.min(yb, ye);
      var h = Math.abs(ye - yb);
      plot.appendChild(
        svgEl("rect", {
          x: lay.pad.l,
          y: top,
          width: lay.innerW,
          height: h,
          class: "chart-band",
        })
      );
    }
    levelLine(lay, plot, overlay.fv_bear, "chart-bear", "bear");
    levelLine(lay, plot, overlay.fv_base, "chart-base", "base");
    levelLine(lay, plot, overlay.fv_bull, "chart-bull", "bull");
    levelLine(lay, plot, overlay.fv_weighted, "chart-weighted", "wtd");

    var bars = state.bars;
    if (bars.length > 1) {
      var d = "";
      for (var j = 0; j < bars.length; j++) {
        d += (j === 0 ? "M" : "L") + lay.x(bars[j].t) + " " + lay.y(bars[j].close) + " ";
      }
      plot.appendChild(svgEl("path", { d: d, class: "chart-price" }));
    } else if (bars.length === 1) {
      plot.appendChild(
        svgEl("circle", {
          cx: lay.x(bars[0].t),
          cy: lay.y(bars[0].close),
          r: 3,
          class: "chart-price-dot",
        })
      );
    }

    var asofTs = parseDay(overlay.asof_date);
    if (!isNaN(asofTs) && asofTs >= lay.t0 && asofTs <= lay.t1) {
      var ax = lay.x(asofTs);
      plot.appendChild(
        svgEl("line", {
          x1: ax,
          x2: ax,
          y1: lay.pad.t,
          y2: lay.pad.t + lay.innerH,
          class: "chart-asof",
        })
      );
    }
    rangeBar(
      lay,
      plot,
      overlay.asof_date,
      overlay.fv_bear,
      overlay.fv_base,
      overlay.fv_bull,
      "chart-this-run",
      "",
      (overlay.session_key || "this session") + " base " + fmtNum(overlay.fv_base)
    );

    (overlay.siblings || []).forEach(function (s) {
      if (!s) {
        return;
      }
      rangeBar(
        lay,
        plot,
        s.asof_date,
        s.fv_bear,
        s.fv_base,
        s.fv_bull,
        "chart-sibling",
        s.run_id ? "/runs/" + s.run_id : "",
        (s.session_key || s.run_id || "session") + " base " + fmtNum(s.fv_base)
      );
    });

    svg.appendChild(plot);
    var hover = svgEl("g", { class: "chart-hover", "clip-path": "url(#price-chart-clip)" });
    svg.appendChild(hover);
    svg._hover = hover;
    svg._lay = lay;

    var last = bars.length ? bars[bars.length - 1] : null;
    fillReadout(last);
  }

  function onMove(evt) {
    if (!svg._lay) {
      return;
    }
    var i = nearestBar(svg._lay, evt.clientX);
    state.hover = i;
    drawHover(svg._lay, svg._hover, i);
    if (i >= 0) {
      fillReadout(state.bars[i]);
      showTooltip(svg._lay, i, evt);
    }
  }

  function onLeave() {
    state.hover = -1;
    if (svg._lay && svg._hover) {
      drawHover(svg._lay, svg._hover, -1);
    }
    if (tooltip) {
      tooltip.hidden = true;
    }
    fillReadout(state.bars.length ? state.bars[state.bars.length - 1] : null);
  }

  function setPressed(range) {
    var buttons = root.querySelectorAll(".chart-ranges [data-range]");
    for (var i = 0; i < buttons.length; i++) {
      var on = buttons[i].getAttribute("data-range") === range;
      buttons[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  function load(range) {
    var gen = ++state.loadGen;
    state.range = range;
    setPressed(range);
    if (!symbol) {
      state.bars = [];
      setStatus("No listing symbol — showing analysis levels only.");
      draw();
      return;
    }
    setStatus("Loading price history…");
    var url =
      "/api/price-history?symbol=" +
      encodeURIComponent(symbol) +
      "&range=" +
      encodeURIComponent(range);
    fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) {
        return r.json().then(function (body) {
          return { ok: r.ok, body: body };
        });
      })
      .then(function (payload) {
        if (gen !== state.loadGen) {
          return;
        }
        if (!payload.ok) {
          state.bars = [];
          setStatus((payload.body && payload.body.detail) || "Price history failed");
          draw();
          return;
        }
        var body = payload.body || {};
        state.bars = Array.isArray(body.bars) ? body.bars : [];
        if (body.error && !state.bars.length) {
          setStatus("Price history unavailable (" + body.error + "). Analysis levels still shown.");
        } else {
          setStatus("");
        }
        draw();
      })
      .catch(function () {
        if (gen !== state.loadGen) {
          return;
        }
        state.bars = [];
        setStatus("Price history failed. Analysis levels still shown.");
        draw();
      });
  }

  function buttonRange(el) {
    var node = el && el.nodeType === 3 ? el.parentElement : el;
    var btn = node && node.closest ? node.closest(".chart-ranges [data-range]") : null;
    if (!btn || !root.contains(btn)) {
      return "";
    }
    return String(btn.getAttribute("data-range") || "").trim().toLowerCase();
  }

  function initialRange() {
    var pressed = root.querySelector('.chart-ranges [data-range][aria-pressed="true"]');
    var fromPressed = buttonRange(pressed);
    if (fromPressed) {
      return fromPressed;
    }
    var first = root.querySelector(".chart-ranges [data-range]");
    return buttonRange(first) || "1y";
  }

  root.addEventListener("click", function (evt) {
    var range = buttonRange(evt.target);
    if (!range || range === state.range) {
      return;
    }
    load(range);
  });

  svg.addEventListener("mousemove", onMove);
  svg.addEventListener("mouseleave", onLeave);
  svg.addEventListener(
    "touchstart",
    function (evt) {
      if (evt.touches && evt.touches[0]) {
        onMove(evt.touches[0]);
      }
    },
    { passive: true }
  );

  if (typeof ResizeObserver === "function") {
    var ro = new ResizeObserver(function () {
      if (svg._lay) {
        draw();
      }
    });
    ro.observe(svg);
  } else {
    window.addEventListener("resize", function () {
      if (svg._lay) {
        draw();
      }
    });
  }

  load(initialRange());
})();
