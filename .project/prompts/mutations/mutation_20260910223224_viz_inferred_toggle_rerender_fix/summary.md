# Mutation Summary

## Intent
Fix a usability bug the user found in the previous turn's "Show inferred edges" Visualize feature: toggling the checkbox had no visible effect until some other control (e.g. "Hide orphan nodes") was also touched, or the user clicked Render again. The checkbox should behave like every other data-affecting Visualize toggle — changing it should immediately re-render.

## Context
The Visualize screen's filter bar has several toggles. Some (Labels, Media, Auto-rotate) only change display properties on the already-rendered 3d-force-graph instance and don't need a full re-render. Others — like "Hide orphan nodes" — change *which nodes/edges exist in the rendered dataset*, which requires re-running `renderViz()` to actually refetch/rebuild the scene. `renderViz()` already read `#viz-show-inferred`'s checked state correctly (added in the prior turn, confirmed live) to decide whether to fetch and splice in inferred edges — but when that prior turn added the checkbox, it added no accompanying `change` listener to call `renderViz()`, unlike `#viz-hide-orphans`, which has one immediately above where the fix was added. This was a straightforward omission: the read-side of the toggle was wired, the fire-side wasn't.

## What Changed and Why
Added one `change` event listener on `#viz-show-inferred` in `ui/js/app.js`, directly modeled on the existing `#viz-hide-orphans` listener a few lines above it: `if (State.viz3d) renderViz();`. The `State.viz3d` guard matches the existing pattern — avoids triggering a render before the user has ever clicked Render once (i.e., before a 3d-force-graph instance exists).

## Key Decisions
- **Matched the existing `viz-hide-orphans` pattern exactly** rather than inventing a new mechanism, since the two toggles are functionally identical in kind (both change which elements exist in the rendered dataset, as opposed to Labels/Media/Auto-rotate which only change display properties of already-rendered elements).

## Live Verification Performed
Started an isolated test server (`HGAI_MONGO_DB=hgai_viz_infer_fix HGAI_PORT=8399`) and seeded the same `vizinfer` hypergraph fixture as the original feature verification (axiom hyperedge `skos:narrowerTransitive` over `[rel:parent, rel:father]`, fact hyperedge `rel:father` over 3 members). In the browser:
1. Selected the graph, rendered with "Show inferred edges" OFF — panel showed "5 hypernodes · 2 hyperedges".
2. Toggled "Show inferred edges" ON *without* touching any other control or clicking Render again — the graph immediately re-rendered, panel updated to "5 hypernodes · 3 hyperedges", and the purple inferred henode appeared.
3. Toggled it back OFF, again without any other interaction — the graph immediately re-rendered back to "5 hypernodes · 2 hyperedges", removing the inferred edge.

Both directions confirmed fixed. Test server killed and `hgai_viz_infer_fix` database dropped afterward. Full test suite: 72 passed (unchanged — this fix is JS-only), same 3 pre-existing unrelated `test_mesh.py` failures.
