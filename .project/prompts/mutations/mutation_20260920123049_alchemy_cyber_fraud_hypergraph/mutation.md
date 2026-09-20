# Mutation Log

## Created (project files)
- **scripts/generators/crowbar_cyber_fraud.py** — The generator: reads the two `crowbar` datasets (six CSV files, ~2M transactions) and bulk-inserts the hypergraph, ontology, provenance and graph definition into MongoDB using the engine's document shape and hyperkey function. Options `--source`, `--db`, `--sample`, `--dry-run`, `--report`.
- **scripts/generators/verify_crowbar_cyber_fraud.py** — Read-only post-load verification (counts, provenance coverage, referential integrity, unlinked nodes, 2×1,000 random source-row comparisons, ontology/inference API checks, SHQL spot checks).
- **tests/test_crowbar_generator.py** — 17 tests keeping the authored ontology tables (classes, relation types, inverses, axioms, hierarchies, concept schemes, geography) internally consistent, plus the numeric/text helpers.

## Created (data, in the configured MongoDB database `hgai`)
- **Hypergraph `alchemy-cyber-fraud-generated-20260920190053`** — 3,631,632 hypernodes and 1,872,417 hyperedges (13,501,743 member slots); label = id; `attributes.name` = "Fraud Detection - Alchemy (2026-09-20)"; generated description; `attributes.provenance` with source hashes, counts, reconciliation, data-quality notes and verification summary.
- **Note `hgai-note-generation-20260920190053`** — Audit record (front matter + ~30k characters of Markdown), owner `admin`, scope `private`, tags include the graph id and `//Audit/Hypergraph Generation`.

## Deleted (data)
- A first, failed load attempt of the same generator (partial graph `alchemy-cyber-fraud-generated-20260920183232`: 3,631,632 nodes / 1,872,417 edges, no finalization) — removed before the successful run.
- Scratch database `hgai_pilot` and its temporary server (port 8391) used for the 20,000-row pilot.

## Not modified
- Source files in `/home/gseaton/Downloads/crowbar` (read-only; SHA-256 recorded).
- No existing hypergraph, node, edge, or application code was changed.
