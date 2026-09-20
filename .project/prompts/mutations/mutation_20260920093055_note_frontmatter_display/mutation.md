# Mutation Log

## Modified
- **ui/js/app.js** — Added front-matter helpers (`splitFrontmatter`, `highlightYaml`, `highlightYamlScalar`, `renderFrontmatterHtml`). `renderNoteMarkdown` (used by Notes Browse and Preview) now splits off the front matter and shows it as a collapsible, syntax-highlighted YAML block above the rendered body. `renderHelpMarkdown` now strips front matter so Help never displays it.
- **ui/css/hgai.css** — Added `.note-frontmatter` block styles (bordered collapsible panel, YAML kind badge, wrapped scrollable `pre`) and `.note-fm-comment`; reuses the existing `json-key/-string/-number/-bool/-null` token colors.
