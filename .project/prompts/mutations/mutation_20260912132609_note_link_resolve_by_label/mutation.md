# Mutation Log

## Modified
- **ui/js/app.js** — `renderNoteMarkdown()`'s note-link resolution now tries a captured reference against note `id` first, then falls back to note `label` if no id matches. Replaced the single `id -> label` `Map` with two indexes (`noteById`, `idsByLabel`) built from the same `listNotes()` call, and a new `resolveNoteRef(ref)` helper that returns the resolved `{id, label}`, an `{ambiguous: true}` marker if more than one note shares that label, or `null` if nothing matches. The broken-link fallback now shows a distinct message for the ambiguous case (multiple notes share the referenced label) versus the not-found case. Renamed the internal `id` field on captured note-link records to `ref` throughout the function, since it's no longer necessarily an id.
- **ui/index.html** — Updated the Content field's inline syntax hint from `[text](note:<id>)` to `[text](note:<id-or-label>)`.
