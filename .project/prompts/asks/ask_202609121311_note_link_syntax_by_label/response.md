# Response Summary

## Question / Intent
The user wanted the exact inline markdown syntax to write inside a note's content for a link with display text `meh` pointing to the note labeled `first-note`.

## Answer / Recommendation
```markdown
[meh](note:6d14c3044a7047d9bb6a9d563a997351)
```
or equivalently (both syntaxes are supported as of this session's most recent mutation, `mutation_20260912124208_note_link_slash_syntax`):
```markdown
[meh](note/6d14c3044a7047d9bb6a9d563a997351)
```

`6d14c3044a7047d9bb6a9d563a997351` is the actual `id` of the real note in this instance whose `label` is `first-note` (looked up live via `GET /api/v1/notes` — confirmed to exist, alongside one other note, `hgai-dev-todo-tasks`).

## Key Points
- **The reference resolves strictly by note `id`, not by `label`.** `renderNoteMarkdown()` (`ui/js/app.js`) builds its resolution table as `new Map(notes.map(n => [n.id, n.label]))` and looks up the captured `note:`/`note/` path segment directly against that map's keys. Writing `[meh](note:first-note)` — using the label instead of the id — will **not** resolve; it renders as a broken-link `<span class="note-link-broken">`, since `"first-note"` (the label) is never a key in that id-keyed map unless a note's `id` and `label` happen to be identical strings, which isn't the case here.
- There's currently no UI affordance to copy a note's own `note:<id>` reference to the clipboard (a feature Quill, the project this was modeled on, does have) — the id has to be found via the notes list/API, same as was done here.

## Context
Builds on this session's two most recent mutations to the Notes feature: `mutation_20260912103825_rich_notes_sharing` (which introduced the `note:<id>` link syntax and its id-keyed resolution) and `mutation_20260912124208_note_link_slash_syntax` (which added the equivalent `note/<id>` form). Both forms behave identically once past the separator character — the distinction that actually matters for this question is id-vs-label, not colon-vs-slash.
