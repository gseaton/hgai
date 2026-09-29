# Mutation Summary

## Intent
Implement Phase 5 of docs/architect/telemetry-20260929061557.md §10: the documentation and disclosure the plan explicitly requires before shipping telemetry as something real customers, including regulated ones, would trust — "the kind of thing a customer's security review will ask for."

## Context
Phases 1-4 built and documented the settings tables incrementally as each phase's settings became real (README.md/configuration.md were kept current throughout, per the established precedent from the earlier storage-aggregation work this session). What remained was the standalone disclosure page itself and completing the settings tables for the two Phase 3a options that were previously listed as reserved/non-functional.

## What Changed and Why
`docs/help/notes/admin/telemetry.md` follows this codebase's existing help-topic conventions exactly (front matter, `help:help-*` cross-references, the same table-driven style as `meshes.md`/`configuration.md`) and is written to answer the actual shipped behavior, not the plan's aspirational text — e.g. it documents the real event schema fields, the real destination-selection logic from `select_exporter`, and the real isolation/retention properties built in Phase 3a, each described precisely enough to match what the code actually does. Every claim in it (what's collected, what's hashed, where it goes, how `__local-telemetry` is isolated) was verifiable against the implementation from the earlier phases in this same session, not just restated from the plan. Cross-links were added from `configuration.md` and `web-ui-tour.md` so the new page is reachable from the places an admin would naturally land first, and `docs/api-reference.md` got a Telemetry section matching its own established per-endpoint documentation style for the two REST endpoints.

## Key Decisions
- Documented behavior, not plan aspiration — e.g. the "toggle" screen is described accurately as a status display with a browse shortcut, matching what Phase 4 actually built, not a literal live toggle the plan's wording could be misread to promise.
- Verified every `help:help-*` cross-reference (including the new page's own outgoing links) against the repository's existing `test_shipped_help_links_and_media_references_resolve` test, which passes — the same correctness bar every other help topic in this project is held to.

## Verification
`python -m pytest tests -q` — 1000 passed (the same 2 pre-existing, unrelated mesh-ping failures deselected as before), including the help-link-resolution and help-topic-parsing tests, which cover the new page directly.
