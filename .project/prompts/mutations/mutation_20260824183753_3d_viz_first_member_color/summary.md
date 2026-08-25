# Mutation Summary

## Intent
A small refinement to the 3D Visualize tab (built up over the preceding several mutations): make the "members" hub's relation-links slightly thinner, and give the first member of each hyperedge (by `seq` order) a visually distinct color so it stands out from the rest of that hyperedge's members.

## Context
Each hyperedge's members-node fans out to one `relation`-kind link per member, all previously colored a uniform amber (`VIZ_LINK_RELATION_COLOR`, `#f59e0b`) per the reference-diagram-driven redesign in the prior mutation. `EdgeMember.seq` (in `hgai/models/hyperedge.py`) already carries an explicit ordering — "sequence position within the edge" — and `renderViz()` already sorts each hyperedge's members by `seq` before building links (`validMembers`), so "the first member" has a well-defined, pre-existing meaning here: `validMembers[0]`.

## What Changed and Why
- **Thinner relation links**: width dropped from `1.4` to `1.0` in the `.linkWidth()` accessor, a simple visual tweak with no data-model implications — reduces visual weight/clutter in denser scenes.
- **First-member link colored blue**: rather than introducing a new data field, the existing `i === 0` position in the already-`seq`-sorted `validMembers.forEach((m, i) => ...)` loop is used directly to pick the link's `color` — `VIZ_LINK_FIRST_MEMBER_COLOR` (`#3b82f6`, blue) for the first, `VIZ_LINK_RELATION_COLOR` (amber) for the rest. Since link color already drives both the WebGL line and (per the immediately preceding mutation) the DOM-overlay label's text color, this one change automatically applies consistently everywhere a relation-link's color is read — no other code paths needed touching.
- **Legend updated** with a third entry ("rel:* edge (first member)" in blue) so the new color's meaning is discoverable rather than a mystery highlight.

## Key Decisions
- **No new "isFirst" data field** — reused the loop index against the already-sorted `validMembers` array directly, since the sort order was already exactly "by seq ascending" and nothing else in the codebase needed a persisted "first member" flag.
- **Verification**: reused the CDP-over-headless-Chrome harness (still no Claude-in-Chrome extension in this environment) against the seeded `hello-world` graph (4 hyperedges). Confirmed: exactly one blue relation-link per hyperedge and all others amber, in every one of the 4 hyperedges individually (not just in aggregate); `linkWidth` reports `1.0` for relation-links vs. `0.8` for hyperedge-links; a screenshot visually confirms one distinct blue arc per "members" hub. Zero console errors. Test infrastructure (local mongod, the hgai server process, headless Chrome) was torn down afterward.
