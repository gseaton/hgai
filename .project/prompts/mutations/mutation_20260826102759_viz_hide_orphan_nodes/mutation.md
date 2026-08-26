# Mutation Log

## Modified
- **ui/index.html** — Added a "Hide orphan nodes" switch (`#viz-hide-orphans`) to the Visualize screen's control row, alongside the existing Labels/Media/Auto-rotate switches.
- **ui/js/app.js** — `renderViz()` now computes, per selected graph, the set of hypernode ids actually referenced as a member by at least one hyperedge in that graph; when the new toggle is checked, hypernodes not in that set are excluded from the rendered node list (and from the type-count legend) entirely — hyperedges, their virtual "members" nodes, and all links are unaffected. Added a `change` listener on the new checkbox that re-runs `renderViz()` (guarded on a graph already being rendered), since — unlike the Labels/Media toggles, which only flip a display flag the already-rendered scene respects — this changes which nodes actually exist in 3d-force-graph's dataset.
