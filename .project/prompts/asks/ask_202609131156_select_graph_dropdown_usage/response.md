# Response Summary

## Question / Intent
The user wanted to know whether the "— Select Graph —" dropdown in the topbar (top-right corner of the UI) is still used by anything, and to have it removed if it turns out to be dead.

## Answer / Recommendation
It's actively used — not dead code, and not safe to remove. It's `#active-graph-select` (`ui/index.html:94`, inside `#topbar`, positioned top-right via `ms-auto`), and it's the single global source of truth for `State.activeGraphId`, which the Hypernodes and Hyperedges screens depend on throughout: the default graph when navigating to either screen, which graph a new node/edge is created in, clone-from behavior, delete operations, and pre-filling each screen's edit modals with the right graph context.

It's kept in a three-way sync with those two screens' own local graph selects (`#nodes-graph-select`, `#edges-graph-select`, `ui/index.html:220,290`): each of the three has a `change` listener (`ui/js/app.js:225-231,276-282,300-...`) that sets `State.activeGraphId` and pushes the same value into the *other two* selects' `.value`. Because the topbar dropdown is the only one of the three visible on every screen (the other two only exist inside their own screens), it's specifically what lets a user pick a graph while on the Dashboard, Notes, Media, or any other screen, so it's already selected by the time they navigate to Hypernodes or Hyperedges.

## Key Points
- `State.activeGraphId` (set/read via this dropdown) appears in roughly 30 distinct places across `ui/js/app.js`, spanning `loadNodes()`, `loadEdges()`, `openNodeModal()`, `openEdgeModal()`, node/edge clone logic, node/edge delete handlers, and `graphSpaceId()` (used to decide whether a space-scoped or unowned API endpoint is called) — confirmed via a direct grep across the file, not inferred from a partial read.
- Removing the dropdown would remove the only way to set the active graph from outside the Hypernodes/Hyperedges screens themselves, and would require reworking the three-way sync (or accepting that `State.activeGraphId` becomes unset until a user lands on one of those two screens and picks from the local select there) — a real workflow change, not a safe no-op deletion.
- No changes were made — this was a pure investigation, and the answer came back "still in active use," so removal wasn't warranted.

## Context
None beyond the direct code investigation described above — no prior session context bore on this question.
