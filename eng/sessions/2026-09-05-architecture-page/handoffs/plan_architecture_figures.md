# Plan — Architecture diagrams as inspectable figures

Follow-up to the `/architecture` page. UX first: a person reading the human map, not a CSS/API patch.

## Goal

On `/architecture`, each mermaid chart is a **figure you inspect**, like a map inside an article:

- Node text is about as large as the page body (never shrunk to “fit the column”).
- The article still scrolls as a document. A wide or tall chart does not shove the next heading off the screen or force sideways scrolling of the whole page.
- Pointer over a figure: **drag** to pan, **wheel / pinch** to zoom.
- Pointer elsewhere: the page scrolls as usual.
- **Reset** returns to an overview that fits the whole chart in the frame.
- If mermaid fails to load, the flowchart **text** remains. If mermaid draws but pan/zoom fails, the **drawn SVG** remains and the frame still scrolls.

Done means the three `ARCHITECTURE.md` diagrams are readable at rest and movable when you need detail. Tests cover the host markup, boot script, and “no squeeze” CSS. `ARCHITECTURE.md` website row mentions inspect (pan/zoom), not only “diagrams draw.”

## Current shape (why it feels bad)

- Sanitizer already emits `<pre class="mermaid">` (source stays in the node). Good.
- `architecture.html` loads `mermaid_boot.js`. Mermaid 11.6.0 from jsDelivr, `securityLevel: "strict"`. Boot does not await `mermaid.run` (it is a promise).
- CSS **squeezes** the SVG: `.architecture-doc .mermaid svg { max-width: 100%; height: auto; }`. That fights `overflow-x: auto` on `pre.mermaid`, so labels go tiny and the scroll path never runs.
- Mermaid’s own default `useMaxWidth` also scales the SVG to the container.

The page is a **long document with three maps in it**. Treating those maps as either a postage-stamp “fit” or a full-size poster in the article stream both fail reading.

## Design it twice

### A — Native 1:1 in the article, scroll the page

Turn off the squeeze. Let mermaid’s layout sit at 1:1. If the chart is wider than the card, the host scrolls.

**Reading:** labels can be large. **Document:** a tall top-to-bottom chart pushes the next section far down; a left-to-right chart makes you scroll the article sideways. You lose the surrounding prose. No inspect gesture, which the reader already asked for.

### B — Figure viewport + inspect (winner)

Each mermaid block lives in a **frame**. Default zoom keeps type readable. If the chart is larger than the frame, you pan and zoom **inside the frame**. The article around it still scrolls.

This is the usual map-in-a-page pattern (not a second drawing engine). `ARCHITECTURE.md` stays mermaid source.

**Winner: B.** A is simpler code. B is the simpler *reader* interface for mixed prose + maps.

## UX policy (one place: boot + a little CSS)

Put size and interaction in `mermaid_boot.js` plus `.architecture-figure` rules. Do not split “fit” across CSS, mermaid defaults, and a pan/zoom library.

| Rule | Behavior |
|------|----------|
| **Readable type first** | Default scale keeps node text ~ body size. Never use “fit the column” as the only view. |
| **Frame, not stamp** | Height about `min(60vh, 36rem)`, min ~ `28rem`. Not a 420px thumbnail. |
| **Start** | Native mermaid size (`useMaxWidth: false`), centered in the frame. If that already fits, you see the whole chart. If not, you pan — labels stay readable. |
| **Reset** | Fit *and* center the whole chart in the frame (overview). This is the one place “fit” is allowed. |
| **Wheel** | Zoom only while the pointer is over that frame (`pointerenter` / `pointerleave`). |
| **Chrome** | One **Reset** control on the figure. No extra +/− bars from the pan/zoom library. |
| **Failures** | Mermaid CDN fail → source text (already). Pan/zoom CDN fail → SVG + overflow on the host; do not drop back to text. |

Do not wrap-after-render as a second script. **Host first:** wrap each `pre.mermaid` in `.architecture-figure` (frame + Reset) **before** `mermaid.run`. Await the run promise, then attach pan/zoom to the SVG.

Library: **svg-pan-zoom** from jsDelivr (same style as mermaid). It has fit/center, which Reset needs. Do not vendor mermaid. Reports do not load this boot.

## What to change

| File | Change |
|------|--------|
| `apps/analysis_web/static/mermaid_boot.js` | Wrap hosts; `useMaxWidth: false`; await `mermaid.run`; load svg-pan-zoom; pan/drag; hover-wheel; Reset = fit/center; two-level fallback |
| `apps/analysis_web/static/app.css` | `.architecture-figure` viewport; **delete** svg `max-width: 100%` squeeze; Reset button placement |
| `apps/analysis_web/templates/architecture.html` | Unchanged except if a class on the card is useful |
| `apps/analysis_web/tests/…` | Host wrapper or Reset in HTML after boot is JS — assert boot source has `useMaxWidth`, `svg-pan-zoom`, Reset, `pointerenter`; CSS file does not squeeze svg to 100%; mermaid fences still `pre.mermaid` |
| `ARCHITECTURE.md` | Website row: diagrams are inspectable figures (pan/zoom), not only “draw” |
| `apps/analysis_web/README.md` | Same one-liner |

Sanitizer stays as it is: inert `<pre class="mermaid">`. Do not put viewports in Python.

## Non-goals

- Clickable mermaid nodes
- Cytoscape / vis-network
- Vendoring mermaid.min.js
- Mermaid on report/compare pages
- Editing `ARCHITECTURE.md` diagram source (layout of the charts themselves)

## Verify

```bash
python -m pytest apps/analysis_web/tests/test_render_markdown.py apps/analysis_web/tests/test_analysis_web.py -q
```

Person: restart UI, open `/architecture`. For each of the three charts: labels readable at rest; drag moves the chart not the page; wheel over the chart zooms; wheel over prose scrolls the page; Reset shows the whole chart; next heading still near the figure.

## Risks

- **svg-pan-zoom vs mermaid DOM:** mermaid 11 may replace or wrap the `<pre>`. Attach to the **SVG node** after run; if the pre is gone, the wrapper still holds the SVG.
- **Touch:** pinch should zoom; one-finger drag should pan. Check a laptop trackpad.
- **CDN:** two script loads (mermaid, then panzoom). Sequence: mermaid onload → run → panzoom onload → attach. If panzoom never arrives, SVG + frame overflow is still OK.
- **Page vs figure scroll:** getting hover-wheel wrong will trap the reader. Default wheel on the page; only preventDefault while over the figure.
