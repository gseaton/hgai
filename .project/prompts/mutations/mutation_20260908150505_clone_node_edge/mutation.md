# Mutation Log

## Modified
- **ui/js/app.js** — `openNodeModal(nodeId, cloneFromId)`: added an optional second parameter. When called as `openNodeModal(null, sourceId)` it fetches the source hypernode, opens the modal in "create" mode with title "Clone of: `<sourceId>`", and pre-fills id (`<sourceId>-copy`, editable), label, type, description, tags, status, valid-from/to, attributes JSON, and media (including default media) from the source. Nothing is saved until the user clicks Save.
- **ui/js/app.js** — `openEdgeModal(edgeId, cloneFromId)`: same pattern for hyperedges — pre-fills id (`<sourceId>-copy`, editable), relation, label, flavor, status, tags, valid-from/to, attributes JSON, member rows, and media (including default media) from the source hyperedge. Nothing is saved until Save is clicked.
- **ui/js/app.js** — Added `window.duplicateNode(id)` and `window.duplicateEdge(id)`, each opening the respective modal in clone mode for the given source id.
- **ui/js/app.js** — Added a "Clone" icon button (`bi-copy`) to each row of the Hypernodes and Hyperedges tables, between the existing Edit and Delete buttons, wired to `duplicateNode(...)` / `duplicateEdge(...)`.
