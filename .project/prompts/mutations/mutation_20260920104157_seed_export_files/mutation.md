# Mutation Log

## Created
- **scripts/seeds/hgai-hypergraph-hello-world.export.yml** — Export of the current `hello-world` hypergraph (30 nodes, 16 edges), media references and audit history stripped for portability.
- **scripts/seeds/hgai-hypergraph-eden.export.yml** — Export of the current `eden` hypergraph (9 nodes, 8 edges).
- **scripts/seeds/README.md** — What the seed files are, how to load them, how to add/update one.
- **tests/test_seeds.py** — Each seed is a valid, self-contained, portable export that imports with no errors; loader discovery/selection/error handling; the Dockerfile copies `scripts/`.
- **tests/test_docs_shql.py** — Every SHQL example in the README, API reference and Help topics must parse and validate (guards against flow-style `?var` YAML).

## Modified
- **scripts/seed_data.py** — Rewritten: no hard-coded data. Discovers `scripts/seeds/*.export.yml`, imports them via `POST /graphs/import?mode=merge` (idempotent); accepts graph ids or file paths, `--list`, `--server/--user/--password`; default server from `HGAI_PORT` (was a fixed 8000); clean error messages and exit codes.
- **Dockerfile** — Comment noting `scripts/` (which contains `scripts/seeds/`) is copied into the image.
- **README.md** — Seeding instructions (new "Seed the example hypergraphs" section, seed table and options), quick-start comments, architecture tree; SHQL examples gallery (1–7, 13–16 rewritten against the seeds; 4b and 17–19 added incl. Eden), pattern reference, MCP payload examples and inverse-of text now use the seed vocabulary and valid block-style YAML.
- **docs/hello-world.md** — Points to the seed files and explains the tutorial data differs from the seed.
- **docs/design/epics-to-build-production-hgai/build-plan.md**, **docs/decks/demo-alpha/deck-demo-alpha.md**, **notes/decks/hgai-tech-developer-20260808.md** — Seed references updated.
- **docs/help/notes/getting-started/quick-start.md**, **admin/docker.md**, **admin/running-locally.md**, **reference/faq.md**, **home.md**, **concepts/{hypernodes,hyperedges,point-in-time}.md**, **shql/{shql-examples,shql-patterns,shql-advanced,shql-filters}.md**, **web-ui/{parameterized-queries,export-import}.md**, **admin/meshes.md**, **integration/{mcp-server,mcp-tools}.md**, **inference/inferencing.md**, **reference/glossary.md** — Seeding instructions and example queries updated to the seeds; SHQL examples verified and converted to valid block-style YAML.
