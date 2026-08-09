# Mutation Log

## Modified
- **notes/queries.md** — Added a new `## Member Node Attributes (SHQL)` section with two query examples, both in the same `rel:member`/`group:three-stooges` naming already used elsewhere in this file: (1) anchor the edge by `relation` plus a known member (`group:three-stooges`) and expand the other member slot (`?member`) to its full node doc, selecting `?member.id`/`?member.label`/`?member.attributes`; (2) the same member-attribute resolution, but anchoring the edge by its own `id:` directly instead of a known member, using the `edge: id:` filter fixed in the prior turn.
