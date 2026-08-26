# Mutation Log

## Modified
- **ui/js/app.js** (`vizBuildLabelLayer()`) — The virtual "members" node (the synthetic per-hyperedge node fanning out to its participants) no longer gets a DOM label element created at all — skipped entirely rather than rendered with empty/hidden text. `hnode`/`henode` labeling is unchanged.
- **ui/css/hgai.css** — Removed the now-unused `.viz-label-node.viz-label-virtual` rule (the distinct green styling previously applied only to the "members" label, which no longer exists).
