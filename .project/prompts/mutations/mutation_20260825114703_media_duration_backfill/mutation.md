# Mutation Log

## Modified
- **hgai_module_storage/backend.py** — Added `set_duration(media_id, duration_seconds)` as a new abstract method on `MediaStore`, deliberately separate from the existing `update()`/`MediaPatch` path since duration is a backend-computed field, never a user-editable one.
- **hgai_module_storage_mongodb/stores/media.py** — Implemented `set_duration()` (plain `$set` on `duration_seconds`, no version bump — this is enrichment, not a user edit).
- **hgai_module_storage_mongodb/stores/media_s3.py** — Same `set_duration()` implementation (identical, since both stores share the same Mongo `media` metadata collection).
- **hgai/core/media.py** — Added `backfill_media_durations(limit=1000)`: scans existing media for audio/video records missing `duration_seconds`, reads each one's full blob, runs the existing `extract_media_duration()` on it, and calls the store's new `set_duration()` for any that resolve successfully. Returns `{"scanned": N, "updated": N}`.
- **hgai/api/routers/media.py** — Added `POST /media/backfill-duration` (admin-only, mirrors the existing `POST /media/sweep-orphaned` pattern), and the corresponding import.
