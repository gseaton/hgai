# Mutation Summary

## Intent
The user revised their earlier request: instead of the virtual "members" node in the 3D hyperedge visualization matching the "relation" links (its outgoing spokes to member nodes), they now want it to match the "hyperedge" link's flavor color (its incoming link from the hyperedge node) — the link labeled `flavor:<flavor>` that connects the hyperedge node to the members hub.

## Context
The Visualize screen (`ui/js/app.js`) renders each hyperedge as: hyperedge node → "hyperedge" virtual edge (colored by `VIZ_FLAVOR_LINK_COLOR[flavor]`, e.g. orange for hub, green for symmetric, etc.) → "members" virtual node → "relation" edges (amber, `VIZ_LINK_RELATION_COLOR`) fanning out to each member. In the immediately preceding session, the members node's color had just been changed from the generic gray `VIZ_STRUCTURAL_COLOR` to `VIZ_LINK_RELATION_COLOR` to match the relation edges. This request supersedes that: the user now wants the node to instead continue the color of the flavor-typed link feeding into it.

## What Changed and Why
In the "members" node construction (`ui/js/app.js`, inside the hyperedge-processing loop in `initViz3D`), the `color` field was changed from the flat `VIZ_LINK_RELATION_COLOR` constant to `VIZ_FLAVOR_LINK_COLOR[flavor] || VIZ_STRUCTURAL_COLOR` — the exact same expression already used a few lines below for the "hyperedge" link's color. Since `flavor` is already resolved earlier in the loop (`const flavor = e.flavor || 'hub';`), no new lookups were needed. This makes the members hub's color vary per-hyperedge by flavor (hub/symmetric/direct/transitive/inverse-transitive) rather than being a single fixed amber, visually continuing the incoming flavor link's color into the hub node.

## Key Decisions
- Reused the flavor-color lookup verbatim (including its `VIZ_STRUCTURAL_COLOR` fallback for unrecognized flavors) rather than introducing a new constant, keeping the members-node color guaranteed to stay in sync with the "hyperedge" link's color if `VIZ_FLAVOR_LINK_COLOR` is ever edited.
- Left the "relation" links' amber color (`VIZ_LINK_RELATION_COLOR`) untouched — this request only concerned the members node's own color, not its outgoing edges.
