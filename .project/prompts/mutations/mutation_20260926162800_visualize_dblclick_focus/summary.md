# Mutation Summary

## Intent
Let users double-click a hypernode or hyperedge in Visualize to focus on it, with degrees reset to 1° and the scene re-rendered.

## Context
Focus is driven by the `#viz-focus-id` text field and `#viz-focus-degree` select, read by `renderViz()`. 3d-force-graph exposes no double-click callback.

## What Changed and Why
`onNodeClick` now records the last clicked node and time; a second click on the same node within 400 ms calls `vizFocusOnNode`, which fills the focus field with the element's raw id, sets degrees to "1" and re-renders. Single clicks behave as before (camera move + detail panel); the first click of a double-click still does that, which is harmless.

## Key Decisions
- Timestamp-based detection inside `onNodeClick`, since the library has no dblclick event.
- A members (virtual) node focuses its parent hyperedge; hyperedge nodes use `id` or `hyperkey`; cross-graph reference nodes work because the neighborhood code already resolves ids across selected graphs.
- Inferred edges have only synthetic ids, so a double-click on them shows a warning toast and falls back to the normal click behaviour.
- No automated UI test exists for this screen; verified by JS syntax check only.

## Follow-up: why the first version did nothing
The first version required the second click of a double-click to hit the same node. But the first click starts a 700 ms camera fly-to, so the node has moved from under the pointer by the second click; the raycast hit another node or nothing, no double-click was recognised, and only the normal zoom happened (the served JS was confirmed current, so it was not a caching problem). The fix listens to the browser's native `dblclick` on the canvas and acts on the node recorded by the FIRST click (kept if the pointer stays within 12 px within 700 ms). Not yet verified in a browser: the Chrome tab reached the login page and the credentials are the user's to enter.

## Verification (browser)
On the `eden` graph (9 hypernodes / 8 hyperedges, degree set to 2°), a double-click on the "Seth" hypernode set the focus field to `person:seth`, reset the degree select to 1°, and re-rendered to 7 hypernodes / 3 hyperedges centred on Seth, with Seth's details shown in the panel.
