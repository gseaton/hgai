# Mutation Summary

## Intent
Give telemetry a real, discoverable README section (it previously had only settings-table rows, no prose overview) and make sure the Help system's own cross-reference hubs (home page, glossary, FAQ) point to the telemetry topic written in an earlier turn.

## Context
Phase 5 of docs/architect/telemetry-20260929061557.md wrote the standalone disclosure topic (docs/help/notes/admin/telemetry.md) and updated the settings tables, but README.md never got a matching prose section, and the Help system's three main discovery surfaces (home.md's quick links, the glossary, the FAQ) had no telemetry entries at all — someone browsing Help rather than searching for "telemetry" by name would never find it.

## What Changed and Why
README's new Telemetry section follows the same structure and level of detail as the Help topic (so the two don't drift), but in README's own denser, more technical register — matching how Meshes/SHQL/MongoDB Indexes are already documented there, with real endpoint paths and a runnable SHQL example rather than narrative prose. It was placed under Administration, next to Backup (the closest existing operational-topic neighbor), with a matching Table of Contents entry, an API Reference endpoint block in the same compact style as every other admin-only route group, and a line in both the Web UI screen list and the Architecture directory tree. The three Help-system discovery surfaces got the smallest change each needs to be a genuine path to the topic: one line in home.md's "Run and administer" list, two glossary rows (the feature and the graph it writes to), and one FAQ entry answering the question a security-conscious reader would actually ask first ("does this phone home?").

## Key Decisions
- Kept README's section and the Help topic complementary rather than identical — README is a denser technical reference (endpoints, directory tree, a runnable query), the Help topic is the full narrative disclosure a security review would read end to end. Neither restates the other's full settings table; both point to Configuration for that.
- Did not touch the pre-existing "14 tools" staleness in README's MCP module description — out of scope for this request, noted to the user separately rather than silently fixed or silently left unmentioned.

## Verification
`python -m pytest tests -q` — 1001 passed (the same 2 pre-existing, unrelated mesh-ping failures deselected as before), including `test_shipped_help_links_and_media_references_resolve`, which covers every new `help:help-*` cross-reference added in this turn. Confirmed README's code-fence count stays even (no unclosed block) and the new TOC anchor matches the heading exactly.
