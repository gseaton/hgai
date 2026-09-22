# Mutation Log

## Modified
- **ui/index.html** — Added a "Max Nodes" number input (`#viz-max-nodes`, default 200, min 1) to the Visualize screen's control bar, between the Focus control and the Labels toggle.
- **ui/js/app.js** — Added `VIZ_MAX_NODES_DEFAULT` and `vizGetMaxNodes()` (reads and clamps the input, falling back to 200 for empty/invalid/non-positive values). `renderViz()` now caps the final merged node set (after all selected graphs, cross-graph references and inferred edges are resolved) to this value, filtering links to match; the focused element (if any) is always kept even if it would otherwise be cut. The type/flavor legend and the "N hypernodes · N hyperedges" stat line are now computed from the final, possibly-capped node set instead of the full pre-cap set, so they always describe what's actually on screen. The truncation toast now distinguishes "server fetch limit exceeded" from "Max Nodes cap applied" (and both together).
- **docs/help/notes/web-ui/visualize.md** — Documented the new Max Nodes control in the controls table.
