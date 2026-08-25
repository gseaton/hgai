# Mutation Log

## Modified
- **ui/index.html** — Added a "Browse Existing" button next to "Upload & Attach" in both the Hypernode and Hyperedge modal Media sections. Added a new `modal-media-picker` modal: search box, content-type filter, optional role input, paginated table of already-uploaded media, and an "Attach" button per row.
- **ui/js/app.js** — Added `State.mediaPickerPage`/`mediaPickerPageSize`; registered `mediaPicker` in `PAGINATION_LOADERS`; added `mediaPickerContext`, `openMediaPicker()`, `loadMediaPicker()`, `attachExistingMedia()` (with a duplicate-attach guard), and wired `btn-node-media-browse`/`btn-edge-media-browse` click handlers plus the picker's search/filter/refresh inputs.
