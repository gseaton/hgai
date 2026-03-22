#!/usr/bin/env python3
"""
HypergraphAI Interactive Shell (hgai)

A full-featured interactive CLI shell for interacting with HypergraphAI servers.
Supports all CRUD operations, HQL queries, import/export, and mesh operations.

Usage:
    python shell/hgai_shell.py
    python shell/hgai_shell.py --server http://localhost:8000 --user admin
    python shell/hgai_shell.py --server http://myserver:8000 --user myuser --password mypass
"""

import argparse
import json
import os
import sys
import textwrap
from getpass import getpass
from typing import Any, Dict, List, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.formatted_text import ANSI
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


# ─── ANSI Colors ─────────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    BLUE   = "\033[34m"
    CYAN   = "\033[36m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"

def cprint(msg, color=C.WHITE, bold=False):
    prefix = C.BOLD if bold else ""
    print(f"{prefix}{color}{msg}{C.RESET}")

def success(msg): cprint(f"  {msg}", C.GREEN)
def error(msg): cprint(f"  ERROR: {msg}", C.RED)
def warn(msg): cprint(f"  WARN: {msg}", C.YELLOW)
def info(msg): cprint(f"  {msg}", C.CYAN)
def dim(msg): cprint(f"  {msg}", C.DIM)


