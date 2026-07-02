# Mutation Summary

## Intent
Make the ID value in each row of the Hypergraphs, Hypernodes, and Hyperedges list tables act as a shortcut to open the edit modal for that entity, matching the behaviour of the pencil icon button already present in the actions column.

## Context
Each table row already has an actions column with view/edit/delete icon buttons. The ID column displayed a `<code>` element with no interactivity. The edit functions (`editGraph`, `editNode`, `editEdge`) are already defined as global `window.*` functions in app.js and accept the same arguments used by the existing edit buttons.

## What Changed and Why
- **app.js**: The first `<td>` in each row renderer (Hypergraphs, Hypernodes, Hyperedges) was given `class="table-id-link"` and an `onclick` handler that calls the same edit function with the same arguments as the pencil button in the same row. No new functions were introduced — the onclick reuses the existing `editGraph`/`editNode`/`editEdge` window globals.
- **hgai.css**: `.table-id-link` styles the cell with `cursor: pointer` and renders the `<code>` child in the app's primary indigo color with a dotted underline at rest, switching to solid underline and darker shade on hover. This gives users a clear affordance that the ID is interactive without disrupting the table layout.

## Key Decisions
- **onclick on the `<td>` rather than wrapping in `<a>`**: Consistent with how the meshes screen already handles row-level clicks; avoids nesting interactive elements and keeps the template strings clean.
- **Dotted underline at rest, solid on hover**: Signals interactivity without being as visually noisy as a permanent solid underline across every ID in the table.
