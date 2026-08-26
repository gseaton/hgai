# Mutation Summary

## Intent
Every hyperedge in the 3D visualization gets a synthetic "members" node (the fan-out point between the hyperedge's own identity node and its participants) that was labeled with the literal text "members" in a floating DOM overlay. With many hyperedges on screen, that's the same repeated, information-free word cluttering the view once per hyperedge — the user wanted it gone.

## Context
`vizBuildLabelLayer()` builds one DOM `<div>` label per node in the graph (positioned every frame via `vizLabelTick()`'s camera-projection math) — hypernodes, hyperedge identity nodes, and these virtual "members" nodes were all treated identically before this change, each getting a label styled via `.viz-label-node`, with `.viz-label-virtual` (green-tinted) as the only distinguishing treatment for the members variant. The node still carries a real, informative hover tooltip (`nodeLabel` in `initViz3D()`, unchanged by this fix) that explains it's a virtual node representing the member set — so removing the persistent overlay label doesn't remove the ability to identify what it is, just the always-visible clutter.

## What Changed and Why
- The label element is now skipped entirely for `kind === 'members'` nodes, rather than created and then hidden or left with empty text — there's no reason to pay the cost of creating, tracking (`vizLabelNodeEls`), and per-frame-positioning a DOM element that would never show anything.
- Removed the `.viz-label-virtual` CSS rule alongside it, since it styled exactly the label this change eliminates and had no other use.

## Verification
Live end-to-end verification via a hand-rolled CDP script against the already-running dev server (frontend-only change, no restart needed) and a freshly-created headless Chrome profile (learned from the previous turn: reusing a profile across a session risks a stale cache of the pre-fix file). Rendered the real `hello-world` graph and confirmed via `State.viz3d.graphData()` and `vizLabelNodeEls`: 14 "members"-kind nodes exist, 0 of them have a label element; the total label-element count (32) exactly matches the combined hypernode+hyperedge count, with no leftover or leaked members labels; a DOM scan of the label layer found zero elements with literal "members" text. Confirmed no regression — real hypernode and hyperedge labels are still present — and confirmed the hover tooltip accessor is untouched. Full `pytest` suite: 45 passed, same 3 pre-existing unrelated `test_mesh.py` failures as before this change (unaffected — frontend-only). `node --check ui/js/app.js` passes. Left the dev server running afterward and killed only the headless Chrome test instance. `git status --short` shows `ui/js/app.js` and `ui/css/hgai.css` as this turn's changes.
