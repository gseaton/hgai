# Mutation Log

## Modified
- **ui/js/app.js** — Added `class="table-id-link"` and `onclick="editGraph(...)"` to the ID `<td>` in the Hypergraphs row renderer (line ~364). Added the same pattern with `onclick="editNode(...)"` to the Hypernodes row renderer (line ~523). Added `onclick="editEdge(...)"` to the Hyperedges row renderer (line ~735). Each uses the same arguments already passed to the pencil-icon edit buttons in the same row.
- **ui/css/hgai.css** — Added `.table-id-link` CSS block: `cursor: pointer` on the cell, primary-colored dotted underline on the `<code>` child, and a solid underline + darker color on hover.
