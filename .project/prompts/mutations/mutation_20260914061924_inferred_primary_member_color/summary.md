# Mutation Summary

## Intent
In the 3D visualizer, literal hyperedges already distinguish their PRIMARY member (`members[0]`, lowest `seq`) by coloring that one relation-link blue while the remaining member links are amber. Inferred hyperedges lost that distinction: every part of an inferred edge's complex — henode, members-node, `flavor:*` link, and *all* relation-links — was painted the single inferred purple (`#c084fc`), so there was no way to tell which member was primary. The user asked for a distinct color (pink suggested) on the inferred edge's primary-member link.

## Context
- All viz colors live as module-level constants near the top of the viz section of `ui/js/app.js` (~line 2499 onward), each with a comment explaining what the color encodes.
- The inferred-edge rendering (added in `mutation_20260910215722_viz_inferred_rendering`) deliberately threads a single `_inferred` boolean and a single color constant through the *existing* generic node/link construction pipeline rather than adding a parallel rendering path. The prior design note explicitly said the whole inferred complex should read as one unit regardless of flavor.
- The first-member-blue behavior (added in `mutation_20260824183753_3d_viz_first_member_color`) keys off the loop index `i === 0` of the already-`seq`-sorted `validMembers` array — no separate data field exists for "primary member."
- Link `color` drives both the WebGL line and the DOM-overlay label's text color, so a single color change propagates everywhere automatically.

## What Changed and Why
One new constant and one ternary change carry the whole feature:

1. `VIZ_INFERRED_FIRST_MEMBER_COLOR = '#f472b6'` was added immediately after `VIZ_INFERRED_COLOR`, so the two inferred hues sit together and the relationship between them is obvious to the next reader.
2. The relation-link `color` expression in the `validMembers.forEach((m, i) => ...)` loop went from a flat "inferred ⇒ purple" to a nested ternary that mirrors the literal-edge scheme inside the inferred branch: `e._inferred ? (i === 0 ? pink : purple) : (i === 0 ? blue : amber)`. Reusing the existing `i === 0` test means the definition of "primary" stays identical for literal and inferred edges — no new data field, no risk of the two notions of "first member" drifting apart.
3. `buildVizLegend()` gained a second row inside the existing `anyInferred` branch so the new color is discoverable, matching how the literal scheme already documents both `rel:* edge` and `rel:* edge (first member)`.

Deliberately *not* changed: the inferred henode, members-node, and `flavor:*` hyperedge link all still use the single `VIZ_INFERRED_COLOR`. Only the primary-member relation-link differs, which is the minimum needed to convey ordering while preserving the original "this whole complex was computed live" read.

## Key Decisions
- **Pink (`#f472b6`) rather than reusing the literal blue `#3b82f6`**: reusing blue would make an inferred edge's primary link indistinguishable from a literal edge's, destroying the inferred/persisted distinction that was the entire point of the purple. Pink is hue-adjacent to the inferred purple, so the complex still visually coheres as "the inferred family" while the primary member pops out of it. It also does not collide with any existing viz constant (`VIZ_TYPE_PALETTE` contains `#db2777`/`#c026d3`, which are noticeably deeper magentas, and type colors appear on spheres, not links).
- **Nested ternary over a lookup table**: only two axes with two values each; a table or helper function would be more indirection than the four-case expression it replaces, and the symmetry of the two branches makes the parallel between the literal and inferred schemes self-documenting.
- **Legend row added rather than repurposing the existing one**: the existing "⚡ inferred" swatch still accurately describes the majority of the complex, so a second row is additive and non-breaking rather than a redefinition.
