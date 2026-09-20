---
id: help-shell
label: The hgsh shell
name: shell
description: The interactive command-line shell for HypergraphAI — connecting, browsing, editing, and running SHQL.
tags: ["//Integration", shell, cli, hgsh, command-line]
status: active
---

# The hgsh shell

`hgsh` is an interactive CLI for HypergraphAI operations. Start it with the script in the project root:

```bash
./hgsh.sh                                       # connect to the default local server
./hgsh.sh --server http://myserver:8357 --user admin
```

## Commands

```
connect <url> [-u user] [-p]   Connect to a HypergraphAI server
disconnect                      Disconnect
use <graph-id>                  Set the active hypergraph
whoami                          Show the current user

ls graphs | nodes | edges       List hypergraphs / nodes / edges (active graph)
get node|edge|graph <id>        Show one item
create node|edge|graph          Create (opens a YAML editor)
update node|edge <id>           Update
delete node|edge <id>           Delete

shql                            Run SHQL (paste YAML, finish with EOF)
shql -f <file>                  Run SHQL from a file
import -f <file> [-g id] [--merge]  Import a hypergraph from an export file
export [-o <file>] [-g id]          Export the active (or -g) hypergraph to a file

help [command]                  Show help
exit                            Leave the shell
```

`export` writes `hgai-hypergraph-<id>-<timestamp>.export.yml` (or the name you give with `-o`); `import` creates a hypergraph from such a file, or loads into an existing one with `--merge`. See [Exporting and importing hypergraphs](help:help-export-import).

Queries run in the shell use the same engine as the [Query screen](help:help-query-screen); see [SHQL overview](help:help-shql-overview).
