## Prompt

Please assess how to import and export hypergraphs and if the current code base has this capability (import / export hypernodes and hyperedges).                                                                                                  

## Assessment

● I'll research the codebase's import/export capabilities before answering — this is a read-only investigation, so I'll dispatch it to a fork to keep the raw exploration out of our context.
 
● Agent "Assess hypergraph import/export capability" finished · 58s

● Import/Export Assessment: HypergraphAI Codebase

**Short answer**: Yes, it exists and works — but only reaches you through the REST API and CLI shell, not the web UI or MCP. Granularity is whole-hypergraph (shell + all its hypernodes + all its hyperedges in one shot), not per-node/per-edge.

## How it works

- **Core logic — hgai/core/engine.py**:
  - `export_hypergraph(graph_id, space_id=None)` (line 360)
    - pulls the graph + up to 10,000 hypernodes + 10,000 hyperedges, returns {"hgai_export": "1.0", "graph": {...}, "nodes": [...], "edges": [...]}                                
  - `import_hypergraph_data(graph_id, data, created_by, space_id=None)` (line 377): 
    - strips server-generated fields (hypergraph_id, timestamps, hyperkey), validates each row, calls create_hypernode/create_hyperedge per item. Returns {"nodes": N, "edges": N, "errors": N}.
- **REST API** — hgai/api/routers/hypergraphs.py: POST /graphs/{id}/export (line 103) and POST /graphs/{id}/import (line 114). Only on the global-graph router — no space-scoped equivalent exists.
- **CLI shell** — shell/hgai_shell.py: export -o <file> (line 897) and import -f <file> (line 873), fully working, documented in README.md:1456-1457.
- **Format proof**: the root-level hg-alpha.20260322.hgai.export.yaml and freakshow-alpha.hg.export.yaml are real artifacts from this exact export — hgai_export: '1.0' / graph: / nodes: / edges: as top-level YAML keys.
  (new-o-output-results-file.yaml is unrelated — that's an HQL query-result dump, not an export.)
- **HQL/SHQL**: neither query language has any export/import verb — pure query, irrelevant here.

  ## Gaps
  - **UI**: ui/js/api.js already defines exportGraph/importGraph client methods, but nothing in app.js or index.html calls them — no button, no modal. It's dead client code; export/import is invisible in the browser.
  - **MCP**: the MCP server exposes 25 tools for full CRUD (graphs/nodes/edges/spaces/mesh) but none named export/import — not reachable by AI agents through MCP.
  - **No test coverage** — zero tests in tests/ exercise either function.
  - **Import is additive-only**: no upsert/overwrite, no dry-run, no schema-version check against hgai_export: "1.0", and per-row failures are silently counted rather than reported with detail. Re-importing the same file will error or duplicate on
    ID collision, not update in place.

---

If you want, I can wire up an Import/Export button pair in the Visualize/Hypergraphs screen (the client methods already exist) — that's the most visible gap. Let me know if that's worth doing next.

