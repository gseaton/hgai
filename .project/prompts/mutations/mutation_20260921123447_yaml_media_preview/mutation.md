# Mutation Log

## Modified
- **ui/js/app.js** — Media preview now recognises YAML files (`isPreviewableMediaType`, `renderMediaPreviewInto`); added `renderYamlMediaPreview` (highlighted, line-numbered `<pre>`, capped at 256 KB / 4,000 lines with a truncation notice); `mediaThumbCellHtml` uses the `bi-filetype-yml` icon for YAML; `openMediaPreview` widens the dialog (`modal-xl`) for YAML.
- **ui/js/yaml-highlight.js** — Added `highlightYamlNumbered` (per-line wrapped spans for a line-number gutter) and `isYamlMedia` (YAML content types, or `.yml`/`.yaml` extension when the stored type is generic); exported to `window` and `module.exports`.
- **ui/css/hgai.css** — Styles for `.media-yaml-preview` (dark scrollable pre, non-selectable CSS line numbers, inline-preview height cap, body layout override).
- **tests/js/test_yaml_highlight.js** — Tests for `highlightYamlNumbered` and `isYamlMedia`.
- **docs/help/notes/web-ui/media.md** — Documented YAML file preview and its size limits.

## Created
- (none new beyond the earlier YAML highlighting change set; `ui/js/yaml-highlight.js` and `tests/js/` were created in the preceding syntax-highlighting task)
