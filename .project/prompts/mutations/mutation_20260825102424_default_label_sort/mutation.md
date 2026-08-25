# Mutation Log

## Modified
- **hgai/api/routers/hyperedges.py** — Added `"label"` to `EDGE_SORT_FIELDS`, making hyperedge listing sortable by `label` (the field already existed on the model but wasn't exposed for sorting or display).
- **ui/index.html** — Added a sortable "Label" column (`data-sort-field="label"`) to the Hyperedges table, positioned after ID and before Relation.
- **ui/js/app.js** — Changed `State.nodesSort`/`State.edgesSort` initial values from `[]` to `[{ field: 'label', dir: 'asc' }]` so both tables default to label-ascending on first load. Added a `<td>` rendering `e.label` in the Hyperedges row template and bumped the table's `colspan` from 7 to 8 in the three places it's hardcoded (loading/empty/error states). Applied `escapeHtml()` to `e.id`, `e.label`, `e.relation`, and `e.flavor` in that same row template (previously unescaped, free-form user-controlled text interpolated raw into `innerHTML` — fixed proactively while touching this template).
