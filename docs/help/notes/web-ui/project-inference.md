---
id: help-project-inference
label: Project Inference
name: project-inference
description: Materialize inferred facts (axiom expansion and transitive closure) into a hypergraph as ordinary hyperedges.
tags: ["//Using the Web UI", inference, materialize, projection]
status: active
---

# Project Inference

Normally [inferencing](help:help-inferencing) is computed live and nothing derived is stored. **Project Inference** lets you *materialize* those derived facts into a hypergraph as ordinary, persisted hyperedges — a **snapshot**, previewed before anything is written. Re-running later only adds new facts; it never removes or updates earlier ones.

## Steps

1. **Source hypergraph(s)** — Ctrl/Cmd-click to select several.
2. **What to project** —
   - *Expand axioms* (inverse-of / symmetric / superproperty), and/or
   - *Transitive closure* (requires an `owl:transitive` axiom on the relation you name).
   Optionally restrict to one **relation** and a **point-in-time**.
3. **Target hypergraph** — an existing graph or a new one (id and label).
4. **Project only new hyperedges?**
   - *On* — members that don't exist in the target are left as references to the source; the target is a thin inference-only layer meant to be queried *alongside* the source (a multi-graph query or a logical graph).
   - *Off* (default) — missing members are copied in, producing a self-contained snapshot.
5. **Preview**, review the list and summary, then **Confirm & Project**.

The REST endpoint is `POST /api/v1/graphs/{target}/infer/project` ([REST API](help:help-rest-api)).