# ─── API Client ───────────────────────────────────────────────────────────────
class HgaiClient:
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(timeout=30.0) if HAS_HTTPX else None

    def _headers(self) -> Dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _request(self, method: str, path: str, body=None, params=None) -> Any:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required: pip install httpx")
        url = f"{self.base_url}/api/v1{path}"
        resp = self._client.request(
            method, url,
            headers=self._headers(),
            json=body,
            params={k: v for k, v in (params or {}).items() if v is not None},
        )
        if resp.status_code == 401:
            raise PermissionError("Authentication required or session expired")
        if resp.status_code == 403:
            raise PermissionError(f"Forbidden: {resp.json().get('detail', 'no permission')}")
        if resp.status_code == 404:
            raise KeyError(resp.json().get('detail', 'Not found'))
        if resp.status_code == 409:
            raise ValueError(resp.json().get('detail', 'Conflict'))
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.json()

    def login(self, username: str, password: str) -> Dict:
        if not HAS_HTTPX:
            raise RuntimeError("httpx required")
        resp = self._client.post(
            f"{self.base_url}/api/v1/auth/token",
            data={"username": username, "password": password, "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()

    def me(self): return self._request("GET", "/auth/me")
    def server_info(self): return self._request("GET", "/server/info")
    def health(self):
        resp = self._client.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    # Graphs
    def list_graphs(self, status="active", limit=100): return self._request("GET", "/graphs", params={"status": status, "limit": limit})
    def get_graph(self, gid): return self._request("GET", f"/graphs/{gid}")
    def create_graph(self, data): return self._request("POST", "/graphs", body=data)
    def update_graph(self, gid, data): return self._request("PUT", f"/graphs/{gid}", body=data)
    def delete_graph(self, gid): return self._request("DELETE", f"/graphs/{gid}")
    def graph_stats(self, gid): return self._request("GET", f"/graphs/{gid}/stats")
    def export_graph(self, gid): return self._request("POST", f"/graphs/{gid}/export")
    def import_graph(self, gid, data): return self._request("POST", f"/graphs/{gid}/import", body=data)

    # Nodes
    def list_nodes(self, gid, **kw): return self._request("GET", f"/graphs/{gid}/nodes", params=kw)
    def get_node(self, gid, nid): return self._request("GET", f"/graphs/{gid}/nodes/{nid}")
    def create_node(self, gid, data): return self._request("POST", f"/graphs/{gid}/nodes", body=data)
    def update_node(self, gid, nid, data): return self._request("PUT", f"/graphs/{gid}/nodes/{nid}", body=data)
    def delete_node(self, gid, nid): return self._request("DELETE", f"/graphs/{gid}/nodes/{nid}")

    # Edges
    def list_edges(self, gid, **kw): return self._request("GET", f"/graphs/{gid}/edges", params=kw)
    def get_edge(self, gid, eid): return self._request("GET", f"/graphs/{gid}/edges/{eid}")
    def create_edge(self, gid, data): return self._request("POST", f"/graphs/{gid}/edges", body=data)
    def update_edge(self, gid, eid, data): return self._request("PUT", f"/graphs/{gid}/edges/{eid}", body=data)
    def delete_edge(self, gid, eid): return self._request("DELETE", f"/graphs/{gid}/edges/{eid}")

    # Query (HQL)
    def query(self, hql: str, use_cache=True): return self._request("POST", "/query", body={"hql": hql, "use_cache": use_cache})
    def validate_query(self, hql: str): return self._request("POST", "/query/validate", body={"hql": hql})

    # Query (SHQL)
    def shql_query(self, shql: str, use_cache=True): return self._request("POST", "/shql/query", body={"shql": shql, "use_cache": use_cache})
    def shql_validate(self, shql: str): return self._request("POST", "/shql/validate", body={"shql": shql})

    # Accounts
    def list_accounts(self, **kw): return self._request("GET", "/accounts", params=kw)
    def get_account(self, username): return self._request("GET", f"/accounts/{username}")
    def create_account(self, data): return self._request("POST", "/accounts", body=data)
    def update_account(self, username, data): return self._request("PUT", f"/accounts/{username}", body=data)
    def delete_account(self, username): return self._request("DELETE", f"/accounts/{username}")


# ─── Shell ────────────────────────────────────────────────────────────────────
COMMANDS = [
    "connect", "disconnect", "whoami", "server",
    "use", "ls", "get", "create", "update", "delete",
    "delete-node", "delete-edge",
    "query", "validate",
    "shql", "shql-validate",
    "import", "export",
    "cls", "help", "exit", "quit",
]

HELP_TEXT = {
    "connect": "connect <url> [-u user] [-p]  —  Connect to a HypergraphAI server",
    "disconnect": "disconnect  —  Disconnect from current server",
    "whoami": "whoami  —  Show current user info",
    "server": "server  —  Show server info and health",
    "use": "use <graph-id>  —  Set active hypergraph for node/edge operations",
    "ls": textwrap.dedent("""\
        ls graphs              List all hypergraphs
        ls nodes               List hypernodes in active graph
        ls edges               List hyperedges in active graph
        ls accounts            List accounts (admin)
        ls meshes              List meshes (admin)"""),
    "get": textwrap.dedent("""\
        get graph <id>         Get a hypergraph
        get node <id>          Get a hypernode
        get edge <id>          Get a hyperedge
        get account <user>     Get an account (admin)"""),
    "create": textwrap.dedent("""\
        create graph           Create a hypergraph (interactive YAML)
        create node            Create a hypernode (interactive YAML)
        create edge            Create a hyperedge (interactive YAML)
        create account         Create an account (admin, interactive YAML)"""),
    "update": textwrap.dedent("""\
        update graph <id>      Update a hypergraph (interactive YAML)
        update node <id>       Update a hypernode (interactive YAML)
        update edge <id>       Update a hyperedge (interactive YAML)"""),
    "delete": textwrap.dedent("""\
        delete graph <id>      Delete a hypergraph (and all its nodes/edges)
        delete node <id>       Delete a hypernode (active graph)
        delete edge <id>       Delete a hyperedge (active graph)
        delete account <user>  Delete an account (admin)"""),
    "delete-node": "delete-node <id>  —  Delete a hypernode from the active graph (alias: dn)",
    "delete-edge": "delete-edge <id>  —  Delete a hyperedge from the active graph (alias: de)",
    "query": textwrap.dedent("""\
        query                  Run HQL query (enter YAML, end with a line containing just '---')
        query -f <file>        Run HQL query from a YAML file"""),
    "validate": "validate  —  Validate an HQL query (same input as 'query')",
    "shql": textwrap.dedent("""\
        shql                   Run SHQL query (enter YAML, end with a line containing just '---')
        shql -f <file>         Run SHQL query from a YAML file
        shql --no-cache        Run SHQL query bypassing the cache
        Alias: sq"""),
    "shql-validate": textwrap.dedent("""\
        shql-validate          Validate an SHQL query (same input as 'shql')
        shql-validate -f <file>  Validate an SHQL query from a file
        Alias: sv"""),
    "import": "import -f <file> [-g <graph-id>]  —  Import nodes/edges from YAML file",
    "export": "export [-o <file>] [-g <graph-id>]  —  Export active graph to YAML",
    "help": "help [command]  —  Show help for a command or list all commands",
    "exit": "exit  —  Exit the shell",
}


class HgaiShell:
    def __init__(self, server: str = None, username: str = None, password: str = None):
        self.client: Optional[HgaiClient] = None
        self.server_url: Optional[str] = server
        self.username: Optional[str] = username
        self.active_graph: Optional[str] = None
        self.running = True

        # Auto-connect if server provided
        if server:
            self._do_connect(server, username, password)

    # ── Prompt ────────────────────────────────────────────────────────────────
    def _prompt_str(self) -> str:
        parts = []
        if self.client and self.username:
            parts.append(f"{C.CYAN}{self.username}{C.RESET}@{C.BLUE}{self.server_url}{C.RESET}")
        if self.active_graph:
            parts.append(f"{C.GREEN}[{self.active_graph}]{C.RESET}")
        return ("  ".join(parts) + " " if parts else "") + f"{C.BOLD}{C.WHITE}hgai>{C.RESET} "

    def _read_multiline(self, prompt="  > ", end_marker="---") -> str:
        """Read multi-line input until end_marker line."""
        print(f"  (enter YAML, finish with a line containing just '{end_marker}')")
        lines = []
        while True:
            try:
                line = input(f"  {C.DIM}>{C.RESET} ")
                if line.strip() == end_marker:
                    break
                lines.append(line)
            except EOFError:
                break
        return "\n".join(lines)

    def _print_json(self, data: Any):
        if isinstance(data, (dict, list)):
            try:
                if HAS_YAML:
                    print(f"\n{C.DIM}{yaml.dump(data, default_flow_style=False, allow_unicode=True)}{C.RESET}")
                else:
                    print(f"\n{json.dumps(data, indent=2, default=str)}\n")
            except Exception:
                print(json.dumps(data, indent=2, default=str))
        else:
            print(data)

    def _print_table(self, rows: List[Dict], cols: List[str], col_labels: List[str] = None):
        if not rows:
            dim("  (no results)")
            return
        labels = col_labels or cols
        widths = [max(len(labels[i]), max(len(str(r.get(c, ''))) for r in rows)) for i, c in enumerate(cols)]
        widths = [min(w, 40) for w in widths]

        header = "  " + "  ".join(f"{C.BOLD}{labels[i]:<{widths[i]}}{C.RESET}" for i, c in enumerate(cols))
        print(header)
        print("  " + "  ".join("-" * w for w in widths))
        for row in rows:
            line = "  " + "  ".join(f"{str(row.get(c, '')):<{widths[i]}}"[:widths[i]] for i, c in enumerate(cols))
            print(line)
        print()

    # ── Connection ────────────────────────────────────────────────────────────
    def _do_connect(self, server: str, username: str = None, password: str = None):
        if not server.startswith("http"):
            server = "http://" + server
        self.server_url = server

        if not username:
            username = input("  Username: ").strip() or "admin"
        if not password:
            password = getpass("  Password: ")

        try:
            client = HgaiClient(server)
            token_resp = client.login(username, password)
            client.token = token_resp["access_token"]
            self.client = client
            self.username = username
            success(f"Connected to {server} as '{username}'")
            info(f"Roles: {', '.join(token_resp.get('roles', []))}")
        except Exception as e:
            error(f"Connection failed: {e}")

    # ── Command Parser ────────────────────────────────────────────────────────
    def handle(self, line: str):
        line = line.strip()
        if not line or line.startswith("#"):
            return

        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:]

        handlers = {
            "connect": self.cmd_connect,
            "disconnect": self.cmd_disconnect,
            "whoami": self.cmd_whoami,
            "server": self.cmd_server,
            "use": self.cmd_use,
            "ls": self.cmd_ls,
            "get": self.cmd_get,
            "create": self.cmd_create,
            "update": self.cmd_update,
            "delete": self.cmd_delete,
            "delete-node": self.cmd_delete_node,
            "delete-edge": self.cmd_delete_edge,
            "dn": self.cmd_delete_node,
            "de": self.cmd_delete_edge,
            "query": self.cmd_query,
            "validate": self.cmd_validate,
            "shql": self.cmd_shql,
            "shql-validate": self.cmd_shql_validate,
            "sq": self.cmd_shql,
            "sv": self.cmd_shql_validate,
            "import": self.cmd_import,
            "export": self.cmd_export,
            "help": self.cmd_help,
            "cls": lambda a: self.cmd_cls(),
            "exit": lambda a: self._exit(),
            "quit": lambda a: self._exit(),
            "?": lambda a: self.cmd_help([]),
        }
        handler = handlers.get(cmd)
        if handler:
            try:
                handler(args)
            except PermissionError as e:
                error(str(e))
            except KeyError as e:
                error(f"Not found: {e}")
            except ValueError as e:
                error(str(e))
            except Exception as e:
                error(f"Command failed: {e}")
        else:
            error(f"Unknown command: '{cmd}'. Type 'help' for help.")

    def _require_connection(self):
        if not self.client:
            raise RuntimeError("Not connected. Use: connect <server-url>")

    def _require_graph(self):
        self._require_connection()
        if not self.active_graph:
            raise RuntimeError("No active graph. Use: use <graph-id>")

    def _exit(self):
        self.running = False

    # ── Commands ──────────────────────────────────────────────────────────────
    def cmd_connect(self, args):
        server = args[0] if args else input("  Server URL [http://localhost:8000]: ").strip() or "http://localhost:8000"
        username = None; password = None
        for i, a in enumerate(args):
            if a in ("-u", "--user") and i+1 < len(args): username = args[i+1]
            if a in ("-p", "--password") and i+1 < len(args): password = args[i+1]
        self._do_connect(server, username, password)

    def cmd_disconnect(self, args):
        self.client = None; self.username = None; self.active_graph = None
        info("Disconnected")

    def cmd_whoami(self, args):
        self._require_connection()
        me = self.client.me()
        self._print_json(me)

    def cmd_server(self, args):
        self._require_connection()
        try:
            h = self.client.health()
            info(f"Status: {h.get('status', '?')}")
        except Exception as e:
            warn(f"Health check failed: {e}")
        si = self.client.server_info()
        self._print_json(si)

    def cmd_use(self, args):
        self._require_connection()
        if not args:
            info(f"Active graph: {self.active_graph or '(none)'}")
            return
        gid = args[0]
        try:
            self.client.get_graph(gid)
            self.active_graph = gid
            success(f"Active graph set to: {gid}")
        except KeyError:
            error(f"Hypergraph '{gid}' not found")

    def cmd_ls(self, args):
        self._require_connection()
        what = args[0].lower() if args else "graphs"

        if what in ("graphs", "graph"):
            resp = self.client.list_graphs(status="", limit=200)
            rows = resp.get("items", [])
            print(f"\n  {C.BOLD}Hypergraphs ({resp.get('total',0)} total){C.RESET}")
            self._print_table(rows, ["id", "label", "type", "status", "node_count", "edge_count"],
                              ["ID", "Label", "Type", "Status", "Nodes", "Edges"])

        elif what in ("nodes", "node"):
            self._require_graph()
            resp = self.client.list_nodes(self.active_graph, limit=100, status="active")
            rows = resp.get("items", [])
            print(f"\n  {C.BOLD}Hypernodes in '{self.active_graph}' ({resp.get('total',0)} total){C.RESET}")
            self._print_table(rows, ["id", "label", "type", "status"], ["ID", "Label", "Type", "Status"])

        elif what in ("edges", "edge"):
            self._require_graph()
            resp = self.client.list_edges(self.active_graph, limit=100)
            rows = resp.get("items", [])
            print(f"\n  {C.BOLD}Hyperedges in '{self.active_graph}' ({resp.get('total',0)} total){C.RESET}")
            for row in rows:
                members = ", ".join(m.get("node_id","?") for m in (row.get("members") or []))
                row["members_summary"] = members[:40]
            self._print_table(rows, ["id", "relation", "flavor", "members_summary", "status"],
                              ["ID", "Relation", "Flavor", "Members", "Status"])

        elif what in ("accounts", "account"):
            resp = self.client.list_accounts(limit=100)
            rows = resp.get("items", [])
            print(f"\n  {C.BOLD}Accounts ({resp.get('total',0)} total){C.RESET}")
            for row in rows:
                row["roles_str"] = ", ".join(row.get("roles") or [])
            self._print_table(rows, ["username", "email", "roles_str", "status"], ["Username", "Email", "Roles", "Status"])

        else:
            error(f"Unknown entity: '{what}'. Use: graphs, nodes, edges, accounts")

    def cmd_get(self, args):
        self._require_connection()
        if len(args) < 2:
            error("Usage: get <graph|node|edge|account> <id>")
            return
        what, eid = args[0].lower(), args[1]

        if what == "graph":
            data = self.client.get_graph(eid)
        elif what == "node":
            self._require_graph()
            data = self.client.get_node(self.active_graph, eid)
        elif what == "edge":
            self._require_graph()
            data = self.client.get_edge(self.active_graph, eid)
        elif what == "account":
            data = self.client.get_account(eid)
        else:
            error(f"Unknown entity: '{what}'"); return

        self._print_json(data)

    def cmd_create(self, args):
        self._require_connection()
        what = args[0].lower() if args else ""

        if what == "graph":
            print("\n  Creating Hypergraph (enter YAML, end with ---):")
            template = "id: my-graph\nlabel: My Hypergraph\ndescription: ''\ntags: []\nattributes: {}"
            print(f"\n  Template:\n{C.DIM}{textwrap.indent(template, '    ')}{C.RESET}\n")
            raw = self._read_multiline()
            if not raw.strip(): return
            data = yaml.safe_load(raw) if HAS_YAML else json.loads(raw)
            result = self.client.create_graph(data)
            success(f"Hypergraph created: {result.get('id')}")

        elif what == "node":
            self._require_graph()
            print(f"\n  Creating Hypernode in '{self.active_graph}' (enter YAML, end with ---):")
            template = "id: my-node\nlabel: My Node\ntype: Entity\ndescription: ''\nattributes: {}\ntags: []"
            print(f"\n  Template:\n{C.DIM}{textwrap.indent(template, '    ')}{C.RESET}\n")
            raw = self._read_multiline()
            if not raw.strip(): return
            data = yaml.safe_load(raw) if HAS_YAML else json.loads(raw)
            result = self.client.create_node(self.active_graph, data)
            success(f"Hypernode created: {result.get('id')}")

        elif what == "edge":
            self._require_graph()
            print(f"\n  Creating Hyperedge in '{self.active_graph}' (enter YAML, end with ---):")
            template = textwrap.dedent("""\
                relation: has-member
                label: My Edge
                flavor: hub
                members:
                  - node_id: node-1
                    seq: 0
                  - node_id: node-2
                    seq: 1
                attributes: {}
                tags: []""")
            print(f"\n  Template:\n{C.DIM}{textwrap.indent(template, '    ')}{C.RESET}\n")
            raw = self._read_multiline()
            if not raw.strip(): return
            data = yaml.safe_load(raw) if HAS_YAML else json.loads(raw)
            result = self.client.create_edge(self.active_graph, data)
            success(f"Hyperedge created: {result.get('id')} (hyperkey: {result.get('hyperkey')})")

        elif what == "account":
            print("\n  Creating Account (enter YAML, end with ---):")
            template = "username: myuser\npassword: mypassword\nemail: user@example.com\nroles: [user]\nstatus: active"
            print(f"\n  Template:\n{C.DIM}{textwrap.indent(template, '    ')}{C.RESET}\n")
            raw = self._read_multiline()
            if not raw.strip(): return
            data = yaml.safe_load(raw) if HAS_YAML else json.loads(raw)
            result = self.client.create_account(data)
            success(f"Account created: {result.get('username')}")

        else:
            error(f"Usage: create <graph|node|edge|account>")

    def cmd_update(self, args):
        self._require_connection()
        if len(args) < 2:
            error("Usage: update <graph|node|edge> <id>")
            return
        what, eid = args[0].lower(), args[1]

        if what == "graph":
            existing = self.client.get_graph(eid)
        elif what == "node":
            self._require_graph()
            existing = self.client.get_node(self.active_graph, eid)
        elif what == "edge":
            self._require_graph()
            existing = self.client.get_edge(self.active_graph, eid)
        else:
            error(f"Unknown entity: '{what}'"); return

        print(f"\n  Current state of '{eid}':")
        self._print_json(existing)
        print(f"\n  Enter updated fields as YAML (end with ---):")
        raw = self._read_multiline()
        if not raw.strip(): return
        data = yaml.safe_load(raw) if HAS_YAML else json.loads(raw)

        if what == "graph":
            result = self.client.update_graph(eid, data)
        elif what == "node":
            result = self.client.update_node(self.active_graph, eid, data)
        elif what == "edge":
            result = self.client.update_edge(self.active_graph, eid, data)

        success(f"Updated: {eid}")
        self._print_json(result)

    def cmd_delete(self, args):
        self._require_connection()
        if len(args) < 2:
            error("Usage: delete <graph|node|edge|account> <id>")
            return
        what, eid = args[0].lower(), args[1]
        confirm = input(f"  Delete {what} '{eid}'? [y/N] ").strip().lower()
        if confirm != 'y':
            info("Cancelled")
            return

        if what == "graph":
            self.client.delete_graph(eid)
            if self.active_graph == eid: self.active_graph = None
        elif what == "node":
            self._require_graph()
            self.client.delete_node(self.active_graph, eid)
        elif what == "edge":
            self._require_graph()
            self.client.delete_edge(self.active_graph, eid)
        elif what == "account":
            self.client.delete_account(eid)
        else:
            error(f"Unknown entity: '{what}'"); return

        success(f"Deleted: {eid}")

    def cmd_delete_node(self, args):
        self._require_graph()
        if not args:
            error("Usage: delete-node <id>")
            return
        nid = args[0]
        confirm = input(f"  Delete hypernode '{nid}' from '{self.active_graph}'? [y/N] ").strip().lower()
        if confirm != 'y':
            info("Cancelled")
            return
        self.client.delete_node(self.active_graph, nid)
        success(f"Hypernode '{nid}' deleted from '{self.active_graph}'")

    def cmd_delete_edge(self, args):
        self._require_graph()
        if not args:
            error("Usage: delete-edge <id>")
            return
        eid = args[0]
        confirm = input(f"  Delete hyperedge '{eid}' from '{self.active_graph}'? [y/N] ").strip().lower()
        if confirm != 'y':
            info("Cancelled")
            return
        self.client.delete_edge(self.active_graph, eid)
        success(f"Hyperedge '{eid}' deleted from '{self.active_graph}'")

    def cmd_query(self, args):
        self._require_connection()
        use_cache = True

        if "-f" in args:
            idx = args.index("-f")
            filepath = args[idx+1] if idx+1 < len(args) else None
            if not filepath:
                error("Usage: query -f <file>"); return
            with open(filepath) as f:
                hql = f.read()
        else:
            print("\n  Enter HQL query (YAML format, end with line containing just ---):")
            if not self.active_graph:
                dim("  Hint: Use 'use <graph-id>' to set a default graph, or specify 'from' in your query")
            hql = self._read_multiline()

        if "--no-cache" in args:
            use_cache = False

        if not hql.strip():
            return

        # Add default graph if not specified and active_graph is set
        if self.active_graph and "from:" not in hql:
            hql = f"hql:\n  from: {self.active_graph}\n" + "\n".join("  " + l for l in hql.split("\n"))

        try:
            result = self.client.query(hql, use_cache=use_cache)
            count = result.get("count", 0)
            alias = result.get("alias", "result")
            cached = result.get("meta", {}).get("cached", False)
            info(f"Query '{alias}': {count} results" + (" (cached)" if cached else ""))
            self._print_json(result)
        except Exception as e:
            error(f"Query failed: {e}")

    def cmd_validate(self, args):
        self._require_connection()
        if "-f" in args:
            idx = args.index("-f")
            filepath = args[idx+1] if idx+1 < len(args) else None
            with open(filepath) as f:
                hql = f.read()
        else:
            print("\n  Enter HQL query to validate (end with ---):")
            hql = self._read_multiline()

        try:
            result = self.client.validate_query(hql)
            if result.get("valid"):
                success("HQL is valid")
            else:
                error("Validation errors:")
                for e in result.get("errors", []):
                    print(f"    - {e}")
        except Exception as e:
            error(f"Validation failed: {e}")

    def cmd_shql(self, args):
        self._require_connection()
        use_cache = "--no-cache" not in args

        if "-f" in args:
            idx = args.index("-f")
            filepath = args[idx + 1] if idx + 1 < len(args) else None
            if not filepath:
                error("Usage: shql -f <file>"); return
            with open(filepath) as f:
                shql = f.read()
        else:
            print("\n  Enter SHQL query (YAML format, end with line containing just ---):")
            if not self.active_graph:
                dim("  Hint: Use 'use <graph-id>' to set a default graph, or specify 'from' in your query")
            shql = self._read_multiline()

        if not shql.strip():
            return

        # Detect accidental HQL queries entered in the SHQL command
        stripped = shql.lstrip()
        if stripped.startswith("hql:") or stripped.startswith("{\"hql\""):
            error("This looks like an HQL query (top-level key is 'hql:').")
            info("Use the 'query' command for HQL, or rewrite with 'shql:' as the top-level key.")
            return

        # Auto-inject active graph as 'from' if not already present
        if self.active_graph and "from:" not in shql:
            shql = f"shql:\n  from: {self.active_graph}\n" + "\n".join("  " + l for l in shql.split("\n"))

        try:
            result = self.client.shql_query(shql, use_cache=use_cache)
            count = result.get("count", 0)
            alias = result.get("alias", "result")
            cached = result.get("meta", {}).get("cached", False)
            info(f"SHQL '{alias}': {count} results" + (" (cached)" if cached else ""))
            self._print_json(result)
        except Exception as e:
            error(f"SHQL query failed: {e}")

    def cmd_shql_validate(self, args):
        self._require_connection()
        if "-f" in args:
            idx = args.index("-f")
            filepath = args[idx + 1] if idx + 1 < len(args) else None
            if not filepath:
                error("Usage: shql-validate -f <file>"); return
            with open(filepath) as f:
                shql = f.read()
        else:
            print("\n  Enter SHQL query to validate (end with ---):")
            shql = self._read_multiline()

        try:
            result = self.client.shql_validate(shql)
            if result.get("valid"):
                success("SHQL is valid")
            else:
                error("Validation errors:")
                for e in result.get("errors", []):
                    print(f"    - {e}")
        except Exception as e:
            error(f"SHQL validation failed: {e}")

    def cmd_import(self, args):
        self._require_connection()
        filepath = None; graph_id = None

        for i, a in enumerate(args):
            if a == "-f" and i+1 < len(args): filepath = args[i+1]
            if a == "-g" and i+1 < len(args): graph_id = args[i+1]

        if not filepath:
            error("Usage: import -f <file> [-g <graph-id>]"); return

        gid = graph_id or self.active_graph
        if not gid:
            error("Specify graph with -g or use 'use <graph-id>'"); return

        with open(filepath) as f:
            if HAS_YAML:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        result = self.client.import_graph(gid, data)
        success(f"Import complete: {result.get('nodes',0)} nodes, {result.get('edges',0)} edges imported ({result.get('errors',0)} errors)")

    def cmd_export(self, args):
        self._require_connection()
        outfile = None; graph_id = None

        for i, a in enumerate(args):
            if a == "-o" and i+1 < len(args): outfile = args[i+1]
            if a == "-g" and i+1 < len(args): graph_id = args[i+1]

        gid = graph_id or self.active_graph
        if not gid:
            error("Specify graph with -g or use 'use <graph-id>'"); return

        data = self.client.export_graph(gid)
        if outfile:
            with open(outfile, "w") as f:
                if HAS_YAML:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(data, f, indent=2, default=str)
            success(f"Exported '{gid}' to: {outfile}")
        else:
            self._print_json(data)

    def cmd_cls(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def cmd_help(self, args):
        if args and args[0] in HELP_TEXT:
            print(f"\n  {C.BOLD}{args[0]}{C.RESET}")
            for line in HELP_TEXT[args[0]].split("\n"):
                print(f"    {line}")
            print()
        else:
            print(f"\n  {C.BOLD}{C.CYAN}HypergraphAI Shell (hgai){C.RESET}")
            print(f"  {C.DIM}Semantic Hypergraph Knowledge Platform{C.RESET}\n")
            print(f"  {C.BOLD}Commands:{C.RESET}")
            for cmd, txt in HELP_TEXT.items():
                first_line = txt.split("\n")[0]
                print(f"    {C.YELLOW}{cmd:<12}{C.RESET} {first_line}")
            print(f"\n  Type {C.BOLD}help <command>{C.RESET} for detailed help on a command.")
            print(f"  Use {C.BOLD}Ctrl+C{C.RESET} or {C.BOLD}exit{C.RESET} to quit.\n")

    # ── Run loop ──────────────────────────────────────────────────────────────
    def run(self):
        print(f"\n  {C.BOLD}{C.CYAN}  HypergraphAI Shell  {C.RESET}")
        print(f"  {C.DIM}Type 'help' for commands. Type 'exit' to quit.{C.RESET}\n")

        if not self.client:
            info("Not connected. Use: connect <server-url>")

        if HAS_PROMPT_TOOLKIT:
            history_file = os.path.expanduser("~/.hgai_shell_history")
            completer = WordCompleter(COMMANDS, ignore_case=True)
            session = PromptSession(
                history=FileHistory(history_file),
                auto_suggest=AutoSuggestFromHistory(),
                completer=completer,
            )
        else:
            session = None

        while self.running:
            try:
                prompt = self._prompt_str()
                if session:
                    line = session.prompt(ANSI(prompt))
                else:
                    line = input(prompt)
                self.handle(line)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print()
                break

        print(f"\n  {C.DIM}Goodbye.{C.RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="HypergraphAI Interactive Shell",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python shell/hgai_shell.py
              python shell/hgai_shell.py --server http://localhost:8000 --user admin
              python shell/hgai_shell.py --server http://myserver:8000 -u myuser -p mypassword
        """)
    )
    parser.add_argument("--server", "-s", default=None, help="HypergraphAI server URL")
    parser.add_argument("--user", "-u", default=None, help="Username")
    parser.add_argument("--password", "-p", default=None, help="Password (use env var HGAI_PASSWORD in production)")
    parser.add_argument("--graph", "-g", default=None, help="Initial active graph ID")
    args = parser.parse_args()

    # Allow password from environment
    password = args.password or os.environ.get("HGAI_PASSWORD")

    shell = HgaiShell(server=args.server, username=args.user, password=password)

    if args.graph:
        shell.active_graph = args.graph
        info(f"Active graph: {args.graph}")

    shell.run()


if __name__ == "__main__":
    main()
