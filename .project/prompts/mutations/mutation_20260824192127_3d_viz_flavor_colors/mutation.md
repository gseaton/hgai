# Mutation Log

## Modified
- **ui/js/app.js** —
  - Replaced the single `VIZ_LINK_HYPEREDGE_COLOR` constant with `VIZ_FLAVOR_LINK_COLOR`, a map from `EdgeFlavor` value to color: `hub` → gold `#d4af37`, `symmetric` → green `#22c55e`, `direct` → cyan `#06b6d4`, `transitive` → violet `#8b5cf6`, `inverse-transitive` → rose `#f43f5e`.
  - `renderViz()`: the "hyperedge" virtual link's `color` is now `VIZ_FLAVOR_LINK_COLOR[flavor] || VIZ_STRUCTURAL_COLOR` instead of the previous fixed magenta; reintroduced the `flavorSeen` tracking `Set` (populated alongside `hyperedgeCount++`) that had been removed in the prior mutation.
  - `buildVizLegend(typeCount, flavorSeen)`: signature reverted from `(typeCount, showEdgeKey: boolean)` back to taking the `flavorSeen` set directly; now renders one legend row per flavor actually present (swatch colored via `VIZ_FLAVOR_LINK_COLOR`, labeled `flavor:<flavor>`), followed by the existing static `rel:* edge` (amber) and `rel:* edge (first member)` (blue) rows whenever at least one hyperedge was rendered.
  - Call site updated: `buildVizLegend(typeCount, hyperedgeCount > 0)` → `buildVizLegend(typeCount, flavorSeen)`.
