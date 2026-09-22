# Mutation Summary

## Intent
Make the hyperedge node (the "edge:<id>" box representing a hyperedge's own identity in the Visualize 3D scene) render as yellow, without changing any of the existing link colors around it.

## Context
The Visualize screen's hyperedge-node color was previously gray (`VIZ_STRUCTURAL_COLOR`, shared with several link-related fallback colors). The color scheme distinguishes several visual roles: the hyperedge node itself, the flavor-typed link from that node to its "members" virtual node, relation-typed links from "members" to each participant, and a separate purple scheme for inferred (computed-live, never-persisted) facts. Only the first of these — the hyperedge node's own fill color — was in scope for this change.

## What Changed and Why
`VIZ_STRUCTURAL_COLOR` was doing double duty: it colored the hyperedge node itself in two code paths (the normal per-graph hyperedge node, and the stub node created when a member reference resolves into another currently-selected graph), and it also served as the *link* color fallback in three other places (the "members" node/its incoming link, and the legend's flavor-swatch fallback). Recoloring `VIZ_STRUCTURAL_COLOR` itself would have changed all of those at once, contradicting "maintain the current link colors." Instead, a new constant (`VIZ_HYPEREDGE_NODE_COLOR`) was introduced and substituted only at the two hyperedge-node creation sites; every link-related use of `VIZ_STRUCTURAL_COLOR` was left exactly as it was.

## Key Decisions
- **Inferred hyperedge nodes were left purple**, not changed to yellow, since that's an existing, separate visual signal ("this was computed live, never persisted") distinct from what the user asked to recolor; the request was read as "the (structural) hyperedge node," consistent with how every other color in this scheme already separates the inferred case out.
- **Verified live in Chrome** against the `eden` graph: read back the rendered `nodes`/`links` arrays from `3d-force-graph`'s data — hyperedge nodes are uniformly `#eab308` (with inferred ones `#c084fc` when "Show inferred edges" is on), while `members`-node colors and every link color are unchanged (`#f97316` hub-orange, `#22c55e` symmetric-green, `#3b82f6` first-member-blue, `#f59e0b` relation-amber, plus the inferred link hues when applicable). Confirmed visually via screenshot. Full test suite still passes (440 passed; this is a UI-only color change with no test coverage of its own).
