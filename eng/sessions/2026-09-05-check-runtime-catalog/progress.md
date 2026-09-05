# Eng session 2026-09-05-check-runtime-catalog

- Created: 2026-09-05T01:43:16Z
- Work type: W1
- Goal: Stop research-runtime law piling into check_session / gates / street_bind

## Log

- 2026-09-05T01:43:16Z scaffolded
- F1: `check_core.py` (Check, load_json, session_since, validate_hooks_list). Domain `session_is_*` wrappers call `session_since`. `gates.load_json` / `validate_hooks_list` re-export. `operating_path.load_json` wraps check_core (dict-only).
- F1: `check_catalog.py` — CheckRow table + `run_catalog(when)`. `entry_checks` / `complete_checks` iterate path tables + catalog; no per-wave if-ladders. `PATH_EXTRAS` feeds `workflow_spec` (no STREET_SINCE import there). Dead `PHASE_COMPLETE_GLOBS` replaced by used `PHASE_COMPLETE_PATHS`.
- F1: `check_session.py` — one sys.path insert; `--full` is a step list. Importlib tests still use `results`/`record()`.
- F2: `street_y1.StreetY1Policy` (2.7 / 2.18 / 2.28). Dials / stacking / SOTP / box floor → `valuation_hygiene.py`. `destock_this_print` → `epistemology.py` (street_bind facade). `check_street_bind` still invokes hygiene so row-sets stay.
- Not this session: split `library.py` ingest vs gates. Remaining gates implementations (FDD, Agent 4, year-dive, LLM identity, MoS) still live in `gates.py` as domain bodies; dispatcher is gone.
- Refactor why: one catalog row per new gate; Street policy is a table not nested `if y1 / gated`; I/O no longer lives in the orchestrator.
- `harness/VERSION` 2.34.0 (runtime reshape, no Mode A statute change).
