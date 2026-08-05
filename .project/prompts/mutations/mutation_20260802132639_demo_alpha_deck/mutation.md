# Mutation Log

## Created
- **docs/decks/demo-alpha/deck-demo-alpha.md** — Full markdown slide deck (14 slides/phases) walking an engineer from a clean HypergraphAI install through hypergraph creation, bulk data import, the Web UI, HQL filter/aggregate queries, point-in-time temporal queries, SHQL pattern-matching (multi-hop joins, FILTER, OPTIONAL, UNION), MCP tool access for AI agents, optional Spaces/RBAC, and an honest live-vs-roadmap breakdown of the inferencing engine. Every command and query result quoted in the deck was executed against a real running server while authoring it.
- **docs/decks/demo-alpha/data/acme-eng-import.yaml** — Bulk-import dataset (24 hypernodes, 23 hyperedges) modeling a fictional "Acme Robotics" engineering org: 3 teams, 7 people, 5 skills, 2 projects, and 6 semantic RelationType nodes. Includes deliberately temporal team-roster edges (Dana Kim's move from the Perception team to the Platform team, versioned via `valid_from`/`valid_to`) to drive the point-in-time demo phase.
- **docs/decks/demo-alpha/queries/q01-list-people.hql** — HQL: list all Person hypernodes.
- **docs/decks/demo-alpha/queries/q02-team-membership-history.hql** — HQL: all historical versions of the Perception team's roster edge (no `at:` clause).
- **docs/decks/demo-alpha/queries/q03-team-roster-pit.hql** — HQL: same roster query pinned to a point in time (`at: 2023-06-01`).
- **docs/decks/demo-alpha/queries/q04-where-numeric.hql** — HQL: numeric `$lte` WHERE operator on `attributes.hired_year`.
- **docs/decks/demo-alpha/queries/q05-where-boolean-or.hql** — HQL: `$or` boolean pass-through over hyperedge `relation`.
- **docs/decks/demo-alpha/queries/q06-members-node-id-in.hql** — HQL: `members.node_id $in [...]` (edges touching either of two people).
- **docs/decks/demo-alpha/queries/q07-members-node-id-all.hql** — HQL: `members.node_id $all [...]` (edge containing both people).
- **docs/decks/demo-alpha/queries/q08-people-and-teams.shql** — SHQL: multi-hop join of people to their team-roster edges via a shared `?person` variable.
- **docs/decks/demo-alpha/queries/q09-skills-lookup.shql** — SHQL: full person↔skill matrix, expanding a hub edge's multiple skill members.
- **docs/decks/demo-alpha/queries/q10-staffing-by-project.shql** — SHQL: project staffing roster via double-anchored member matching.
- **docs/decks/demo-alpha/queries/q11-filter-hired-before-2021.shql** — SHQL: `filter:` expression on a numeric attribute.
- **docs/decks/demo-alpha/queries/q12-optional-mentor.shql** — SHQL: `optional:` left-outer-join pattern for mentorship.
- **docs/decks/demo-alpha/queries/q13-union-python-or-lead.shql** — SHQL: `union:` of two independent pattern branches with `distinct: true`.
- **docs/decks/demo-alpha/queries/q14-pit-team-roster.shql** — SHQL: point-in-time query equivalent to q03, expressed as a pattern match.
