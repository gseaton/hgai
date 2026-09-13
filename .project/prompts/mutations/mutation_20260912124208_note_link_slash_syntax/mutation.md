# Mutation Log

## Modified
- **ui/js/app.js** — `renderNoteMarkdown()`'s note-link regex now matches `[text](note:<id>)` OR `[text](note/<id>)` (character class `note[:/]` in place of the literal `note:`), so both syntaxes resolve identically to an internal note link or a "broken link" fallback. Updated the section-header comment above the function to document both forms.
