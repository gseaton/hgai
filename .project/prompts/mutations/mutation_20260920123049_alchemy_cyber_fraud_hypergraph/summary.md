# Mutation Summary

## Intent
Turn the `crowbar` folder (two synthetic banking-fraud datasets) into a new hypergraph in the cybersecurity / fraud-detection domain: entities as hypernodes, relationships as hyperedges, a domain ontology with OWL/SKOS semantics, provenance on every element, and a comprehensive audit Note.

## Context
- The folder holds ~300 MB: a *fraud-detection* dataset (50,000 account profiles, 1M transactions, fraud-pattern catalogue, 7,411 shared-attribute links with fraud-ring ids, 26,280 hourly statistics) and a *synthetic-banking-txns* dataset (1M transactions with customers, cards, devices, IPs, merchants, cities). They share no identifiers.
- HypergraphAI's edge flavors are only `hub` and `symmetric` (each hub–spoke pair is an independent fact) and the inference engine's control vocabulary is `owl:inverse-of/symmetric/transitive` and `skos:broaderTransitive/narrowerTransitive` between relation-type nodes. A hypergraph has no `name` field and "properties" are the `attributes` document.
- The full volume (about 5.5M documents) makes REST-per-document loading impractical (hours), so the data is bulk-inserted into MongoDB directly, with the engine's own document shape and hyperkey function.

## What Changed and Why
- **Generator + tests + verifier** are checked into `scripts/generators/` so the run is reproducible and auditable (its SHA-256 is recorded in the hypergraph and Note, and matched the file at verification time).
- **Model**: each row-level entity (account, transaction, hourly bucket, customer, card, device, IP, merchant, city, ring) is a hypernode carrying only data literals; every reference to another entity is a hyperedge. Because a transaction relates to many things, relationships are hub hyperedges grouping all spokes of a relation for a hub (chunked at 250), which keeps 2M transactions to 1.87M hyperedges without losing any (hub, spoke) fact. Two kinds of information had no direct row equivalent and are labelled as derived in provenance (customer→card/device, shared-identifier links, ring counts).
- **Ontology** (authored by the agent, flagged `ontology-authored`): 27 classes, 55 relation types with domain/range, inverse pairs, symmetric and transitive relations, a two-level `skos:broaderTransitive` relation hierarchy for account/customer links, `skos:narrowerTransitive` categorisation hierarchy, SKOS concept schemes (merchant category, fraud typology, channel, account type) with polyhierarchies and cross-dataset `exactMatch`/`closeMatch`, and a transitive geography (world→continent→country→city).
- **Provenance** is in `attributes.provenance` on the graph, every node and every edge (source file, row or row range, method, mapping, run id, generator).
- **Audit Note** records the request, interpretation/deviations, source hashes, mappings, counts, reconciliation of source aggregates with recomputed values (all matched exactly), data-quality findings, verification results, limitations, and reproduction/removal commands.

## Key Decisions and Findings
- **Full fidelity over sampling**: all 2,000,000 transactions and every entity were loaded; verification found 0 dangling members, 0 nodes outside a hyperedge, and 0 mismatches in 2×1,000 random source rows.
- **Failed first attempt, fixed**: the first full load crashed on its last batch because two customers sharing more than one identifier produced identical hyperedges (same relation and members), rejected by the hyperkey uniqueness. Such edges are now merged into one listing all shared identifiers; the partial graph was deleted and the load rerun.
- **Source observations recorded** (not "fixed"): merchants seen in several cities, 177 cards / 77 devices / 176 IPs shared by several customers, 3,000 links without a ring, 97 accounts without transactions, zone-less timestamps in one dataset, and latitude/longitude values that do not match country/city.
- **Scale limitations documented in the Note**: SHQL `infer: true` only considers a bounded (2,000-edge) candidate set per pattern and is slow on a graph this size — the per-edge `/infer/expand` and `/infer/transitive` endpoints are the usable inference paths; whole-graph export and Visualize are impractical.
- **Deviations from the wording**: the trailing blanks in id/label/name were filled with a UTC timestamp / date; `name` lives in `attributes.name`; the Note is `private` (owner `admin`).
- **Verification**: 17 new tests; full suite 344 passed, 2 pre-existing unrelated mesh-ping failures.
