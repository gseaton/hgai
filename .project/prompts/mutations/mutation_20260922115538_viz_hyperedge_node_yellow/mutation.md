# Mutation Log

## Modified
- **ui/js/app.js** — Added `VIZ_HYPEREDGE_NODE_COLOR = '#eab308'` (yellow). The hyperedge node itself (the "edge:<id>" box, `kind: 'henode'`) now uses this color in both places it's created — the directly-selected graph's own hyperedge nodes, and the cross-graph hyperedge stub node — replacing the prior gray (`VIZ_STRUCTURAL_COLOR`). Inferred hyperedge nodes keep their existing purple (`VIZ_INFERRED_COLOR`), unchanged. All link colors (the flavor-typed hyperedge→members link, relation links, first-member links, the "members" virtual node's color, and the legend's flavor-swatch fallback) are untouched.
