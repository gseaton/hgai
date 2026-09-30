# Mutation Summary

## Intent
Produce a Lattice Partner Program partner summary, with a short Integration Summary matching the application form field, covering how HypergraphAI would partner with Anduril and other Lattice partners.

## Context
The program page text was supplied in docs/marketing/anduril-lattice-partner-program-overview.txt (SDK with gRPC/REST, open entity and tasking models, sandboxes, partners such as Scale, Striveworks, Oracle, Spire, Saronic, Forterra). Platform claims come from README.md. This supersedes the earlier 20260930080606 summary, which lacked program details; that file was left in place.

## What Changed and Why
One new file. Partner collaboration is framed by partner type, drawn from the program text, and explicitly labeled as proposed with no implied relationship with any named company.

## Key Decisions
- Filename had a blank timestamp in the prompt; the timestamp convention from the prior request was used.
- Connector kept as proposed, not built; pre-revenue and no SOC 2 stated plainly.
- No non-ASCII characters used.
