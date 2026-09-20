# Mutation Summary

## Intent
A Note's leading `---`-fenced YAML front matter (e.g. the AI Chat's "Save as Note" writes prompt, vendor/model, timing and token counts) was being run through the Markdown renderer, which turns it into a horizontal rule plus a heading and mangles the YAML. The user wanted it shown properly, as structured YAML, in the Notes Browse and Preview modes only, and never shown in Help.

## Context
- Both Notes modes render through one function, `renderNoteMarkdown`; Edit mode shows the raw textarea and is intentionally unchanged.
- Help renders through `renderHelpMarkdown`. Built-in help files already have front matter removed by the server, but a `system:help` *Note* keeps its own front matter in its text, so Help needed its own suppression.
- No YAML parser exists in the browser (CodeMirror's YAML mode is only a tokenizer), and the app already has JSON token colors on a dark code background.

## What Changed and Why
- `splitFrontmatter` separates a leading front-matter block from the body. It only counts as front matter if every unindented line looks like YAML (`key:`, `- item`, comment), so a note that merely uses `---` horizontal rules is left alone.
- `renderNoteMarkdown` renders the body as before and prepends the front matter as a collapsible "Front matter · YAML" panel. It is built from escaped text after sanitization, like the other placeholder HTML, so note content cannot inject markup.
- `highlightYaml` colors keys, quoted/plain strings, numbers, booleans, null and comments, and treats `key: |` / `key: >` block scalars as a single string so prompts containing "word: text" are not mis-highlighted.
- `renderHelpMarkdown` uses only the body from `splitFrontmatter`, so Help never shows front matter regardless of source.

## Key Decisions
- **Syntax-highlighted YAML rather than a parsed key/value table**: it shows the true structure exactly as stored (including multi-line block scalars) without adding a YAML parser dependency.
- **Front matter is validated before being stripped**, avoiding false positives on ordinary horizontal-rule notes.
- **Client-side stripping for Help** rather than changing the server's note-topic text, keeping the agent's help tools and API unchanged.
- **Verification**: node checks of the split/highlight logic (chat-style, CRLF, lists, comments, empty, unclosed, horizontal-rule-only cases); in the browser a chat-style Note showed the highlighted block in Browse and Preview with the body and a later horizontal rule rendered normally, Edit stayed raw, and a `system:help` Note with front matter showed only its body in Help while file topics were unaffected. No console errors; test notes deleted. The Python suite is unchanged (241 passed, 2 pre-existing mesh-ping failures).
