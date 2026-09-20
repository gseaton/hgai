# Seed hypergraphs

Each `hgai-hypergraph-<id>.export.yml` file here is an ordinary HypergraphAI **hypergraph export file**
(the same format as **Hypergraphs → Export** in the Web UI and `GET /api/v1/graphs/<id>/export?format=yaml`).
`python scripts/seed_data.py` imports every file in this folder into a running server; the Docker image
contains them because it copies the whole `scripts/` folder.

| File | Hypergraph | Contents |
|------|------------|----------|
| `hgai-hypergraph-hello-world.export.yml` | `hello-world` | Three Stooges, Rat Pack and Beatles lineups (temporal `rel:member` edges, `rel:lineup` collections, inverse-of and broader axioms) |
| `hgai-hypergraph-eden.export.yml` | `eden` | A small family tree with `rel:parent` / `rel:child` / `rel:sibling` edges and inverse-of and transitive axioms |

```bash
python scripts/seed_data.py             # load everything here (idempotent: existing data is skipped)
python scripts/seed_data.py eden        # one seed, by graph id
python scripts/seed_data.py --list      # what is available
```

## Adding or updating a seed

1. Build the hypergraph in the UI, then **Export** it (or `GET /api/v1/graphs/<id>/export?format=yaml`).
2. Save it here as `hgai-hypergraph-<graph-id>.export.yml` (no timestamp).
3. Optional, recommended for a portable file: remove the `media` / `default_media_id` entries (media files are not part of an export) and the per-item `mutations` history.

`tests/test_seeds.py` checks that every file here is a valid, self-contained export that imports without errors.
