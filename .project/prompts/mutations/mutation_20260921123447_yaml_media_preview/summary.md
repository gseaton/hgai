# Mutation Summary

## Intent
Let users preview YAML files stored as Media (for example a `*.export.yml` hypergraph export or a SHQL query file) directly in the UI, with the same syntax highlighting now used for Notes and Help.

## Context
The Media preview dialog only supported image/audio/video. The dependency-free YAML tokenizer (`ui/js/yaml-highlight.js`) had just been added for Notes/Help, so it was reused. Browsers frequently upload `.yml` files as `application/octet-stream` or `text/plain`, so type alone is not a reliable signal.

## What Changed and Why
YAML detection (`isYamlMedia`) accepts the YAML MIME types, or a `.yml`/`.yaml` extension when the stored type is generic. The preview downloads the blob, highlights it with a line-number gutter drawn by CSS (`data-ln` + `::before`, non-selectable so copy/paste yields clean YAML), and shows it in a wider dialog. The thumbnail cell gets a YAML file icon. Help docs (Media topic) describe the feature.

## Key Decisions
- Size cap: the first attempt (1 MB) produced ~344k DOM spans for a 2.9 MB file and froze the renderer, because every token is a span. The preview is now limited to 256 KB and 4,000 lines with a visible notice pointing to Download; a 2.8 MB file renders in ~120 ms.
- Line numbers are CSS-generated rather than text so they are not selected/copied.
- Verified live in Chrome (small `.yml` with octet-stream, `application/x-yaml`, `text/yaml` oversized file); test media were deleted afterwards. Node suite (13 tests) and pytest (345 passed; 2 pre-existing mesh ping failures unrelated) pass.
