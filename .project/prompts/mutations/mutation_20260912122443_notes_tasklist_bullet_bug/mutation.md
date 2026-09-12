# Mutation Log

## Modified
- **ui/css/hgai.css** — Added two rules under `.note-preview-pane`: `li:has(> input[type="checkbox"]) { list-style-type: none; }` (removes the browser's default bullet marker specifically on list items containing a checkbox — and only those) and `li > input[type="checkbox"] { margin: 0 0.4em 0 -1.4em; vertical-align: middle; }` (pulls the checkbox into the space the removed bullet vacated, aligning it the way GitHub's own task-list styling does). Applies to both Browse mode's `#note-browse-content` and Preview mode's `#note-preview`, since both share the `.note-preview-pane` class.
