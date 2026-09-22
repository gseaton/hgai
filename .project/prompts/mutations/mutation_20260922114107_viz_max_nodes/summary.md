# Mutation Summary

## Intent
Guard the Visualize screen against an inadvertent render of too many nodes — selecting a large hypergraph (or several at once) could hand 3d-force-graph thousands of nodes and freeze the scene. The user asked for a "Max Nodes" control, default 200, to cap this.

## Context
Visualize already had a server-side per-graph fetch cap (`VIZ_FETCH_LIMIT = 500` nodes and 500 edges per selected graph, existing before this change) with its own truncation toast, but no cap on what actually gets pushed into the 3D scene — which can exceed that per-graph fetch limit when multiple graphs are selected, cross-graph member references pull in additional nodes, inferred edges are shown, or virtual "hyperedge" and "members" nodes are added on top of the raw hypernode/hyperedge counts. That final, fully-merged set is what needed capping, not the per-graph fetch.

## What Changed and Why
The cap is applied once, right after `nodesById` (the de-duplicated map of every node the render would show) is fully built across all selected graphs — so it sees the true final count, not a per-graph or pre-merge approximation. If the count exceeds Max Nodes, the node array is truncated and links are filtered to drop any that would dangle. The one exception is a focused element (Focus / degrees-of-separation): it's always kept even when the cap would otherwise remove it, since focusing on an element only to have the cap discard it would defeat the feature.

Because capping means the rendered set is no longer necessarily "every node considered," the type/flavor legend and the hypernode/hyperedge stat counter were switched from accumulating during graph traversal to being recomputed from the final node array — otherwise the legend counts (used for the clickable type-filter) would silently drift from what's on screen whenever the cap is active.

## Key Decisions
- **Applied after merge, not per-graph or at fetch time**: capping at fetch time would still let N selected graphs each contribute up to the cap, and wouldn't account for cross-graph stub nodes or virtual hyperedge/members nodes added later in the render pipeline. Capping the final merged set is the only point that reflects what's actually about to be drawn.
- **Focus element is exempt from the cap**: verified conceptually — a user setting a low Max Nodes while using Focus wants a small *neighborhood* view, not a coin-flip on whether the very element they're focusing on survives truncation.
- **Verified live in Chrome**: set Max Nodes to 25 against the ~5.5M-record alchemy-cyber-fraud dataset — exactly 25 nodes rendered, links correctly dropped (no dangling references), stats line and legend matched. Reset to the 200 default against the small `eden` graph (25 total nodes, well under the cap) — full hyperedge/members/relation structure rendered identically to before this change, confirming no regression from the legend/stats refactor. No console errors in either case. Full test suite (440 passed) and the Node YAML-highlight suite (13 passed) still pass, both unaffected by this UI-only change.
