# Mutation Log

## Created
- **docs/help/notes/web-ui/rdf-import.md** (`id: help-rdf-import`) — New, dedicated Help topic: full RDF-to-hypergraph mapping model (id expansion, `rdf:type`/label handling, literal-attribute digit/quote-led value classification, OWL `owl:TransitiveProperty`/`owl:inverseOf`/`owl:SymmetricProperty` axiom-edge synthesis), a worked-example gallery (simple attributes, an attribute mixed with a relationship, a failed digit-led cast, and an OWL symmetric-axiom example feeding `infer: true`), and a Caveats section split into "Not handled" (RDF Collections, JSON-LD named graphs, reification, other OWL/RDFS axioms) and "Surprising-but-intentional behavior" (digit-led strings still becoming numbers, the `-1` fallback, bare dates staying text, attribute keys never expanding, type-only classes getting no node, merge-never-overwrites).

## Modified
- **docs/help/notes/web-ui/export-import.md** — Added a pointer from the existing condensed "Importing RDF" section to the new `help-rdf-import` topic; added the `import-rdf` shell command to the shell command block (it was previously undocumented there).
- **docs/help/notes/integration/shell.md** — Added the `import-rdf` command to the command reference and command table (was entirely undocumented despite existing in `shell/hgai_shell.py`), with a link to the new RDF import topic.
- **docs/help/notes/home.md** — Added a link to the new RDF import topic alongside the existing "Export and import a hypergraph" bullet under "Use the Web UI".
- **docs/help/notes/reference/glossary.md** — Added "RDF import" and "CURIE" glossary entries, both linking to the new topic.
- **README.md** — Added a "RDF Import" table-of-contents entry and a new `## RDF Import` section (between `## Web UI` and `## Inferencing`) with REST/shell entry-point examples, the full mapping-model table, and a "Not handled" summary; added the `import-rdf` command to the `### hgsh Shell Commands` block (previously missing); updated the `## Web UI` section's Hypergraphs bullet to mention RDF import alongside native export/import.
