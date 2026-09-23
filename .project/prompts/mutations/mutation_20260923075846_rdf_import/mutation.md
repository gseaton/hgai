# Mutation Log

## Created
- **hgai/core/rdf_import.py** — The RDF -> hypergraph mapping engine. Parses Turtle/RDF-XML/JSON-LD/N3 via `rdflib` and produces an in-memory document in the same shape as a native `hgai_export` file (`rdf_to_export_document`), so it flows through the existing `hgai.core.transfer.import_document` pipeline unchanged. Every subject and every resource-valued (IRI/blank-node) object becomes a hypernode (id = a sanitized `prefix:local` CURIE, never the raw IRI); `rdf:type` sets the node's `type` + `attributes.rdf_type`; a label is picked from `rdfs:label`/`skos:prefLabel`/`foaf:name`/`dc:title`/`dcterms:title`; every other literal-valued triple becomes an attribute (BSON-safe types converted, else the lexical string); every resource-valued triple becomes a `hub` hyperedge (subject seq 0, object seq 1). Also exports `resolve_format()` (alias/extension -> rdflib format name) and `SUPPORTED_FORMATS`.
- **tests/test_rdf_import.py** — 58 tests covering format resolution, the full mapping (nodes, edges, attributes, rdf:type, labels, literal type conversion, blank nodes, id sanitizing/collision handling, determinism, cross-format equivalence), and error handling.

## Modified
- **requirements.txt**, **pyproject.toml** — Added `rdflib` (7.6.0 pinned / `>=7.0.0`) as a dependency.
- **hgai/api/transfer_http.py** — Added `read_rdf_body()`: reads the raw request body, resolves the RDF format, and converts it via `rdf_import.rdf_to_export_document`, raising the same 400/413 HTTP errors as the existing `read_export_body()`.
- **hgai/api/routers/hypergraphs.py** — Added `POST /graphs/import/rdf` (required `graph_id` and `format` query params, optional `label`, same `mode` as the native import route), reusing `run_import()` and the same permission check as `POST /graphs/import`.
- **hgai/api/routers/spaces.py** — Added `POST /spaces/{space_id}/graphs/import/rdf`, mirroring `POST /spaces/{space_id}/graphs/import` (space-membership-gated).
- **shell/hgai_shell.py** — Added `import-rdf` shell command (`cmd_import_rdf`) and `HgaiClient.import_rdf_file()`, mirroring the existing `import`/`import_graph_file`; format is inferred from the file extension when `--format` is omitted.
- **ui/js/api.js** — Added `HGAI_API.importRdfFile()`.
- **ui/js/app.js** — Extended the Graph Import modal's logic: `graphImportDetectFormat()` routes a chosen file to the native-export or RDF path by extension; RDF selection shows an explanatory note, makes the Hypergraph ID field required (client-side guard before calling the API), and calls `importRdfFile` instead of `importGraphFile`; a new help-link handler closes the modal and opens the "Exporting and importing hypergraphs" Help topic.
- **ui/index.html** — Extended the Import modal: file input now also accepts `.ttl/.rdf/.xml/.jsonld/.n3`, updated description text, added an RDF-specific info note (`#graph-import-rdf-note`, hidden by default) and made the Hypergraph ID label's required/optional state dynamic (`#graph-import-id-label`).
- **docs/help/notes/web-ui/export-import.md** — Added an "Importing RDF" section (mapping table, UI/REST usage, documented limitations); updated the topic's intro/description/tags.
- **docs/api-reference.md** — Added a `POST /graphs/import/rdf` reference section (query params, mapping table, limitations) after the existing import endpoints.
- **README.md** — Added the `POST /graphs/import/rdf` line to the quick-reference endpoint list.
