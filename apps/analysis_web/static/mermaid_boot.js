/* Architecture figures: draw mermaid, then pan/zoom inside a frame.
 *
 * Host first (wrap before mermaid.run). Readable native size (useMaxWidth
 * off). Reset fits the whole chart. Control icons zoom without dragging.
 * Wheel zoom only while the pointer is over the figure. Mermaid CDN fail
 * → flowchart text. Pan/zoom CDN fail → drawn SVG + overflow on the host.
 */
(function () {
  var MERMAID_SRC =
    "https://cdn.jsdelivr.net/npm/mermaid@11.6.0/dist/mermaid.min.js";
  var PANZOOM_SRC =
    "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.2/dist/svg-pan-zoom.min.js";

  var nodes = document.querySelectorAll(".architecture-doc pre.mermaid");
  if (!nodes.length) return;

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = function () {
        resolve();
      };
      s.onerror = function () {
        reject(new Error(src));
      };
      document.head.appendChild(s);
    });
  }

  function wrapHosts(list) {
    for (var i = 0; i < list.length; i++) {
      var pre = list[i];
      if (pre.closest(".architecture-figure")) continue;
      var figure = document.createElement("div");
      figure.className = "architecture-figure";
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "architecture-figure-reset";
      btn.textContent = "Reset";
      pre.parentNode.insertBefore(figure, pre);
      figure.appendChild(pre);
      figure.appendChild(btn);
    }
  }

  function attachOne(figure) {
    var svg = figure.querySelector("svg");
    if (!svg || !window.svgPanZoom) return;
    var pz;
    try {
      pz = window.svgPanZoom(svg, {
        zoomEnabled: true,
        panEnabled: true,
        controlIconsEnabled: true,
        fit: false,
        center: true,
        minZoom: 0.15,
        maxZoom: 10,
        mouseWheelZoomEnabled: false,
      });
    } catch (err) {
      return;
    }
    try {
      pz.center();
    } catch (err2) {
      /* native size still shown */
    }
    figure.classList.add("is-interactive");
    figure.addEventListener("pointerenter", function () {
      pz.enableMouseWheelZoom();
    });
    figure.addEventListener("pointerleave", function () {
      pz.disableMouseWheelZoom();
    });
    var btn = figure.querySelector(".architecture-figure-reset");
    if (btn) {
      btn.addEventListener("click", function () {
        pz.fit();
        pz.center();
      });
    }
  }

  function attachAll() {
    if (!window.svgPanZoom) return;
    var figures = document.querySelectorAll(".architecture-figure");
    for (var i = 0; i < figures.length; i++) attachOne(figures[i]);
  }

  wrapHosts(nodes);

  loadScript(MERMAID_SRC)
    .then(function () {
      if (!window.mermaid) return;
      window.mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "neutral",
        useMaxWidth: false,
        flowchart: { useMaxWidth: false },
      });
      return window.mermaid.run({
        querySelector: ".architecture-figure .mermaid",
      });
    })
    .then(function () {
      return loadScript(PANZOOM_SRC).catch(function () {
        /* SVG stays; frame overflow still works */
      });
    })
    .then(function () {
      attachAll();
    })
    .catch(function () {
      /* mermaid failed: source text remains in pre.mermaid */
    });
})();
