# Mutation Log

## Modified
- **ui/index.html** — Added a "Clear" button (`#btn-viz-clear`, `btn-outline-danger`) between the existing "Fit" and "Render" buttons in the Visualize screen's header.
- **ui/js/app.js** — Added `vizClear()`: empties the `3d-force-graph` instance's data (`graphData({ nodes: [], links: [] })`), clears the DOM label-overlay layer (`vizClearLabelLayer()`), clears the legend and stats badge, clears the search input, resets the Element Details panel to its empty state (`vizClearDetail()`), and restores the empty-state placeholder (with its original "Select one or more hypergraphs and click **Render**..." message) so the canvas returns to its pre-render appearance. Wired `#btn-viz-clear`'s click to `vizClear`. The hypergraph multi-select, status filter, and Labels/Auto-rotate toggles are left untouched — Clear resets the *rendered scene*, not the user's chosen filters.
