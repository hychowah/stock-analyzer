"use strict";

(function () {
  const page = document.querySelector(".harness-page");
  if (!page) return;
  const version = page.getAttribute("data-harness-version") || "live";
  const specEl = document.getElementById("harness-spec");
  const inspector = document.getElementById("inspector-body");
  const lanes = document.getElementById("swimlanes");
  const dag = document.getElementById("artifact-dag");
  const svg = document.getElementById("dag-svg");
  let spec = {};
  try {
    spec = specEl ? JSON.parse(specEl.textContent || "{}") : {};
  } catch (err) {
    spec = {};
  }

  function showLanes() {
    if (lanes) lanes.hidden = false;
    if (dag) dag.hidden = true;
  }
  function showDag() {
    if (lanes) lanes.hidden = true;
    if (dag) dag.hidden = false;
    drawDag();
  }

  function drawDag() {
    if (!svg) return;
    const edges = Array.isArray(spec.edges) ? spec.edges : [];
    const names = [];
    const seen = {};
    edges.forEach(function (e) {
      [e.from, e.to].forEach(function (n) {
        if (!n || seen[n] || String(n).indexOf("*") >= 0) return;
        seen[n] = true;
        names.push(String(n));
      });
    });
    const width = Math.max(640, names.length * 8);
    const rowH = 22;
    const height = Math.max(240, names.length * rowH + 40);
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("width", "100%");
    svg.innerHTML = "";
    const ns = "http://www.w3.org/2000/svg";
    names.forEach(function (name, i) {
      const y = 20 + i * rowH;
      const text = document.createElementNS(ns, "text");
      text.setAttribute("x", "8");
      text.setAttribute("y", String(y));
      text.setAttribute("class", "dag-label");
      text.textContent = name;
      svg.appendChild(text);
    });
  }

  async function loadPrompt(agentId) {
    if (!inspector) return;
    inspector.textContent = "Loading…";
    const url =
      "/api/harness/prompt?agent=" +
      encodeURIComponent(agentId) +
      "&version=" +
      encodeURIComponent(version);
    try {
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) {
        inspector.textContent = data.error || "error";
        return;
      }
      const conv = data.conventions_html || "";
      const body = data.body_html || "";
      inspector.innerHTML =
        "<h3 class=\"mono\">" +
        (data.title || agentId) +
        "</h3><details><summary>Conventions for all agents</summary>" +
        conv +
        "</details>" +
        "<div class=\"report-body\">" +
        body +
        "</div>";
    } catch (err) {
      inspector.textContent = String(err);
    }
  }

  document.querySelectorAll(".harness-agent").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const id = btn.getAttribute("data-agent");
      if (id) loadPrompt(id);
    });
  });
  const lanesBtn = document.getElementById("view-lanes");
  const dagBtn = document.getElementById("view-dag");
  if (lanesBtn) lanesBtn.addEventListener("click", showLanes);
  if (dagBtn) dagBtn.addEventListener("click", showDag);
})();
