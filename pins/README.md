# Published harness pins

Each `pins/<semver>/` folder is a **frozen** Mode A runtime (`AGENTS.md`, `harness/`, `packages/kd_research/`, Mode A scripts) copied when `harness/VERSION` was bumped. Going-forward pins do not copy catalog/UI/eng packages or tests. `pins/2.27.0`–`2.37.0` are older full `packages/`+`scripts/` copies.

- Do **not** edit a published pin after it is committed.
- `live` Analyze uses the working tree, not these folders.
- Host MCP / `.grok` stay on the workspace; they are not copied here.
- Create a new pin with `python scripts/publish_harness_release.py` in the same change set as the VERSION bump.
