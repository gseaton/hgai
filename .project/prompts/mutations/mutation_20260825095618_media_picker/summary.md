# Mutation Summary

## Intent
The hypernode/hyperedge editors already let a user upload a brand-new file and attach it in one step (added in an earlier session turn), but there was no way to attach a file that had already been uploaded elsewhere (e.g. via the standalone Media tab, or attached earlier to a different entity) — the user had to re-upload the same bytes to reference them again. The user asked for a way to *reference* already-uploaded media from the node/edge editors, in addition to the existing upload-and-attach path, and asked that both paths store media identically to the standalone Media tab's upload flow.

## Context
This is the latest step in a long-running media-storage feature (Phases 1-4 of `/home/gseaton/.claude/plans/refactored-petting-iverson.md`), followed by UI phases: standalone Media management screen, per-association role/attribute editing, and now this picker. The `media: List[MediaRef]` field on hypernodes/hyperedges and the `POST /media` upload endpoint were already in place; no backend changes were needed for this request.

## What Changed and Why
- Verified first that "store in the same manner" was already satisfied: the existing `handleMediaUpload()` used by the node/edge modals' "Upload & Attach" button calls the exact same `HGAI_API.uploadMedia(file)` client method — and therefore the same `POST /media` backend endpoint and storage backend (GridFS or S3, per config) — as the standalone Media tab's upload modal. No duplication of upload logic existed to consolidate.
- Added the missing capability: a "Browse Existing" button beside "Upload & Attach" in both the Hypernode and Hyperedge modals' Media sections, opening a new picker modal that lists already-uploaded media (reusing `HGAI_API.listMedia`, the same list endpoint the standalone Media tab uses) with search/content-type filtering and pagination.
- Clicking "Attach" on a picker row pushes a `MediaRef` onto the same in-memory `nodeMediaItems`/`edgeMediaItems` arrays that the upload flow already populates, so it flows through the existing `renderMediaList()`, per-association role/attribute editing, and save/refcount logic without any change to those paths.
- Added a duplicate-attach guard (attaching a `media_id` already present in the entity's list shows a warning toast instead of adding a second ref).
- An optional role input in the picker modal lets the user tag the association's role at attach time, mirroring the role input already present on the upload flow.

## Key Decisions
- Reused the existing `PAGINATION_LOADERS` dispatch pattern (`ui/js/app.js`) by registering a `mediaPicker` entry, rather than writing bespoke pagination logic for the picker modal — kept the picker consistent with how Nodes/Edges/Media pagination already works.
- Click-to-attach per row (not a multi-select + bulk-attach UI) — matches the granularity of the existing upload-and-attach flow (one file/one attach action at a time) and keeps the picker modal simple; multi-attach wasn't requested.
- The picker's role input is applied at attach time rather than pre-filled per row, since role is a property of the *association* (this entity's relationship to the file), not of the media file itself — consistent with how `MediaRef.role` is modeled.

## Verification
Live end-to-end verification via a hand-rolled CDP script (driving a headless Chrome instance against a local `mongod` + `python -m hgai.main`, since no browser extension is connected in this environment): for both a hypernode and a hyperedge, exercised "Upload & Attach" (new file) and "Browse Existing" (search, attach with a role, duplicate-attach guard) in the same edit session, saved the entity, confirmed both media refs persisted correctly via a `GET` round-trip, then deleted the entity and both media records (refcount-gated delete succeeding confirms `ref_count` was correctly decremented). Full `pytest` suite re-run: 45 passed, same 3 pre-existing unrelated `test_mesh.py` failures present before this session's changes. `node --check ui/js/app.js` passes. `git status --short` matches the expected file set for this session.
