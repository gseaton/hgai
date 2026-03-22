## HypergraphAI Design Tenets

### Core HypergraphAI Engine

- HypergraphAI is a semantic knowledge hypergraph storage engine.
- HypergraphAI provides hypergraph composition for querying.
- HypergraphAI leverages semantic associations in hyperedges.
- HypergraphAI provides collections of hypernodes (entity hypernodes as well as hyperedge hypernodes) in hyperedge semantic relationships.
- HypergraphAI hyperedges have their own contextual document-based attributes.
- HypergraphAI hypernodes (entities; nouns) have their own contextual document-based attributes.
- HypergraphAI hyperedges are treated as hypernodes.
- HypergraphAI hyperedges are FIRST-CLASS elements.
- HypergraphAI supports composition of one or more hypergraph(s) for querying.
- HypergraphAI architecture provides HypergraphAI servers that may be combined into HypergraphAI meshes.
- HypergraphAI meshes may contain one or more HypergraphAI servers or HypergraphAI meshes.
- HypergraphAI allows for querying and composition across HypergraphAI servers in HypergraphAI meshes.
- HypergraphAI provides RBAC (role-based access control) for users/actors `accounts` of HypergraphAI.
- HypergraphAI provides `tags` field/attribute (list of strings) for every HypergraphAI artifact/component.
- HypergraphAI provides `status` field/attribute for every HypergraphAI artifact/component, where the attribute value of `active` makes those artifacts/components operations/visible to operations by default.
- HypergraphAI stores all of HypergraphAI control configurations in HypergraphAI semantic knowledge hypergraphs.
- HypergraphAI provides APIs that are MCP (model context protocol) server tools as needed and organized into logical MCP servers and associated MCP server tools.
- HypergraphAI hosts multiple MCP servers based on the needs and organization of HypergraphAI operations and processing.
- HypergraphAI allows for the creation, modifications, versioning, and archiving of nodes / entities.
- HypergraphAI allows for the creation, modifications, versioning, and archiving of hyperedges.
- HypergraphAI allows for inferencing across hypergraphs using semantic knowledge relationships.
- HypergraphAI leverages SKOS (simple knowledge organization system) semantic relationships to support inferencing, including, but not limited to, `broader` and `narrower`.
- HypergraphAI supports `logical` hypergraphs that compose one or more other logical or instantiated hypergraphs (possibly across HypergraphAI servers) and are treated as hypergraphs.
- HypergraphAI supports temporal existential qualifier mechanisms for pinning an assertion (hyperedge), query, or export to a particular moment in time.  For example, asking who is the President of the United States given a particular point-in-time (PIT) would return the appropriate response for that point-in-time.
- HypergraphAI servers have all logic and services necessary to manage and conduct HypergraphAI mesh operations.
- HypergraphAI provides caching mechanisms for queries with the ability to override or refresh caching with query calls.
- HypergraphAI is modular in design, meaning EVERYTHING is developed and deployed in the HypergraphAI server as modules (security, core operations, etc).

### HypergraphAI Standards and Declarative Plain Text Formats

- HypergraphAI provides standards for plain text declarative language for defining nodes with attributes (document-oriented, yaml or json) using offsides formatting that may be used by human users or generative AI models (MCP server tool calls, etc).
- HypergraphAI provides standards for plain text declarative language for defining hyperedges with attributes (document-oriented, yaml or json) using offsides formatting that may be used by human users or generative AI models (MCP server tool calls, etc).
- HypergraphAI provides standards for plain text declarative query language that support:
  - Simple single hypergraph queries.
  - Composable multi-hypergraph queries.
  - Aggregation functions.
  - Aliases for fields, nodes, hyperedges, and graphs (e.g. `as <alias>`) 
- HypergraphAI may leverage semantic web technologies, such as SKOS and OWL. However, HypergraphAI is a semantic knowledge HYPERGRAPH, not a graph.
- HypergraphAI prefers dot-delimited nesting notations when necessary (e.g `<grandparent>.<parent>.<child>`).

### HypergraphAI Import / Export

- HypergraphAI provides an import tool to ingest hyperedges, hypernodes into hypergraphs.
- HypergraphAI provides an export tool to export hypergraphs.

### HypergraphAI Technical Stack and Developer Friendliness

- HypergraphAI uses primarily the Python programming language.
- HypergraphAI uses FastAPI/FastMCP via the current Anthropic MCP Python SDK.
- HypergraphAI uses MongoDB for primary storage of semantic knowledge hypergraph artifacts.
  - database: 'hgai'
  - collections: name and number of collections as necessary/appropriate to support 
- HypergraphAI uses environment variables for some configuration settings (as appropriate).
- HypergraphAI is a Docker application and should be deployable to any Docker-enabled container platform.
- HypergraphAI servers may easily be run on local developer machines.
  - HypergraphAI code base supports `dotenv` for local developer environment variable files.
- HypergraphAI modules may be easily developed by third-parties using naming and other standards.
- HypergraphAI modules may be easily and SECURELY deployed in HypergraphAI servers.

### HypergraphAI Management

- HypergraphAI has an `admin` role that allows for management of users/agents (accounts), including granular access and operations control for HypergraphAI engine operations, hypergraphs, meshes, etc.
- HypergraphAI provides a management UI console only accessiable by `admin` role accounts

### HypergraphAI Documentation

- HypergraphAI provides/generates documentation for the HypergraphAI servers and meshes operations, maintenance, and concepts.
- HypergraphAI provides/generates documentation for creating a simple "hello, world." hypergraph with hyperedges and hypernodes.
- HypergraphAI provides/generates documentation on how to develop and deploy custom HypergraphAI modules.
- HypergraphAI code base provides/generates a `README.md` documentation markdown file that contains all pertinent information for developers and administrators to configure, run, and manage a HypergraphAI server and HypergraphAI meshes. 

### HypergraphAI User Interface (UI) / User Experience (UX)

- HypergraphAI has a user-friendly UI.
- HypergraphAI UI requires `account` login and authentication.
- HypergraphAI UI makes API server tool calls to the HypergraphAI API implemented via MCP server tools.

### HypergraphAI Miscellaneous Context

- HypergraphAI core engine and core modules are open-source under the MIT 2.0 license.
- HypergraphAI custom or advanced modules may have different licensing dictated by the authors of the modules.

### HypergraphAI Shell

- HypergraphAI provides an 'hgai' shell for CLI shell interaction with HypergraphAI servers/meshes.
  - provides secure user/pwd connections to HypergraphAI servers/meshes
  - provides up/down command history navigation at prompt
  - provides commands for all HypergraphAI operations supported by the HypergraphAI MCP Server API
  - provides in-shell `help` command to provide help for commands and other operations
