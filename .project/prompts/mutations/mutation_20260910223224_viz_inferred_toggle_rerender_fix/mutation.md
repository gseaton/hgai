# Mutation Log

## Modified
- **ui/js/app.js** — Added a `change` event listener on `#viz-show-inferred` (right after the existing `#viz-hide-orphans` listener) that calls `renderViz()` when the graph is already rendered (`if (State.viz3d) renderViz();`), mirroring the pattern already used for `viz-hide-orphans`. The checkbox itself and the `renderViz()` logic that reads it were already correct; only the missing event wiring was added.
