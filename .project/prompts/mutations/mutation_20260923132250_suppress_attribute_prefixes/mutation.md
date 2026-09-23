# Mutation Log

## Created
- **tests/test_transfer_http.py** — 15 pure, storage-free unit tests for the new `_local_attribute_name`, `_strip_attribute_key_prefixes`, and `strip_attribute_prefixes_in_doc` functions: CURIE stripping, full-IRI stripping (slash and fragment forms), unchanged-if-no-separator, unchanged-if-key-ends-in-its-only-separator, empty/None passthrough, collision avoidance (two prefixed keys sharing a local name; a prefixed key colliding with an already-unprefixed one), and a doc-level test covering both node and edge `attributes`.

## Modified
- **hgai/api/transfer_http.py** — Added `_local_attribute_name()` (extracts a key's local name after its last `#`/`/`, or `:` if neither is present), `_strip_attribute_key_prefixes()` (rewrites a single attributes dict's keys, leaving a key untouched if stripping it would collide with another key's resulting name), and `strip_attribute_prefixes_in_doc()` (applies the above to every node's and edge's `attributes` in an in-memory export document). Added a `strip_attribute_prefixes: bool = False` parameter to `run_import()`, applied before handing the document to `transfer.import_document`.
- **hgai/api/routers/hypergraphs.py** — Added `strip_attribute_prefixes` query parameter to `POST /graphs/import` and `POST /graphs/import/rdf`, passed through to `run_import`.
- **hgai/api/routers/spaces.py** — Same addition to the space-scoped `POST /spaces/{space_id}/graphs/import` and `POST /spaces/{space_id}/graphs/import/rdf`.
- **ui/index.html** — Added a "Suppress Attribute Prefixes" checkbox (`#graph-import-strip-prefixes`) to the Import Hypergraph modal, with inline help text and examples, placed below the create/merge mode radios.
- **ui/js/api.js** — `importGraphFile()` and `importRdfFile()` gained a `stripAttributePrefixes` option, sent as the `strip_attribute_prefixes` query parameter (omitted when false, to keep the request URL clean).
- **ui/js/app.js** — The Import modal's reset logic now unchecks the new checkbox; the submit handler reads its checked state and passes it to both `importGraphFile`/`importRdfFile` calls.
- **docs/api-reference.md** — Documented `strip_attribute_prefixes` on both `POST /graphs/import` and `POST /graphs/import/rdf`.
- **docs/help/notes/web-ui/export-import.md** — Documented the new checkbox in the Web UI import steps, and the `strip_attribute_prefixes=true` REST parameter.
- **docs/help/notes/web-ui/rdf-import.md** — Extended the existing "Attribute keys never expand" caveat with a pointer to this new option, including the collision-avoidance behavior.
- **README.md** — Added a paragraph to the `## RDF Import` section documenting the option and its collision-avoidance behavior.
