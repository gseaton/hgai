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
import -f <file>                Import nodes/edges from a YAML file
export -o <file>                Export the active graph to YAML

help [command]                  Show help
exit                            Leave the shell
```

Queries run in the shell use the same engine as the [Query screen](help:help-query-screen); see [SHQL overview](help:help-shql-overview).
