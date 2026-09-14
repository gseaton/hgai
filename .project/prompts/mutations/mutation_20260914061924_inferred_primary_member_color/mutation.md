# Mutation Log

## Modified
- **ui/js/app.js** — Added the `VIZ_INFERRED_FIRST_MEMBER_COLOR = '#f472b6'` (pink) constant beside `VIZ_INFERRED_COLOR`, with a comment explaining it is the inferred-edge counterpart to `VIZ_LINK_FIRST_MEMBER_COLOR`. In `renderViz()`'s `validMembers.forEach((m, i) => ...)` loop, the relation-link `color` expression now applies the first-member distinction on inferred edges too: `i === 0` gets pink, the rest keep `VIZ_INFERRED_COLOR`; literal edges are unchanged (blue / amber). Updated the preceding comment block to describe the new two-tier inferred scheme. In `buildVizLegend()`, the `anyInferred` branch appends a second row, "⚡ inferred (first member)", with a pink swatch and a title tooltip.
