# Mutation Log

## Modified
- **hgai_module_telemetry/events.py** — Added `SYSTEM_ACTOR`, `actor_of()`, and an `actor` field in `build_event` output.
- **tests/test_telemetry.py** — Updated event-shape test for the `actor` key; asserts `__system` for no account and the id for an account.
- **docs/architect/telemetry-20260929061557.md** — Added `actor` to the example event JSON.
- **docs/help/notes/admin/telemetry.md** — Added `actor` row to the collected-fields table.
