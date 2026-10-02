# Mutation Summary

## Intent
Assess how HypergraphAI would support BFO and CCO based ontologies, as a report for the architecture docs.

## Context
Grounded in the RDF importer, the inference engine, SHQL, the SPARQL plan documents and the multi-tenancy plan. To avoid asserting things from reading alone, a BFO-shaped Turtle fragment (real BFO ids, a restriction, an instance) was imported through the real importer and queried in a real engine, using scratch scripts outside the project.

## What Changed and Why
One new document. Key verified findings: import maps classes, properties, annotations, inverse, transitive and symmetric axioms cleanly with IRI ids; rdfs:subClassOf is stored but not transitive until an owl:transitive axiom is added, after which infer: true returns the full ancestor chain; restrictions survive as blank-node structure without semantics; language tags are dropped; subPropertyOf, disjointness and imports are stored or ignored.

## Key Decisions
- Claims are labelled as verified (fragment) versus expected (full BFO and CCO releases, which were not imported).
- CCO identifiers are not quoted since they are opaque and release-specific; BFO ids are quoted with a note to confirm.
- The report proposes work items (R1 to R11) rather than implementing anything.
