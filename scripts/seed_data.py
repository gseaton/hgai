#!/usr/bin/env python3
"""
HypergraphAI seed loader.

Loads the example hypergraphs in `scripts/seeds/` into a running server. Each
seed is an ordinary HypergraphAI hypergraph export file
(`hgai-hypergraph-<id>.export.yml`), so the same files can also be loaded from
the Web UI (Hypergraphs > Import) or the shell (`import -f <file>`). Nothing is
hard-coded here: add or edit a seed by adding or editing a file in that folder.

Usage:
    python scripts/seed_data.py                       # load every seed (hello-world, eden)
    python scripts/seed_data.py hello-world           # load one (by graph id) ...
    python scripts/seed_data.py eden ./my.export.yml  # ... or several, by id or file path
    python scripts/seed_data.py --list                # show the available seeds
    python scripts/seed_data.py --server http://localhost:8357 --user admin --password pwd357

Loading is idempotent: a hypergraph that already exists is merged into, and
nodes/edges that are already present are skipped, never overwritten.

Default server: http://localhost:$HGAI_PORT (8357 if HGAI_PORT is unset). In
the Docker image HGAI_PORT is 8000, so `docker-compose exec hgai python
scripts/seed_data.py` needs no options.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import yaml

SEEDS_DIR = Path(__file__).resolve().parent / "seeds"
SEED_SUFFIX = ".export.yml"


class SeedError(Exception):
    """A seed file could not be found, read, or is not a hypergraph export."""


def default_server() -> str:
    return f"http://localhost:{os.environ.get('HGAI_PORT', '8357')}"


def describe_seed(path: Path) -> Dict[str, object]:
    """Read just enough of a seed file to identify it: its graph id, label and
    size. Raises SeedError if it isn't a hypergraph export file."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise SeedError(f"{path}: cannot read as YAML ({e})")
    if not isinstance(doc, dict) or not doc.get("hgai_export"):
        raise SeedError(f"{path}: not a HypergraphAI export file (missing 'hgai_export')")
    graph = doc.get("graph") or {}
    if not graph.get("id"):
        raise SeedError(f"{path}: the export has no graph id")
    return {
        "id": graph["id"], "label": graph.get("label") or graph["id"], "path": path,
        "nodes": len(doc.get("nodes") or []), "edges": len(doc.get("edges") or []),
    }


def find_seeds(seeds_dir: Path = SEEDS_DIR) -> List[Dict[str, object]]:
    """Every `*.export.yml` in the seeds folder, ordered by file name."""
    return [describe_seed(p) for p in sorted(seeds_dir.glob(f"*{SEED_SUFFIX}"))]


def resolve_seeds(names: List[str], seeds_dir: Path = SEEDS_DIR) -> List[Dict[str, object]]:
    """No names -> every seed. A name is a seed's graph id (e.g. `eden`) or a
    path to any export file."""
    available = find_seeds(seeds_dir)
    if not names:
        return available
    by_id = {s["id"]: s for s in available}
    chosen = []
    for name in names:
        if name in by_id:
            chosen.append(by_id[name])
        elif Path(name).is_file():
            chosen.append(describe_seed(Path(name)))
        else:
            known = ", ".join(sorted(by_id)) or "none found"
            raise SeedError(f"'{name}' is neither a seed id ({known}) nor an export file")
    return chosen


async def wait_for_server(base_url: str, retries: int = 30, delay: float = 2.0):
    """Poll /health until the server is ready or retries are exhausted."""
    async with httpx.AsyncClient(timeout=5.0) as probe:
        for attempt in range(1, retries + 1):
            try:
                if (await probe.get(f"{base_url}/health")).status_code == 200:
                    print(f"  Server ready (attempt {attempt})")
                    return
            except Exception:
                pass
            print(f"  Waiting for server... ({attempt}/{retries})")
            await asyncio.sleep(delay)
    raise RuntimeError(f"Server at {base_url} did not become ready after {retries} attempts")


async def login(client: httpx.AsyncClient, server: str, username: str, password: str) -> str:
    resp = await client.post(f"{server}/api/v1/auth/token", data={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


async def import_seed(client: httpx.AsyncClient, server: str, token: str, seed: Dict[str, object]) -> Dict:
    """POST the export file's text to the server's import endpoint (mode=merge:
    create the hypergraph if missing, skip what already exists)."""
    resp = await client.post(
        f"{server}/api/v1/graphs/import",
        params={"mode": "merge"},
        content=Path(seed["path"]).read_bytes(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/x-yaml"},
    )
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise RuntimeError(f"HTTP {resp.status_code}: {detail}")
    return resp.json()


async def seed(server: str, username: str, password: str, seeds: List[Dict[str, object]]) -> int:
    """Load `seeds`; returns the number that failed."""
    server = server.rstrip("/")
    print(f"Connecting to {server} ...")
    await wait_for_server(server)

    failures = 0
    async with httpx.AsyncClient(timeout=120.0) as client:
        token = await login(client, server, username, password)
        print(f"Authenticated as '{username}'\n")
        for s in seeds:
            print(f"Loading '{s['id']}' ({s['label']}) from {Path(s['path']).name} "
                  f"— {s['nodes']} nodes, {s['edges']} edges")
            try:
                r = await import_seed(client, server, token, s)
            except Exception as e:
                failures += 1
                print(f"  [FAILED] {e}")
                continue
            action = "created" if r.get("graph_created") else "already existed, merged"
            print(f"  [ok] hypergraph {action}: {r['nodes']} nodes and {r['edges']} edges added"
                  f" ({r['skipped_nodes']} nodes / {r['skipped_edges']} edges already present)")
            for detail in r.get("error_details", []):
                print(f"       ! {detail}")
            if r.get("errors"):
                failures += 1

    if failures:
        print(f"\nSeed finished with {failures} problem(s).")
    else:
        first = seeds[0]["id"] if seeds else "<graph-id>"
        print("\nSeed data complete! Try this in the Query (SHQL) screen:\n"
              f"\n  shql:\n    from: {first}\n    where:\n      - node: ?n\n    select:\n      - ?n.id\n      - ?n.label\n      - ?n.type\n")
    return failures


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load the example hypergraphs in scripts/seeds/ (HypergraphAI export files) into a running server")
    parser.add_argument("seeds", nargs="*", help="Seed graph ids or export-file paths (default: every seed)")
    parser.add_argument("--list", action="store_true", help="List the available seeds and exit")
    parser.add_argument("--server", default=default_server(), help="HypergraphAI server URL (default: %(default)s)")
    parser.add_argument("--user", default="admin", help="Username")
    parser.add_argument("--password", default="pwd357", help="Password")
    args = parser.parse_args(argv)

    try:
        if args.list:
            for s in find_seeds():
                print(f"{s['id']:<14} {s['nodes']:>3} nodes {s['edges']:>3} edges  {Path(s['path']).name}  ({s['label']})")
            return 0
        seeds = resolve_seeds(args.seeds)
    except SeedError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if not seeds:
        print(f"ERROR: no seed files found in {SEEDS_DIR}", file=sys.stderr)
        return 2

    try:
        return 1 if asyncio.run(seed(args.server, args.user, args.password, seeds)) else 0
    except httpx.HTTPStatusError as e:
        hint = " (check --user / --password)" if e.response.status_code == 401 else ""
        print(f"ERROR: {e.request.method} {e.request.url} -> HTTP {e.response.status_code}{hint}", file=sys.stderr)
    except (httpx.HTTPError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
