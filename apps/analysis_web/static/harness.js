"use strict";

(function () {
  const shell = document.querySelector(".harness-shell");
  if (!shell) return;
  const version = shell.getAttribute("data-harness-version") || "live";
  const modelEl = document.getElementById("harness-page-model");
  const emptyEl = document.getElementById("inspector-empty");
  const bodyEl = document.getElementById("inspector-body");
  let model = {};
  try {
    model = modelEl ? JSON.parse(modelEl.textContent || "{}") : {};
  } catch (err) {
    model = {};
  }
  const promptCache = {};

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        const val = attrs[key];
        if (val == null || val === false) return;
        if (key === "className") node.className = val;
        else if (key === "text") node.textContent = val;
        else node.setAttribute(key, val === true ? "" : String(val));
      });
    }
    (children || []).forEach(function (child) {
      if (child) node.appendChild(child);
    });
    return node;
  }

  function qattr(name, value) {
    return (
      "[" +
      name +
      '="' +
      String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"') +
      '"]'
    );
  }

  function findAgent(agentId) {
    const stages = model.stages || [];
    for (let s = 0; s < stages.length; s++) {
      const phases = stages[s].phases || [];
      for (let p = 0; p < phases.length; p++) {
        const agents = phases[p].agents || [];
        for (let a = 0; a < agents.length; a++) {
          if (agents[a].id === agentId) {
            return { agent: agents[a], phase: phases[p], stage: stages[s] };
          }
        }
      }
    }
    return null;
  }

  function findPhase(phaseId) {
    const stages = model.stages || [];
    for (let s = 0; s < stages.length; s++) {
      const phases = stages[s].phases || [];
      for (let p = 0; p < phases.length; p++) {
        if (phases[p].id === phaseId) {
          return { phase: phases[p], stage: stages[s] };
        }
      }
    }
    return null;
  }

  function chips(list) {
    const ul = el("ul", { className: "harness-chips" });
    (list || []).forEach(function (chip) {
      const span = el("span", {
        className: "harness-chip" + (chip.required ? " is-required" : ""),
        title: chip.path || "",
      });
      span.appendChild(document.createTextNode(chip.label || chip.name || ""));
      if (chip.producer_label) {
        span.appendChild(
          el("span", { className: "muted", text: " from " + chip.producer_label })
        );
      }
      ul.appendChild(el("li", null, [span]));
    });
    return ul;
  }

  function notesList(notes) {
    if (!notes || !notes.length) return null;
    const ul = el("ul", { className: "harness-page-notes" });
    notes.forEach(function (note) {
      ul.appendChild(el("li", { text: note.text || note.id || "" }));
    });
    return ul;
  }

  function clearSelection() {
    document.querySelectorAll(".harness-agent.is-selected, .harness-phase.is-selected").forEach(
      function (node) {
        node.classList.remove("is-selected");
      }
    );
  }

  function setUrl(agentId, phaseId) {
    const url = new URL(window.location.href);
    if (agentId) url.searchParams.set("agent", agentId);
    else url.searchParams.delete("agent");
    if (phaseId && !agentId) url.searchParams.set("phase", phaseId);
    else url.searchParams.delete("phase");
    url.searchParams.set("version", version);
    window.history.replaceState({}, "", url);
  }

  function showInspector(node) {
    if (emptyEl) emptyEl.hidden = true;
    if (!bodyEl) return;
    bodyEl.hidden = false;
    bodyEl.replaceChildren(node);
  }

  function heading(kicker, title) {
    return el("header", null, [
      el("p", { className: "harness-kicker muted", text: kicker }),
      el("h2", { text: title }),
    ]);
  }

  function labeled(title, child) {
    if (!child) return null;
    return el("div", null, [el("h3", { text: title }), child]);
  }

  function renderAgentOverview(hit, prompt) {
    const agent = hit.agent;
    const phase = hit.phase;
    const bits = [phase.label || phase.id, agent.id];
    if (agent.spawn_role) bits.push(agent.spawn_role);
    const wrap = el("div", { className: "harness-overview" });
    wrap.appendChild(heading(bits.join(" · "), agent.label));
    if (prompt && prompt.role_line) {
      wrap.appendChild(el("p", { className: "muted", text: prompt.role_line }));
    }
    if (prompt && prompt.summary) {
      wrap.appendChild(el("p", { text: prompt.summary }));
    }
    const writes = labeled("Writes", chips(agent.write_chips || []));
    if (writes) wrap.appendChild(writes);
    const agentNotes = notesList(agent.notes);
    if (agentNotes) wrap.appendChild(labeled("Notes", agentNotes));
    return wrap;
  }

  function renderPhaseOverview(hit) {
    const phase = hit.phase;
    const stage = hit.stage;
    const wrap = el("div", { className: "harness-overview" });
    wrap.appendChild(heading((stage.label || "") + " · " + phase.id, phase.label));
    if (phase.purpose) wrap.appendChild(el("p", { text: phase.purpose }));
    if (phase.agents && phase.agents.length) {
      const list = el("ul", { className: "harness-chips" });
      phase.agents.forEach(function (ag) {
        const btn = el("button", {
          type: "button",
          className: "harness-chip",
          text: ag.label,
        });
        btn.addEventListener("click", function () {
          selectAgent(ag.id);
        });
        list.appendChild(el("li", null, [btn]));
      });
      wrap.appendChild(labeled("Specialists", list));
    }
    if (phase.needs && phase.needs.length) {
      wrap.appendChild(labeled("Needs first", chips(phase.needs)));
    }
    if (phase.writes && phase.writes.length) {
      wrap.appendChild(labeled("Writes", chips(phase.writes)));
    }
    const n = notesList(phase.notes);
    if (n) wrap.appendChild(labeled("Notes", n));
    return wrap;
  }

  function renderSections(sections) {
    const frag = document.createDocumentFragment();
    (sections || []).forEach(function (section) {
      const open = section.id === "briefing" || section.id === "body";
      const details = el("details", { className: "harness-section" });
      if (open) details.open = true;
      details.appendChild(el("summary", { text: section.label || section.id }));
      const body = el("div", { className: "report-body" });
      body.innerHTML = section.html || "";
      details.appendChild(body);
      frag.appendChild(details);
    });
    return frag;
  }

  function renderPromptPanel(prompt) {
    const wrap = el("div", { className: "harness-prompt" });
    if (!prompt) {
      wrap.appendChild(el("p", { className: "muted", text: "Loading…" }));
      return wrap;
    }
    if (prompt.found === false) {
      wrap.appendChild(el("p", { className: "err", text: "No prompt slice for this agent." }));
      return wrap;
    }
    wrap.appendChild(renderSections(prompt.sections || []));
    if (prompt.body_html) {
      const src = el("details", { className: "harness-source" });
      src.appendChild(el("summary", { text: "View source" }));
      const body = el("div", { className: "report-body" });
      body.innerHTML = prompt.body_html;
      src.appendChild(body);
      wrap.appendChild(src);
    }
    return wrap;
  }

  function paintAgent(hit, tab, prompt) {
    const root = el("div");
    const tabs = el("div", { className: "harness-tabs", role: "tablist" });
    const overviewBtn = el("button", {
      type: "button",
      className: tab === "prompt" ? "" : "is-active",
      text: "Overview",
    });
    const promptBtn = el("button", {
      type: "button",
      className: tab === "prompt" ? "is-active" : "",
      text: "Prompt",
    });
    overviewBtn.addEventListener("click", function () {
      paintAgent(hit, "overview", promptCache[hit.agent.id]);
    });
    promptBtn.addEventListener("click", function () {
      openPrompt(hit);
    });
    tabs.appendChild(overviewBtn);
    tabs.appendChild(promptBtn);
    root.appendChild(tabs);
    const panel = el("div", { className: "harness-panel" });
    if (tab === "prompt") panel.appendChild(renderPromptPanel(prompt));
    else panel.appendChild(renderAgentOverview(hit, promptCache[hit.agent.id]));
    root.appendChild(panel);
    showInspector(root);
  }

  async function openPrompt(hit) {
    const id = hit.agent.id;
    if (promptCache[id]) {
      paintAgent(hit, "prompt", promptCache[id]);
      return;
    }
    paintAgent(hit, "prompt", null);
    const url =
      "/api/harness/prompt?agent=" +
      encodeURIComponent(id) +
      "&version=" +
      encodeURIComponent(version);
    try {
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) {
        promptCache[id] = { found: false, error: data.error || "error", sections: [] };
      } else {
        promptCache[id] = data;
      }
    } catch (err) {
      promptCache[id] = { found: false, error: String(err), sections: [] };
    }
    const selected = document.querySelector(".harness-agent.is-selected");
    if (selected && selected.getAttribute("data-agent") === id) {
      paintAgent(hit, "prompt", promptCache[id]);
    }
  }

  function selectAgent(agentId) {
    const hit = findAgent(agentId);
    if (!hit) return;
    clearSelection();
    const btn = document.querySelector(".harness-agent" + qattr("data-agent", agentId));
    if (btn) btn.classList.add("is-selected");
    const phaseEl = document.querySelector(".harness-phase" + qattr("data-phase", hit.phase.id));
    if (phaseEl) phaseEl.classList.add("is-selected");
    setUrl(agentId, hit.phase.id);
    paintAgent(hit, "overview", promptCache[agentId]);
  }

  function selectPhase(phaseId) {
    const hit = findPhase(phaseId);
    if (!hit) return;
    clearSelection();
    const phaseEl = document.querySelector(".harness-phase" + qattr("data-phase", phaseId));
    if (phaseEl) phaseEl.classList.add("is-selected");
    setUrl("", phaseId);
    showInspector(renderPhaseOverview(hit));
  }

  document.querySelectorAll(".harness-agent").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const id = btn.getAttribute("data-agent");
      if (id) selectAgent(id);
    });
  });
  document.querySelectorAll(".harness-phase-head").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const id = btn.getAttribute("data-phase");
      if (id) selectPhase(id);
    });
  });

  const openAgent = shell.getAttribute("data-open-agent") || "";
  const openPhase = shell.getAttribute("data-open-phase") || "";
  if (openAgent) selectAgent(openAgent);
  else if (openPhase) selectPhase(openPhase);
})();
