# Mutation Log

## Modified
- **docs/decks/demo-alpha/queries/q09-skills-lookup.shql** — Replaced `{ bind: "?person", id: "?person" }` with plain `{ bind: "?person" }` in the has-skill edge's member pattern; updated the accompanying comment to describe the current (post-fix) anchoring behavior instead of the old workaround.
- **docs/decks/demo-alpha/queries/q10-staffing-by-project.shql** — Replaced `{ bind: "?project", id: "?project" }` and `{ bind: "?person", id: "?person" }` with plain `{ bind: "?project" }` / `{ bind: "?person" }`; updated the comment similarly.
- **docs/decks/demo-alpha/queries/q13-union-python-or-lead.shql** — Replaced `{ bind: "?person", id: "?person" }` with `{ bind: "?person" }` in the UNION's first branch.
- **docs/decks/demo-alpha/deck-demo-alpha.md** — Updated the q09, q10, and q13 YAML code blocks in Phase 6/7 to match the simplified query files; rewrote the "Practical tip — anchoring an already-bound variable" callout to describe the engine's current behavior (already-bound `bind` variables are automatically treated as anchors) rather than instructing readers to manually repeat a variable as both `bind` and `id`.
