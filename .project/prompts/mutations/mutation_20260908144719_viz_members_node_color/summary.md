# Mutation Summary

## Intent
The user wants the 3D hyperedge visualization to read more clearly: the virtual "members" hub node that fans a hyperedge out to its participants should visually match the "relation"-labeled links that connect it to those members, rather than blending into the generic gray used for other structural elements.

## Context
The Visualize screen (`ui/js/app.js`) renders each hyperedge as: a hyperedge node → a virtual "hyperedge" edge (colored by flavor) → a virtual "members" node → "relation" edges (colored `VIZ_LINK_RELATION_COLOR`, amber) fanning out to each actual member node. This structure is documented in `docs/architecture/hypergraph-3d-viz.md` and echoed in inline comments near the top of the Visualize section (`ui/js/app.js:1671`). Previously, the members node used `VIZ_STRUCTURAL_COLOR` (gray, `#9ca3af`), the same generic color used for other purely-structural elements, which visually disconnected it from the relation links it anchors.

## What Changed and Why
In the node-construction code for the "members" virtual node (`ui/js/app.js`, in the hyperedge-processing loop inside `initViz3D`), the node's `color` field was changed from `VIZ_STRUCTURAL_COLOR` to `VIZ_LINK_RELATION_COLOR` — the same amber constant already used to color the "relation" links radiating from that node to each member. This makes the hub and its spokes read as one cohesive visual unit (the hub matches the majority of its outgoing links), which is what the user asked for.

## Key Decisions
- `VIZ_LINK_RELATION_COLOR` (not `VIZ_LINK_FIRST_MEMBER_COLOR`, the blue used only for the first/seq-0 member's link) was chosen as the target color since the user referred to "the hyperedge 'relation' link" generically, and the amber color is what the majority of relation edges use — the blue first-member link is a deliberate visual exception to highlight ordering, not "the" relation-link color.
- No change was made to the "hyperedge" virtual edge (hyperedge-node → members-node), which remains colored by flavor per `VIZ_FLAVOR_LINK_COLOR`; that edge encodes a different structural relationship (flavor/topology) and was out of scope for this request.
