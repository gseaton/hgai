# Mutation Summary

## Intent
Make the initial sample data for a new install ordinary hypergraph export YAML files in a `scripts/seeds` folder (present in the Docker image), instead of Python literals in the seed script, include both the `hello-world` and `eden` hypergraphs, and update all docs/instructions accordingly.

## Context
- The previous `scripts/seed_data.py` (the user called it `seed.py`) hard-coded a small Three Stooges dataset and printed HQL-era example queries. Its default server was port 8000 although local dev runs on 8357.
- Export/import had just been added, so a seed can now be the same export file format and be loaded through the import endpoint (which creates the hypergraph from the file).
- The user wrote both `scripts/seed` and `scripts/seeds`; the plural `scripts/seeds` was used everywhere. "Current hello-world/eden" was taken to mean the instances in the running server, exported as-is.
- The Dockerfile already copied all of `scripts/`, so the seeds reach the image without further change.

## What Changed and Why
- **Seeds** — exported the live `hello-world` and `eden`, then stripped media references (39, pointing at media files that exist only on this instance) and the per-item audit history, and prefixed a short YAML comment header. They remain valid exports (verified by re-parsing and by importing into an empty instance).
- **Loader** — `seed_data.py` now only discovers, selects and imports files: `python scripts/seed_data.py [ids-or-paths] [--list]`. It merges idempotently, reports counts, exits non-zero on failure, and defaults to `http://localhost:$HGAI_PORT` (8357 locally, 8000 in Docker) so the documented commands work.
- **Verification on a fresh install** — a second server on an empty database was seeded; both graphs came out identical to the files, re-running skipped everything, and queries ran. Tests check every seed file for validity, self-containment and clean import, and that the Dockerfile copies `scripts/`. Docker itself was not available to build the image.
- **Docs** — README, Help topics, tutorial, design/deck notes now describe the seed files and options.
- **Example queries** — while pointing docs at the real seed data, the SHQL examples turned out not to match it and several did not parse: unquoted `?var` inside flow-style YAML (`{ bind: ?x }`, `[?a, ?b]`) is invalid, and a `type:` inside an edge's `members:` pattern is silently ignored by the engine. Every example over the seeds was rewritten in block style using the documented join idiom (`node_id: ?id` then a `node:` pattern on that id), run against the seeded data, and added Eden examples; a parse/validate test now covers all documented SHQL.

## Key Decisions
- **Stable file names** (`hgai-hypergraph-<id>.export.yml`, no timestamp) so docs and commands can reference them.
- **Default loads every seed**, `merge` mode for idempotence; `--list` and per-seed selection for control.
- **Seeds are the data as it exists**, including outliers (an `a`/"is-a" relation node, an Event node whose video was removed, and an edge referencing a `person:tommy-moore` node that does not exist). They were left as-is and the dangling reference is allow-listed in the test.
- **Script name kept** (`seed_data.py`) so existing commands remain valid.
- 327 tests pass, 2 pre-existing unrelated mesh-ping failures. The test instance/database and scratch files were removed.
