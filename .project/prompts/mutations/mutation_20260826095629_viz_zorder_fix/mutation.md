# Mutation Log

## Modified
- **ui/js/app.js** — Added `vizZIndexForDist(dist)`, a shared helper deriving a CSS z-index from camera distance (closer = higher), placed next to `vizProjectPoint`/`vizWorldSizeToPx`. `vizLabelTick()` now assigns `el.style.zIndex` from this helper for all three DOM-overlay element kinds it positions every frame — node labels (`vizLabelNodeEls`), link labels (`vizLabelLinkEls`), and media thumbnails (`vizThumbNodeEls`) — using the same distance scale across all three so, e.g., a close link label correctly outranks a far node label.
- **ui/css/hgai.css** — Added `isolation: isolate` to `#viz-label-layer`, making it its own stacking context so the new per-frame z-index values assigned to its children can only ever compete with each other and can never affect stacking relative to the WebGL canvas or the rest of the page.
