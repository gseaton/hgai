# Mutation Log

## Modified
- **hgai/core/inference.py** — `project_inference()`'s lazy imports gained `get_hyperedge`, `get_hypernode`, `create_hypernode` from `hgai.core.engine` and `HypernodeCreate` from `hgai.models.hypernode`. Added an `_ensure_member_exists(node_id)` helper (with an `ensured_member_ids` cache set) that, for a materialized edge's member id, checks whether it already exists as a hypernode or hyperedge in the target graph and, if not, copies a matching hypernode from whichever source graph has it (id/label/type/description/valid_from/valid_to) into the target graph. This is called for every member of a candidate immediately before `create_hyperedge()` writes the materialized edge (only on the actual-write path, not `dry_run`).
