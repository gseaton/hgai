# Mutation Summary

## Intent
Follow-up to an ask about SHQL scaling limits: make the hard-coded candidate caps configurable and surface a `truncated` flag so overflow is no longer silent.

## Context
Caps were literals (`limit=2000` in the SHQL engine node/edge pattern searches, `limit=5000` in inference). Settings live in `hgai/config.py` (pydantic, `HGAI_` env prefix).

## What Changed and Why
Three settings replace the literals. Each capped fetch requests cap+1 documents; an extra document proves overflow without a count query, is discarded, and records a message in a ContextVar sink. `execute_shql` installs the sink around pattern evaluation and reports `meta.truncated` (bool) and `meta.truncated_by` (which caps hit). `project_inference` does the same in its return dict. Docs and env example updated; a test covers the exact boundary (cap vs cap+1).

## Key Decisions
- ContextVar sink rather than threading a parameter through the recursive evaluators (optional/union) and inference helpers.
- Settings only, no per-query override (not requested; avoids letting queries bypass an operator ceiling).
- Cached results carry the flag in `meta`, so cache hits stay accurate.
- Not addressed: per-binding search N+1 and in-memory aggregation.
