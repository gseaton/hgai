# Mutation Log

## Created
- **ui/js/yaml-highlight.js** — Dependency-free YAML tokenizer/highlighter (`highlightYaml`, `highlightYamlBlocks`), usable in the browser and in Node. Colours keys (plain, quoted, `rel:member`-style), scalars by type (string, number, boolean, null, ISO date), full-line and inline comments (never inside quotes), block scalars, single- and multi-line flow collections, anchors/aliases/tags, document markers, list dashes, and SHQL `?variables`.
- **tests/js/test_yaml_highlight.js** — Node test suite (11 tests): token classification, edge cases, HTML escaping, and a round-trip check that highlighting never changes text across all 185 yaml/shql blocks in the repository's Markdown.
- **tests/test_yaml_highlight_js.py** — Runs the Node suite under pytest (skipped if Node is not installed).

## Modified
- **ui/js/app.js** — Removed the older line-based front-matter highlighter; `renderNoteMarkdown` (Notes Browse and Preview) and `renderHelpMarkdown` (Help topics) now call `highlightYamlBlocks()` after rendering; the front-matter panel uses the shared `highlightYaml`.
- **ui/index.html** — Loads `yaml-highlight.js` before `app.js`.
- **ui/css/hgai.css** — Added `.yaml-*` token styles (same palette as the JSON viewer on the dark code background); removed the old `.note-fm-comment` rule.
- **docs/help/notes/web-ui/notes.md**, **docs/help/notes/web-ui/authoring-help.md** — Documented that ```yaml / yml / shql code blocks are highlighted.
