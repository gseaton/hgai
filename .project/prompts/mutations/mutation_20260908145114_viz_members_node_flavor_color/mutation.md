# Mutation Log

## Modified
- **ui/js/app.js** — In `initViz3D`'s graph-building pass (around line 2372), changed the color assigned to the virtual "members" hub node from `VIZ_LINK_RELATION_COLOR` (amber, set in the prior mutation) to `VIZ_FLAVOR_LINK_COLOR[flavor] || VIZ_STRUCTURAL_COLOR`, matching the color of the "hyperedge" virtual edge (the flavor-typed link from the hyperedge node into the members node). Updated the accompanying comment.
