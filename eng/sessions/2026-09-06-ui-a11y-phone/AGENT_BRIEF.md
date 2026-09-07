# Agent brief — ui-a11y-phone (post-SDR)

Mode B W4. Read `eng/AGENTS.md` and parent `PLAN.md` § Session 5 plus `handoffs/sdr-wave4b-a11y-phone.md`.

**Start after** `ui-nav-ia` **and** `ui-decision-blotter` (skip link exists; `.decision` selectors exist). You own the **1100px contract** in `app.css`.

SDR verdict: **mixed / reshape**. Do **not** clip `.stack-table thead` (that recreates the invisible tab-stop this session exists to kill). Drop harness 900px from this session.

## Goal

First Tab is not an invisible checkbox. Night primary buttons pass 4.5:1. Landscape phone / tablet get stacked cards. Report tables scroll locally.

## Slices

1. **breakpoint-1100** — One comment; replace **every** `max-width: 800px` in `app.css`. Desktop disclose hide at `min-width: 1101px`. README/CSS comments move with it.
2. **disclose-focus** — Class-level hide when wide (Menu + Lab + Filters). Phone `:focus-visible` on `.disclose-btn`.
3. **contrast** — Night `--btn-bg` `#2563eb` in both dark tables. Words use `--muted`.
4. **thead** — Keep `display:none`. After swap, `aria-label` from `data-label`. Do not clip.
5. **live-focus** — `#runs-status` outside the swap. Dispatch `runs-table-updated`. `compares.js` listens to that. Sticky compare bar only while a pick is on. 44px pick hit. Hint = ticker + session_key.
6. **figures** — Architecture frame in the 1100px query; mermaid `controlIconsEnabled: true`. **No harness.css.**

## Non-goals

Do not reorder columns. Do not restyle `.decision` / `.below-bear`. Do not reintroduce 800. No sticky site header. No second card markup. No harness pipeline column.

## Verify

pytest. Keyboard: Tab on desktop `/` does not land on a mystery checkbox. ~844px-wide viewport uses stacked cards. Sort headers are not tab stops on phone. `eng_verify`.

No commit until the user agrees.
