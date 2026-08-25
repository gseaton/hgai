# Mutation Log

## Modified
- **hgai/models/media.py** — Added `name`, `label`, `description` (all `Optional[str]`) to `Media` and to `MediaUpdate`.
- **hgai_module_storage/filters.py** — Added `name`, `label`, `description` to `MediaPatch`. Updated `MediaFilters.search`'s comment to reflect its broadened matching.
- **hgai_module_storage_mongodb/stores/media.py** — `update()` now applies `name`/`label`/`description` from the patch. `list()`'s `search` filter now matches against `filename`, `name`, `label`, or `description` (was filename-only).
- **hgai_module_storage_mongodb/stores/media_s3.py** — Same two changes as `stores/media.py` (this store duplicates that logic for the S3-backed blob variant).
- **hgai/api/routers/media.py** — `update_media` passes `name`/`label`/`description` through from `MediaUpdate` into `MediaPatch`. Updated the `search` query-param description to match the broadened semantics.
- **ui/index.html** — Added Name/Label/Description fields to the Upload Media modal and the Media Edit modal. Added a "Label" column to the standalone Media table. Updated the media search box and media-picker search box placeholders to mention name/label search.
- **ui/js/app.js** — `loadMedia()` renders the new Label column (bumped `colspan` 8→9 in its loading/empty/error states). `btn-upload-media`/`btn-confirm-upload-media` handlers collect and submit name/label/description on upload (via the same follow-up `updateMedia` call already used for tags/attributes). `editMedia()`/`btn-save-media-edit` populate and persist the three fields. `openMediaPreview()` gained a `label` parameter and now prefers it for the preview modal's title; the standalone table's preview button and the media-picker's preview button now pass `m.label` through.
