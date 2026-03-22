#!/usr/bin/env python3
"""
HypergraphAI Seed Data Script
Populates the 'hello-world' hypergraph with example data demonstrating
hypernodes, hyperedges, and semantic relationships.

Usage:
    python scripts/seed_data.py [--server http://localhost:8000] [--user admin] [--password pwd357]
"""
import sys
import os
import argparse
import asyncio

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx


API_BASE = "http://localhost:8000/api/v1"
GRAPH_ID = "hello-world"


async def wait_for_server(base_url: str, retries: int = 30, delay: float = 2.0):
    """Poll /health until the server is ready or retries are exhausted."""
    import asyncio
    health_url = f"{base_url}/health"
    async with httpx.AsyncClient(timeout=5.0) as probe:
        for attempt in range(1, retries + 1):
            try:
                resp = await probe.get(health_url)
                if resp.status_code == 200:
                    print(f"  Server ready (attempt {attempt})")
                    return
            except Exception:
                pass
            print(f"  Waiting for server... ({attempt}/{retries})")
            await asyncio.sleep(delay)
    raise RuntimeError(f"Server at {base_url} did not become ready after {retries} attempts")


async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    resp = await client.post(
        f"{API_BASE}/auth/token",
        data={"username": username, "password": password},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def create_node(client: httpx.AsyncClient, token: str, graph_id: str, node: dict) -> dict:
    resp = await client.post(
        f"{API_BASE}/graphs/{graph_id}/nodes",
        json=node,
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 409:
        print(f"  [skip] Node '{node['id']}' already exists")
        return node
    resp.raise_for_status()
    return resp.json()


async def create_edge(client: httpx.AsyncClient, token: str, graph_id: str, edge: dict) -> dict:
    resp = await client.post(
        f"{API_BASE}/graphs/{graph_id}/edges",
        json=edge,
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 409:
        print(f"  [skip] Edge '{edge.get('id', edge.get('relation'))}' already exists")
        return edge
    resp.raise_for_status()
    return resp.json()


async def seed(server: str, username: str, password: str):
    global API_BASE
    API_BASE = f"{server}/api/v1"

    print(f"Connecting to {server} ...")
    await wait_for_server(server)

    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await login(client, username, password)
        print(f"Authenticated as '{username}'")

        # ── Hypernodes ────────────────────────────────────────────────────────
        print(f"\nCreating hypernodes in '{GRAPH_ID}' ...")

        nodes = [
            {
                "id": "three-stooges",
                "label": "Three Stooges",
                "type": "Group",
                "attributes": {
                    "formed": 1925,
                    "genre": "comedy",
                    "medium": ["film", "television", "stage"]
                },
                "tags": ["entertainment", "comedy", "classic"],
                "status": "active"
            },
            {
                "id": "moe-howard",
                "label": "Moe Howard",
                "type": "Person",
                "attributes": {
                    "first_name": "Moe",
                    "last_name": "Howard",
                    "birth_name": "Moses Horwitz",
                    "born": "1897-06-19",
                    "died": "1975-05-04",
                    "role": "leader",
                    "order": 1
                },
                "tags": ["stooge", "comedian"],
                "status": "active",
                "valid_from": "1897-06-19T00:00:00Z",
                "valid_to": "1975-05-04T23:59:59Z"
            },
            {
                "id": "larry-fine",
                "label": "Larry Fine",
                "type": "Person",
                "attributes": {
                    "first_name": "Larry",
                    "last_name": "Fine",
                    "birth_name": "Louis Feinberg",
                    "born": "1902-10-05",
                    "died": "1975-01-24",
                    "role": "middle stooge",
                    "order": 2
                },
                "tags": ["stooge", "comedian"],
                "status": "active",
                "valid_from": "1902-10-05T00:00:00Z",
                "valid_to": "1975-01-24T23:59:59Z"
            },
            {
                "id": "curly-howard",
                "label": "Curly Howard",
                "type": "Person",
                "attributes": {
                    "first_name": "Curly",
                    "last_name": "Howard",
                    "birth_name": "Jerome Lester Horwitz",
                    "born": "1903-10-22",
                    "died": "1952-01-18",
                    "role": "funny one",
                    "order": 3
                },
                "tags": ["stooge", "comedian", "original"],
                "status": "active",
                "valid_from": "1903-10-22T00:00:00Z",
                "valid_to": "1952-01-18T23:59:59Z"
            },
            {
                "id": "shemp-howard",
                "label": "Shemp Howard",
                "type": "Person",
                "attributes": {
                    "first_name": "Shemp",
                    "last_name": "Howard",
                    "birth_name": "Samuel Horwitz",
                    "born": "1895-03-11",
                    "died": "1955-11-22",
                    "role": "replacement stooge",
                    "order": 3
                },
                "tags": ["stooge", "comedian"],
                "status": "active",
                "valid_from": "1895-03-11T00:00:00Z",
                "valid_to": "1955-11-22T23:59:59Z"
            },
            {
                "id": "curly-joe-derita",
                "label": "Curly-Joe DeRita",
                "type": "Person",
                "attributes": {
                    "first_name": "Joe",
                    "last_name": "DeRita",
                    "born": "1909-07-12",
                    "died": "1993-07-03",
                    "role": "replacement stooge",
                    "order": 3
                },
                "tags": ["stooge", "comedian", "comeback"],
                "status": "active"
            },
            {
                "id": "has-member",
                "label": "Has Member",
                "type": "RelationType",
                "attributes": {
                    "description": "Indicates group membership",
                    "inverse": "member-of"
                },
                "tags": ["semantic", "relation"],
                "status": "active"
            },
            {
                "id": "sibling",
                "label": "Sibling",
                "type": "RelationType",
                "attributes": {
                    "description": "Sibling relationship between persons",
                    "symmetric": True
                },
                "tags": ["semantic", "relation", "symmetric"],
                "status": "active"
            }
        ]

        for node in nodes:
            result = await create_node(client, token, GRAPH_ID, node)
            print(f"  [ok] Node: {node['id']} ({node['type']})")

        # ── Hyperedges ────────────────────────────────────────────────────────
        print(f"\nCreating hyperedges in '{GRAPH_ID}' ...")

        edges = [
            # Original lineup (1932–1946): Moe, Larry, Curly
            {
                "id": "edge-stooges-original",
                "relation": "has-member",
                "label": "Three Stooges Original Lineup",
                "flavor": "hub",
                "members": [
                    {"node_id": "three-stooges", "seq": 0},
                    {"node_id": "moe-howard",    "seq": 1},
                    {"node_id": "larry-fine",    "seq": 2},
                    {"node_id": "curly-howard",  "seq": 3},
                ],
                "attributes": {
                    "era": "classic",
                    "shorts_count": 97
                },
                "tags": ["original", "classic"],
                "status": "active",
                "valid_from": "1932-01-01T00:00:00Z",
                "valid_to": "1946-12-31T23:59:59Z"
            },
            # Shemp era (1947–1955): Moe, Larry, Shemp
            {
                "id": "edge-stooges-shemp",
                "relation": "has-member",
                "label": "Three Stooges Shemp Era",
                "flavor": "hub",
                "members": [
                    {"node_id": "three-stooges", "seq": 0},
                    {"node_id": "moe-howard",    "seq": 1},
                    {"node_id": "larry-fine",    "seq": 2},
                    {"node_id": "shemp-howard",  "seq": 3},
                ],
                "attributes": {
                    "era": "shemp",
                    "shorts_count": 77
                },
                "tags": ["shemp"],
                "status": "active",
                "valid_from": "1947-01-01T00:00:00Z",
                "valid_to": "1955-11-22T23:59:59Z"
            },
            # Comeback era (1959–1970): Moe, Larry, Curly-Joe
            {
                "id": "edge-stooges-comeback",
                "relation": "has-member",
                "label": "Three Stooges Comeback Era",
                "flavor": "hub",
                "members": [
                    {"node_id": "three-stooges",   "seq": 0},
                    {"node_id": "moe-howard",       "seq": 1},
                    {"node_id": "larry-fine",       "seq": 2},
                    {"node_id": "curly-joe-derita", "seq": 3},
                ],
                "attributes": {
                    "era": "comeback",
                    "films_count": 6
                },
                "tags": ["comeback"],
                "status": "active",
                "valid_from": "1959-01-01T00:00:00Z",
                "valid_to": "1970-12-31T23:59:59Z"
            },
            # Sibling: Moe, Shemp, and Curly are brothers (Horwitz family)
            {
                "id": "edge-horwitz-siblings",
                "relation": "sibling",
                "label": "Horwitz Brothers",
                "flavor": "symmetric",
                "members": [
                    {"node_id": "moe-howard",   "seq": 1},
                    {"node_id": "shemp-howard", "seq": 2},
                    {"node_id": "curly-howard", "seq": 3},
                ],
                "attributes": {
                    "family": "Horwitz",
                    "stage_name_family": "Howard"
                },
                "tags": ["family", "siblings"],
                "status": "active"
            },
        ]

        for edge in edges:
            result = await create_edge(client, token, GRAPH_ID, edge)
            print(f"  [ok] Edge: {edge['id']} ({edge['relation']})")

        print("\nSeed data complete!")
        print(f"\nExample HQL queries to try:")
        print("""
  # Who were the Three Stooges in 1940?
  hql:
    from: hello-world
    at: "1940-06-01T00:00:00Z"
    match:
      type: hyperedge
      relation: has-member
    where:
      members:
        node_id: three-stooges
    return:
      - members
      - attributes

  # Find all siblings
  hql:
    from: hello-world
    match:
      type: hyperedge
      relation: sibling
    return:
      - members
      - attributes
""")


def main():
    parser = argparse.ArgumentParser(description="HypergraphAI seed data loader")
    parser.add_argument("--server", default="http://localhost:8000", help="HypergraphAI server URL")
    parser.add_argument("--user", default="admin", help="Username")
    parser.add_argument("--password", default="pwd357", help="Password")
    args = parser.parse_args()

    asyncio.run(seed(args.server, args.user, args.password))


if __name__ == "__main__":
    main()
