# Mutation Summary

## Intent
Persist the Harry S. Truman SKTL YAML example (generated as a text response in the prior ask session) as a file in the project so it can be reused, imported, or referenced later.

## Context
The SKTL example was produced in response to an ask prompt requesting a comprehensive encyclopedic representation of Harry S. Truman's Wikipedia article in the hgai v1.0 YAML format. The format uses a flat `nodes:` list with `type: Rel` as the hyperedge discriminator, standard semantic predicates (schema:, skos:, rel:), and typed prefixes (person:, org:, event:, place:, doc:, office:). The file was placed in `scratch/` as a working/reference artifact rather than a production data directory.

## What Changed and Why
Created `scratch/hdtl.yaml` containing the full SKTL representation. The `scratch/` directory was created as it did not yet exist. The filename `hdtl.yaml` was specified by the user.

## Key Decisions
- Placed in `scratch/` per user instruction; this directory is appropriate for example/reference files not yet imported into any hypergraph.
