# Mutation Log

## Modified
- **ui/js/app.js** — Added `VIZ_DBLCLICK_MS`, `vizLastNodeClick`, `vizFocusIdForNode`, `vizFocusOnNode`; the 3D graph's `onNodeClick` treats two clicks on the same node within 400 ms as a double-click that sets `#viz-focus-id`, resets `#viz-focus-degree` to 1 and calls `renderViz()`.
- **docs/help/notes/web-ui/visualize.md** — Documented double-click focus.

## Modified (follow-up fix)
- **ui/js/app.js** — Replaced the timestamp check inside `onNodeClick` with `vizNoteNodeClick` (remembers the node and pointer position of the first click) plus a native `dblclick` listener on `#viz-canvas` (`vizHandleDblClick`) that calls `vizFocusOnNode`; window widened to 700 ms with a 12 px pointer slop.
