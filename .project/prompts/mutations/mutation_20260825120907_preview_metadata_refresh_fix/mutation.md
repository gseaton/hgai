# Mutation Log

## Modified
- **hgai_module_storage/filters.py** — Added `id: Optional[str]` to `MediaFilters`, an exact-match filter distinct from the existing free-text `search`.
- **hgai_module_storage_mongodb/stores/media.py** — `list()` applies `filters.id` as an exact `{"id": ...}` match when present.
- **hgai_module_storage_mongodb/stores/media_s3.py** — Same `filters.id` handling in `list()`.
- **hgai/api/routers/media.py** — Added an `id` query param to `GET /media`, threaded into `MediaFilters`, so a single record's authoritative metadata can be fetched by exact id via the existing list endpoint (`GET /media?id=<id>&limit=1`) rather than adding a new route.
- **ui/js/app.js** — Added `fetchMediaMetadata(mediaId)` (returns the authoritative `Media` record for a local, non-mesh-qualified id, or `null` on any failure/mesh-id). `openMediaPreview()` now renders immediately from whatever `info` it was called with (so the modal opens instantly with no visible delay), then — in parallel with the media blob fetch already happening for the player — fetches the authoritative record and, if found, re-renders the title, download button, and metadata table from it, overriding anything stale in the originally-passed `info`.
