# Mutation Log

## Modified
- **ui/js/app.js** —
  - Added `VIZ_LINK_FIRST_MEMBER_COLOR = '#3b82f6'` (blue) alongside the existing edge-kind color constants.
  - `initViz3D()`: `.linkWidth()` for `relation`-kind links reduced from `1.4` to `1.0` (the `hyperedge`-kind links stay at `0.8`, unchanged).
  - `renderViz()`: the `validMembers.forEach(...)` loop building each hyperedge's relation-links now uses the loop index — the first member (`i === 0`, i.e. lowest `seq`, since `validMembers` is already sorted by `seq`) gets `color: VIZ_LINK_FIRST_MEMBER_COLOR`; every other member keeps `VIZ_LINK_RELATION_COLOR` (amber).
  - `buildVizLegend()`: added a third edge-kind legend row, `"rel:* edge (first member)"` in blue, alongside the existing flavor/relation entries.
