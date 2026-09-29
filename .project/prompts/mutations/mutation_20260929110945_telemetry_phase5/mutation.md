# Mutation Log

## Created
- **docs/help/notes/admin/telemetry.md** — The disclosure help topic the plan's §5.7 calls for: what is collected (the full event shape), what is never collected (content, chat, media, vendor keys — matched against §5's hard privacy rule), how account/graph/space ids are hashed and how to opt out of that, destination selection (external / local / both) and the HTTPS requirement, `__local-telemetry`'s isolation and retention, and a step-by-step for turning it on.

## Modified
- **README.md**, **docs/help/notes/admin/configuration.md** — Added the two Phase 3a settings (`HGAI_TELEMETRY_LOCAL_ENABLED`, `HGAI_TELEMETRY_LOCAL_RETENTION_DAYS`) to the settings tables, completing what Phase 1 deliberately left out while they were still non-functional; `configuration.md` also cross-links to the new telemetry page.
- **docs/help/notes/web-ui/web-ui-tour.md** — Added the "Telemetry" admin screen row to the screen tour table.
- **docs/api-reference.md** — Added a "Telemetry" section documenting `GET /telemetry/status` and `POST /telemetry/ingest` (request shape, field constraints, a worked example), matching the existing per-endpoint documentation style.
