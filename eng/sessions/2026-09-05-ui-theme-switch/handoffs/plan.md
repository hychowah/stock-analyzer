# Plan: night / light theme switch

**Review (2026-09-05):** Direction mixed → reshape. Two candidates applied: (1) token cascade — light on `:root`, dark only on `html[data-theme="dark"]`, no-JS dark only on `@media (prefers-color-scheme: dark) { html:not([data-theme]) }`; (2) one membership list — chrome / paper / semantic. Winner A unchanged.

## Goal

A person can switch the analysis website between **light** and **night** from the shared header. The choice sticks across pages and reloads. Light matches today’s look. Night inverts **chrome** only. Done means: toggle works on every `base.html` page, persists in `localStorage` after a click, first paint does not flash the wrong theme, tests + `eng_verify` green, browser check on several routes.

## Current shape

- One product UI: FastAPI + Jinja + static CSS. Every page extends `apps/analysis_web/templates/base.html`.
- Colors are **hex in selectors**. `static/app.css` owns chrome. `static/harness.css` repeats the same slate hex.
- No theme, no `prefers-color-scheme`, no chrome tokens. `:root` only sets font and `#1a1a1a`.
- One inline color in `base.html` (tagline `#94a3b8`).
- Browser memory already exists: `runs.js` uses `localStorage` key `analysis_web.runs.query` and ignores quota / private-mode failures.
- Semantic greens/reds are **not** chrome: Live chg-up/down, `.badge.pass/.fail/.status-*`, chart series, harness stage accents.
- Architecture figures use mermaid `theme: "neutral"` on a white `.architecture-figure`.
- App state law: server files under `apps/analysis_web/.local/` only. Theme must not touch `archive/`.

## Design it twice

| | A — tokens + `data-theme` + one JS file | B — two stylesheets (`app.css` / `app-dark.css`) |
|---|---|---|
| Switch | `html[data-theme="light"\|"dark"]`; header button | Swap `<link href>` |
| New CSS | Write the rule once; dark is a token table | Copy every rule; harness needs a third file |
| First paint | Blocking `theme.js` in `<head>` before CSS | Same FOUC plus a wrong-sheet flash |
| Common case | Click Night; every page already extends `base.html` | Same click, worse maintenance |

**Winner: A.** One attribute and one button. Dark is a second palette on the same rules.

Binary Light/Night. First visit follows `prefers-color-scheme` **without** writing storage. A click writes `analysis_web.theme` (`light` or `dark`). Fail-open like `runs.js`. No System/Light/Night three-way. No cookie.

## Token module (from-scratch)

**Cascade** (comment this next to the token block, and on the `theme.js` tag: `no defer` — why):

1. Light table on `:root` only (today’s hex). Includes `--paper` and `color-scheme: light`.
2. Dark table **only** on `html[data-theme="dark"]`. Does **not** restyle `--paper`. Sets `color-scheme: dark`.
3. No-JS dark **only** as `@media (prefers-color-scheme: dark) { html:not([data-theme]) { …same dark names… } }`. Never `@media { :root { dark } }` — that ties with `:root` light and would paint Night for a stored Light on a dark OS.
4. `theme.js` (no `defer`, before `app.css`) always sets `data-theme` to `light` or `dark` before paint. With JS, the media query never applies. Persist only after a click.

**Membership** (one list next to `:root`; grep leftover chrome hex against this list, not “every hex”):

| Bucket | What | How |
|---|---|---|
| **chrome** | page, fg, muted, card, border, hover, header, links, inputs, buttons, pre, flash/err, chart **stage / grid / ink / tooltip / range chips / this-run / hover halo**, default chip `--chip-bg` | `var(--…)` — inverts |
| **paper** | `.architecture-figure` and its Reset | `--paper` equal in both palettes (defined on `:root` only). Not a dark override of `--card`. Mermaid stays `neutral`. |
| **semantic** | Live chg-up/down; `.badge.pass/.fail/.status-*`; bear/base/bull/weighted/asof series + labels + **those** swatches; perf-bar pos/neg; harness stage accents + required cyan | hex forever |

Price **ink** includes `.chart-price`, `.swatch-price`, and `.chart-this-run`. Default `.badge` and harness chip are chrome, not “badges” as a lump.

## What to change

1. **`apps/analysis_web/static/app.css`** — token block + cascade as above; chrome hex → `var(--…)`. Paper uses `--paper`. Semantic stays hex.

2. **`apps/analysis_web/static/harness.css`** — chrome hex → the same tokens. Stage accents and required-chip cyan stay hex.

3. **`apps/analysis_web/static/theme.js`** (new) — key `analysis_web.theme`; apply immediately; bind header button; storage failures ignored.

4. **`apps/analysis_web/templates/base.html`** — `<script src="/static/theme.js"></script>` in `<head>` **before** the stylesheet, no `defer`. Comment on the tag. Header toggle. Tagline inline color → class.

5. **`apps/analysis_web/README.md`** — one line: theme is browser-local (`analysis_web.theme`), not archive.

6. **Tests** (`apps/analysis_web/tests/test_analysis_web.py`)
   - `:root` defines chrome vars including `--paper`; `html[data-theme="dark"]` defines chrome vars and does **not** set `--paper`.
   - Dark media query targets `html:not([data-theme])`, not `:root`.
   - chg-up/down rule bodies still contain hex `background` (not `var(`).
   - `theme.js` has the storage key, `light`/`dark`, `prefers-color-scheme`, ignore-storage.
   - Home HTML includes `theme.js` before `app.css` and `#theme-toggle`. `/harness` still has both.

7. **`ARCHITECTURE.md`** — leave it. No new page, CLI, archive plane, or identity.

## Non-goals

- Per-user server cookie / account preference.
- Three-way System/Light/Night control.
- Restyling mermaid to a dark theme.
- Tokenizing semantic colors (table above).
- High-contrast / extra palettes.
- Touching catalog, harness VERSION, or `archive/`.

## Verify

- `python -m pytest apps/analysis_web/tests -q`
- `python scripts/eng_verify.py`
- Browser (desktop + ~375px): `/`, a run detail (chart), `/harness`, `/architecture`, `/analyze`, `/portfolio`. Toggle Night → navigate (stays) → reload (stays) → Light (today’s look). Live chips and pass/fail badges still green/red. Architecture figure stays paper. No wrong-theme flash on reload.

## Risks

- Incomplete chrome token coverage: leftover page/card/table hex will pop in night. Grep against the membership list.
- FOUC if `theme.js` is deferred or placed after CSS.
- Chart price stroke is `#0f172a` today — must be `--chart-ink` or it vanishes on a dark stage.
- Header is already dark; the toggle must stay visible (ghost on the navy bar).
- `localStorage` in private mode: fail open to system preference; do not throw.
