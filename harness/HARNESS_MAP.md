# Stock-Research Harness Map

**Purpose of this system:** investment-decision research — decision-grade fair value, risks, timing, and provenance.  
**North star for agents:** leave artifacts the **next** phase can use without re-guessing numbers or missing material risks.  
**Not the goal:** token thrift or shorter runs for their own sake.

Normative rules: root `AGENTS.md`. Subagent templates: `harness/agent_prompts.md`. Pipeline design: `harness/design_phase_status_and_exemplars.md`. Industry research notes: `harness/research/`.

---

## 1. Session layout

```text
archive/research/<TICKER>/<YYYY-MM-DD>/
  reports/   README + fundamental + technical
  data/      financials, prices, valuation_model.json, compute/, raw_sec/, transcripts/
  charts/
  registry/  configs, evidence JSON, phase_status, handoffs/, raw/
  meta/      run_manifest, prediction_snapshot
```

Scaffold: `python3 scripts/scaffold_session.py --ticker T --date YYYY-MM-DD`

---

## 2. Phase graph → handoff promise

| Phase | Agents | Must produce (evidence) | Next phase needs |
|-------|--------|-------------------------|------------------|
| **orch** | main | `sector_config.json`, `market_context.json`, `research_brief.json` (new sessions) | Scope, sector model family, intensity, investment questions |
| **0** | background swarm | `background.json`, `raw/phase0_*.json`, handoff | Valuation/risk themes; `risk_candidate` list; brief coverage gaps |
| **1_parallel** | 2a, 2b, 2c | financials CSV, `sec_filings` + `raw_sec/`, `news_sentiment`, fetch log, handoffs | Actuals, primary text, catalysts |
| **1b** | 2d | `latest_quarter.json` + evidence_log | Overrides input for Agent 5; risks for 2.5 |
| **1c** | 2e | `filing_deep_dive.json` (+ transcripts if any) | Footnotes, strategy_arc, scorecard for valuation hooks |
| **2_parallel** | 4, 5, 12 | `technical.json`, `valuation_model.json`, `tsr_validation.json` | FV/MOS for reports & stress; levels for technical report |
| **2_5** | stress swarm | `risk_bridge.json`, ≥5 `raw/stress_*.json` | Risk lens, scenario probs, sizing input |
| **3** | 6 | `charts/*.png` | Visuals for reports |
| **4_parallel** | 7, 8, 11 | three `reports/*.md` | Investor-readable package |
| **5** | 13 | `audit.json` verdict | Gate for “complete” |
| **done** | — | audit PASS (or waived in README) | Catalog snapshot |

**Dependency rule of thumb:** do not start **2** without 1b+1c evidence; do not start **4** without valuation+risk_bridge+technical+tsr; do not claim **done** without audit PASS.

---

## 3. If X is missing, do not start Y

| Missing / broken | Do not start | Fix first |
|------------------|--------------|-----------|
| `sector_config` or `market_context` | Phase 0 / 1 | Orchestrator classification |
| `research_brief` (new sessions) | Phase 0 fan-out | Write brief after classification |
| `sp_financials.csv` or `sec_filings` / raw_sec | 1b / 1c / 2 | Agents 2a / 2b |
| `latest_quarter` or `filing_deep_dive` | Phase 2 valuation | 2d / 2e |
| `valuation_model.json` | 2.5, 3, 4 | Agent 5 |
| `risk_bridge` or technical / tsr | Phase 4 reports | 2.5 / 4 / 12 |
| Three reports | Phase 5 | Agents 7 / 8 / 11 |

**Mechanical preflight:**

```bash
python3 scripts/preflight_phase.py --ticker T --date D --phase 2_parallel
python3 scripts/preflight_phase.py --ticker T --date D --phase 2_5
python3 scripts/preflight_phase.py --ticker T --date D --phase 4_parallel
python3 scripts/preflight_phase.py --ticker T --date D --phase 5
```

Orchestrator **MUST** preflight (or equivalent evidence check) before those phases. FAIL → fix upstream; do not invent.

---

## 4. Intensity & research depth (investment complexity)

| Signals | Depth | Behavior |
|---------|-------|----------|
| intensity `low`, confidence ≥0.70, widely held US GAAP | `standard` | Full quality gates; region hooks may be `noted_only` |
| intensity `medium`, multi-currency, local filings | `deep` | Ownership/FX/local CoC in Phase 0 + 2e + valuation hooks; stress region if material |
| intensity `high`, family/SOE/VIE, confidence &lt;0.70, thin disclosure | `deep` + **widen FV range** | Mandatory control/related-party work; ≥1 region/gov stress; `requires_manual_review` as warranted |

Set `research_depth` on `registry/research_brief.json`. Depth **adds** research on hard names; it never strips deep dive, ≥5 stress scenarios, or audit.

---

## 5. Decision-grade returns (agent → next agent)

1. **Artifact on disk** is the product; chat is disposable.  
2. Swarm JSON: specific findings + sources + `downstream_relevance` (Phase 0) / grounded haircuts (2.5).  
3. Handoff section 4: top 3 miss-nots, range wideners, paths.  
4. Full filings live in `data/raw_sec/` — not in return JSON.  
5. Numbers in reports come from registry/compute only.

Details: `harness/agent_prompts.md` conventions + `harness/exemplars/`.

---

## 6. Where things live

| Need | Path |
|------|------|
| Normative spec | `AGENTS.md` |
| Prompt templates | `harness/agent_prompts.md` |
| Schemas | `templates/*.schema.json` |
| Structural check | `scripts/check_session.py --full` |
| Phase preflight | `scripts/preflight_phase.py` |
| Session acceptance | `check_session.py --full --write-acceptance` |
| Sector methodology | `sector_*.md` (advisory) |
| Region methodology | `region_*.md` (advisory) |
| Filing deep-dive method | `harness/filing_deep_dive.md` |
| Resume map design | `harness/design_phase_status_and_exemplars.md` |
| Judgment exemplars | `harness/exemplars/` |

---

## 7. Session complete?

1. `registry/audit.json` → `verdict: PASS` (or README waivers)  
2. `python3 scripts/check_session.py --ticker T --date D --full` green  
3. Optional: `--write-acceptance registry/session_acceptance.json` for a machine checklist  

Then: `build_prediction_snapshot.py` + `rebuild_catalog.py`.
