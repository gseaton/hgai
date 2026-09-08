# Mutation Log

## Modified
- **ui/js/app.js** — In `initViz3D`'s graph-building pass (around line 2370), changed the color assigned to the virtual "members" hub node from `VIZ_STRUCTURAL_COLOR` (gray) to `VIZ_LINK_RELATION_COLOR` (amber), matching the color already used for the relation-labeled links fanning out from that node. Added a short comment explaining why.
