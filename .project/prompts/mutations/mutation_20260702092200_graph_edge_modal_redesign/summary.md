# Mutation Summary

## Intent
Bring the Hypergraph and Hyperedge editor modals into visual parity with the already-redesigned Hypernode modal, applying the same structural and aesthetic patterns: styled header with entity badge, sectioned form body with bold uppercase section headers, bold field labels, dark JSON attributes editor, and a consistent footer.

## Context
The Hypernode modal had been redesigned in a prior session with: a colored gradient header, an icon badge, a subtitle, form sections separated by dividers with uppercase labels, bold `.form-label` styling, and a dark-themed `.node-attributes-editor` textarea. The `node-form-section*` CSS classes were already defined. The graph and edge modals still used the original flat Bootstrap layout with no sectioning.

## What Changed and Why

**Hypergraph modal (`#modal-graph`):**
- Header: indigo gradient background matching the app's primary color (used for hypergraph icons/buttons throughout the UI), indigo icon badge with `bi-diagram-3-fill`, subtitle.
- Body: sectioned into Identity (Space, ID, Label, Type, Description), Classification (Tags), Attributes (JSON).
- Description changed from `<textarea>` to `<input type="text">` — consistent with the Hypernode modal, where description is a short single-line field.
- ID input gained `font-monospace` class — consistent with Hypernode.
- Attributes textarea uses the existing `node-attributes-editor` class for the dark code theme.
- Footer consolidated with the shared footer rule.

**Hyperedge modal (`#modal-edge`):**
- Header: cyan gradient matching the info color used for hyperedge icons/buttons throughout the UI, cyan icon badge with `bi-share-fill`, subtitle.
- Body: sectioned into Identity (Hypergraph, ID, Relation, Flavor, Label), Classification (Status, Tags), Temporal Validity, Members, Attributes.
- Hypergraph select/display rows changed from `col-md-6` to `col-12` — same as the Hypernode modal, since the selector needs full width to show long graph names.
- `#edge-graph-display` gained `node-graph-display-field` class for the styled muted display field.
- Members section lifted out of the flat grid into its own `node-form-section` with a section header and hint.
- `btn-add-member` changed from `btn-outline-primary` (indigo) to `btn-outline-info` (cyan) to match the edge entity color identity.
- Attributes textarea uses the existing `node-attributes-editor` class.

## Key Decisions
- **Reused `node-form-section*` classes across all three modals**: The classes are named for the node modal but are purely structural/typographic with no color, so they apply universally without creating redundant CSS.
- **Entity badge colors follow the existing UI color identity**: Graph=indigo (primary), Node=green (success), Edge=cyan (info) — matching the icons and button colors already used in the list screens and topbar.
- **Footer rule consolidated**: The three modal footers share identical padding/background/border, so they were collapsed into one CSS rule instead of three.
- **All element IDs preserved**: 12 graph modal IDs and 21 edge modal IDs verified unchanged so existing JS handlers require no modification.
