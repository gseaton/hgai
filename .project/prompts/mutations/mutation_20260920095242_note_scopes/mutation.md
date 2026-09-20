# Mutation Log

## Modified
- **hgai/models/note.py** — Added `NoteScope` (private, protected, protected-edit, public, public-edit); `scope` on `NoteBase` (default `protected`, so pre-scope notes read as before) with `NoteCreate` overriding the default to `private`; `my_access` on `NoteResponse`; `SetNoteScopeRequest`.
- **hgai/core/notes.py** — Added `note_access` (owner/editor/viewer/None from scope + share list); `can_view_note`/`can_edit_note` now derive from it; `list_notes_visible_to` gained `scope`/`owner_username` filters; new `set_note_scope` (own `scope` audit mutation); `share_note` promotes a private note to protected; `scope` added to tracked fields.
- **hgai/api/routers/notes.py** — Responses include `my_access`; list accepts `scope` and `owner`; `scope` is sortable; new `PUT /notes/{id}/scope` (owner/admin only); share info returns `scope`.
- **hgai_module_storage/filters.py** — `NoteFilters.scope`/`owner_username`; `NotePatch.scope`.
- **hgai_module_storage_mongodb/stores/notes.py** — Visibility query now = owner OR public scope OR (on share list AND scope != private); scope filter treats a missing scope as `protected`; `scope` is patchable.
- **hgai_module_storage_mongodb/indexes.py** — Added `scope` index on `notes`.
- **ui/index.html** — Notes list: Scope column, scope and owner filters; note modal: Scope select with help text and a Browse-view owner/scope line; share modal: current scope and hint.
- **ui/js/api.js** — `setNoteScope`.
- **ui/js/app.js** — Scope badges/descriptions; `noteCanEdit`/`noteIsOwner` use the server's `my_access`; list shows Scope and "(you)", scope/owner filters, view-only icon; modal scope select (owner/admin-only, saved via the scope endpoint, chosen on create); share modal shows/keeps scope in step.
- **tests/test_notes.py** — Scope access matrix, legacy-note default, create defaults, and a parity test proving the Mongo visibility query agrees with `note_access` for every scope/ACL/user combination.
- **tests/test_help.py** — Note fixture gained `scope`; new test that public notes are help topics for any account and private ones are not.
- **README.md**, **docs/api-reference.md** — Documented scopes, `PUT /notes/{id}/scope`, new list filters, `my_access`.
- **docs/help/notes/{web-ui/notes,web-ui/authoring-help,reference/faq,reference/glossary}.md** — Help content for scopes and sharing.
