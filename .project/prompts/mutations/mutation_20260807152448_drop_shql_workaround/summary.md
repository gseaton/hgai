# Mutation Summary

## Intent
Simplify the `demo-alpha` deck's SHQL examples now that the underlying engine bug they were working around has been fixed upstream, so the deck teaches the current, idiomatic way to write these queries instead of a now-unnecessary defensive pattern.

## Context
While authoring the original deck (see [[docs/decks/demo-alpha]] mutation from 2026-07-31/08-02), live testing against `hgai_module_shql/engine.py` found that an edge's `members:` pattern only treated a sub-pattern as an "anchor" (matched deterministically) if it carried an explicit `id:` key — an already-bound `?variable` from an earlier `node:` pattern didn't count, so two same-shaped member patterns on a multi-member hub edge (e.g. a person hub-linked to several skills) could silently bind the wrong node. The deck worked around this by repeating the bound variable as both `bind` and `id` (`{ bind: "?person", id: "?person" }`), documented as a "practical tip."

In a separate session on 2026-08-07 (commit `3e926c8`), the engine itself was fixed: `_resolve_member_pat` now treats an already-bound `bind` variable as an anchor directly, and `seq` (positional) matching was added alongside `id`. The user was made aware of this via a prior "familiarize the changes" ask in this conversation, and asked to update the deck accordingly.

## What Changed and Why
Before editing anything, the fix was independently re-verified live: a disposable throwaway server (`hgai_demo_validate2`, port 8399, dropped afterward) was seeded with the deck's own `acme-eng-import.yaml` dataset, and simplified versions of q09, q10, and q13 (dropping the `id: "?var"` self-reference) were run against it. All three produced results identical to the original workaround-era versions (14, 7, and 6 rows respectively), confirming the simplification is safe before it was written into the deck.

The three affected query files (`q09-skills-lookup.shql`, `q10-staffing-by-project.shql`, `q13-union-python-or-lead.shql`) had their redundant `id: "?var"` self-references removed, leaving plain `{ bind: "?var" }` member patterns. The deck's corresponding YAML code blocks were updated to match, and the "Practical tip — anchoring an already-bound variable" callout was rewritten from an instruction ("repeat the variable as both bind and id to force anchor classification") to an explanation of the engine's current, automatic behavior — since the old phrasing was actionable advice for a bug that no longer exists, and leaving it in would teach readers an unnecessary and now-slightly-misleading pattern.

## Key Decisions
- **Verified live before editing, not just trusted the commit diff.** The commit message and diff were convincing on their own, but the deck exists specifically so unattended engineers can run it without surprises — re-running the actual queries against the actual dataset before simplifying them was cheap insurance against a partial fix or an edge case the diff didn't cover.
- **Rewrote the callout rather than deleting it.** The underlying concept (member patterns can reference variables bound by earlier patterns, and the engine uses that to disambiguate multi-member hyperedges) is still genuinely useful for a reader unfamiliar with SHQL — only the "how to force it" mechanic was obsolete, not the concept itself.
