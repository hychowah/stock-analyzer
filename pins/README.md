# Published harness pins

Each `pins/<semver>/` folder is a **frozen** Mode A runtime (law + `packages/` + `scripts/` + `AGENTS.md`) copied when `harness/VERSION` was bumped.

- Do **not** edit a published pin after it is committed.
- `live` Analyze uses the working tree, not these folders.
- Host MCP / `.grok` stay on the workspace; they are not copied here.
- Create a new pin with `python scripts/publish_harness_release.py` in the same change set as the VERSION bump.
