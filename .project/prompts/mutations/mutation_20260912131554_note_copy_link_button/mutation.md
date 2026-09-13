# Mutation Log

## Modified
- **ui/index.html** — Added a "Copy Link" button (`#btn-note-copy-link`) to the note editor modal's header, next to the existing "Share" button, hidden (`d-none`) by default.
- **ui/js/app.js** — `openNoteModal()` now toggles `#btn-note-copy-link`'s visibility based on whether the note being opened is an existing (saved) note or a brand-new one. Added a click handler that builds `[<current label>](note:<id>)` from the note's real id and whatever is currently in the Label field (not the last-saved label), and copies it to the clipboard via `navigator.clipboard.writeText()` with a confirmation toast.
