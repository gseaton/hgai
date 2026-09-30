---
title: "HypergraphAI Partner Summary for the Anduril Lattice Partner Program"
description: "The roles HypergraphAI plays as a semantic memory and knowledge layer for Anduril Lattice, and how it would partner with Anduril and other Lattice partners"
generated: "2026-09-30T08:20:39"
audience: "Anduril Lattice Partner Program reviewers and prospective Lattice partners"
status: "Draft partner proposal. See Status and Scope Notes."
---

# HypergraphAI and the Anduril Lattice Partner Program

## Partner Summary

Program reference: https://www.anduril.com/lattice/lattice-partner-program

## Integration Summary

HypergraphAI plans to integrate with Lattice through the Lattice SDK (REST and gRPC APIs and the open entity and tasking data models) as a semantic knowledge and agent memory data service that runs beside Lattice at the tactical edge and at the enterprise. It would mirror and enrich Lattice entities and tasks in persisted semantic hypergraphs, and publish analyst and agent conclusions back to Lattice. It would also expose the same knowledge through the Model Context Protocol (MCP) to AI applications, agents and models from Lattice partners and Anduril, so they share one governed, cross-vendor, cross-host, cross-platform, cross-model, cross-session context memory. Planned partner-facing integrations include AI and model platforms, autonomous platform and sensor providers, space data providers, and cloud and edge infrastructure providers, each contributing or consuming data through the shared semantic layer.

## 1. Summary

HypergraphAI is a semantic hypergraph knowledge platform. A single hyperedge connects any number of nodes, semantics are stored as data, time and provenance are built in, and every operation is available to AI agents through MCP as well as REST, a query language (SHQL), a shell and a web UI.

The Lattice Partner Program describes an ecosystem where partners create, integrate and deploy capabilities through Lattice, using open data models and standard interfaces. Lattice provides the mesh, the shared operational picture and tasking. HypergraphAI is proposed as the **semantic memory and knowledge layer** that partners and Anduril can share on top of that picture: durable, governed and queryable meaning that people and AI agents from many vendors use together.

HypergraphAI fills five roles, described in section 3:

1. Universal agentic context memory
2. Universal agentic semantic knowledge store
3. Human analyst semantic knowledge platform
4. Semantic integration layer
5. Persisted enterprise and operational semantic knowledge hypergraphs

## 2. Why the Lattice Ecosystem Needs a Shared Semantic Layer

The program's stated model is many partners, each contributing a capability (a vehicle, a sensor feed, a model, a cloud, an AI planner) into Lattice. That model creates a coordination problem above the level of entities and tasks.

| Ecosystem need | Gap without a shared semantic layer | What HypergraphAI adds |
|---|---|---|
| Many partner AI systems work the same mission | Each keeps private, session-bound context and cannot see what the others learned | One shared, permissioned memory that any MCP-capable or REST client reads and writes |
| Operations outlast any session, model version or vendor choice | Context is lost on session end, model swap or host change | Durable memory independent of vendor, host, model and session |
| Partners publish data with different schemas and vocabularies | Point-to-point mappings that do not scale and hide meaning | Meaning modeled once, as data: types, relationships and vocabularies |
| Analysts must audit what a machine concluded | Conclusions with no traceable basis | Provenance, point-in-time queries and inspectable inference |
| Relationships are rarely pairwise | Pairwise graphs flatten a mission into disconnected links | N-ary hyperedges keep the whole relationship as one first-class object |

## 3. Primary Roles

### 3.1 Universal Agentic Context Memory

Agents need memory that is not owned by any one vendor, host or session.

| Dimension | What it means | How HypergraphAI delivers it |
|---|---|---|
| Cross-vendor | Agents and applications from different Lattice partners share what they know | Memory sits in an open, vendor-neutral store. Any agent that speaks MCP or REST uses the same memory. |
| Cross-host | Agents on different machines, edge nodes, enclaves or sites share memory | The store is a network service. Servers can be joined into a mesh and queried together. |
| Cross-model | Swapping or mixing language models does not lose context | Context is stored as structured hypergraph data, not as model-specific state or prompts. |
| Cross-session | Work resumes after a session ends, restarts or hands off | Context is persisted with timestamps and point-in-time history, so an agent can recall what was known at any earlier moment. |

Access is governed. Every MCP call runs as the authenticated account and is checked with the same role-based rules as the REST API. Writes are audited under the caller. A restricted partner agent gets its own account with limited graph access and operations.

### 3.2 Universal Agentic Semantic Knowledge Store

The same store serves two lifetimes of agent knowledge.

| Mode | Purpose | Pattern |
|---|---|---|
| Transient, per-job | Working knowledge for a single task, mission phase or agent run | Create a scoped hypergraph for the job, let agents read and write facts and intermediate conclusions, then archive or delete it when the job ends. |
| Persisted, long-term | Knowledge that should outlive any job | Promote validated facts from a job graph into a long-lived hypergraph that later jobs and other agents build on. |

Both modes use the same model and query language, so promoting knowledge from a job graph to a persisted graph is a data operation, not a re-implementation. A single query can span a job graph and a long-term graph.

### 3.3 Human Analyst Semantic Knowledge Platform

Analysts and agents work on the same knowledge through interfaces suited to each.

- **Web UI** for browsing, visualizing and editing hypergraphs, running queries, and reading notes and media attached to entities.
- **SHQL** for precise queries: multi-hop joins, filters, optional and union patterns, aggregation, sorting, and point-in-time queries ("what did we believe at time T").
- **Shell** for scripted and repeatable analyst workflows.
- **Inspectable inference.** Semantic relationships such as broader, narrower and related are expanded by axiom-driven inference, and an analyst can see which conclusions were stated and which were inferred.
- **Notes and media** attached to nodes and graphs, so supporting material stays with the knowledge it supports.
- **Shared workspaces (spaces)** with per-space membership and roles, so teams see only what they are assigned to see.

### 3.4 Semantic Integration Layer

HypergraphAI does not replace partner systems. It gives them a common meaning.

- **Model meaning once.** Types, relationships and vocabularies are stored as data in the hypergraph, not hard-coded in each integration.
- **Map many sources to one model.** Feeds from vehicles, sensors, models, databases and other platforms are mapped into hypernodes and hyperedges through REST, MCP or scripted loaders.
- **Keep the whole relationship.** An n-ary hyperedge represents a multi-party relationship (for example an asset, a tasking, a location, a time window and a constraint) as one object with its own attributes.
- **Query across sources.** SHQL queries can span several graphs at once, and federated mesh queries can span several servers.
- **Interoperate with standards.** SKOS-style semantic relationships are supported, and a SPARQL to SHQL translation path is in development for organizations with RDF-based assets.

For Lattice, entity and task data exposed through the open data models can be mirrored or referenced into a semantic graph, enriched with mission context, and queried alongside knowledge from other partners.

### 3.5 Persisted Enterprise and Operational Semantic Knowledge Hypergraphs

Beyond agent memory, HypergraphAI is a system of record for durable semantic knowledge.

| Knowledge type | Examples |
|---|---|
| Operational | Order of battle, capability and readiness models, mission and task structures, standing constraints |
| Enterprise | Organizational structure, program and supply relationships, equipment and configuration knowledge, policy and doctrine vocabularies |
| Lessons and history | After-action findings, decision records and the evidence behind them, retained with time and provenance |

Properties that matter for this role:

- **Temporal:** every change is retained, and any query can be evaluated at a past point in time.
- **Governed:** role-based access control on graphs and spaces, audit of writes, and separation of teams and tenants through spaces.
- **Pluggable storage:** the default backend is MongoDB, behind an abstract storage interface, so other backends can be added without changing the rest of the platform.
- **Scale-aware querying:** aggregation and paging are pushed down to the storage backend so large graphs are queried without loading everything into memory.

## 4. Partnering with Anduril and Other Lattice Partners

The program lists partners across AI and models, autonomous platforms, space, cloud and edge infrastructure, and integrators. The table below shows how HypergraphAI would work with each kind of partner. These are proposed collaboration patterns based on the partner types named on the program page. They are not existing agreements, and no named company has been approached or has endorsed them.

### 4.1 With Anduril

| Area | Proposed integration |
|---|---|
| Lattice SDK | Build a HypergraphAI connector on the Lattice SDK (REST or gRPC; Go, Java, JavaScript or Python bindings) that reads entities and tasks through the open data models and writes them as hypernodes and hyperedges, keeping source identifiers for traceability. |
| Return path | Publish enrichments, classifications and analyst or agent conclusions back to Lattice as entity enrichment, where the program permits. |
| Sandbox and validation | Develop and test against Lattice sandbox environments and representative data, then pursue testing and validation to earn the program's proven-integration credibility. |
| Joint work | Reference demonstrations and joint marketing, using the Lattice Partner badging once eligible. |

### 4.2 With Other Lattice Partners

| Partner type (examples from the program) | What they contribute | What HypergraphAI provides them |
|---|---|---|
| AI and model platforms (for example planning and defense-tuned language models, model operations platforms) | Models, inference and AI-enabled planning | A cross-model, cross-vendor memory so their outputs and inputs persist and are shared, plus a governed knowledge base to ground planning and inference in mission context |
| Autonomous platforms (ground, air, surface, maritime) | Vehicle and payload entities, telemetry, tasking status | A common semantic model for fleet capability, readiness and tasking relationships, and a place for mission history that outlives a single vehicle or sortie |
| Space and sensing data providers | Orbital, RF and geolocation data services | Integration of external data services into the same graph as Lattice entities, with provenance and time, so analysts can fuse and audit them |
| Cloud and edge infrastructure providers | Compute and hosting for disrupted, disconnected, intermittent and low-bandwidth (DDIL) environments | A self-hostable, container-packaged knowledge store that runs at the edge and in the cloud, with mesh federation to reconcile sites |
| Integrators and program builders | Delivery into end-user programs | A reusable semantic layer that they configure instead of building their own memory and knowledge store for each program |

### 4.3 Ecosystem Patterns

- **Shared mission graph.** Partners with different vendors' agents write to one permissioned job graph, so their agents read the same context while each write is attributed to its own account.
- **Model portability.** A mission moves from one model or planner to another without losing accumulated context, because context is stored as data and not as model state.
- **Edge to enterprise sync.** Edge servers keep working through intermittent connectivity, and mesh federation lets separate servers be queried together when connected.
- **Neutral ground.** Because the store is vendor-neutral, it is a common place where competing partners can exchange context under access rules the operator controls.

## 5. Proposed Integration Architecture

```
 Sensors, platforms, C2 and mission systems
                 |
                 v
        Anduril Lattice mesh  (entities, tasks, assets)
                 |
      Lattice SDK connector (partner-built, see 4.1)
                 |
                 v
 +------------------------------------------------------+
 |  HypergraphAI                                        |
 |   - Job graphs (transient) and long-term graphs      |
 |   - Semantic model: types, relations, vocabularies   |
 |   - SHQL, REST, MCP, web UI, shell                   |
 |   - RBAC, spaces, audit, point-in-time history       |
 |   - Mesh federation across servers and sites         |
 +------------------------------------------------------+
        ^                    ^                    ^
        |                    |                    |
 Partner AI agents        Analysts          Partner systems
 (any vendor, via MCP)  (UI, SHQL, shell)   (REST, loaders)
```

### 5.1 Integration Touchpoints

| Direction | Touchpoint | Description |
|---|---|---|
| Lattice to HypergraphAI | Lattice SDK connector | Reads entities and tasks and writes them as hypernodes and hyperedges. |
| HypergraphAI to Lattice | Lattice SDK connector | Publishes conclusions and enrichments back through Lattice interfaces. |
| Agents to HypergraphAI | MCP | 30 tools covering graph, node and edge management, SHQL queries, inference, media, spaces and mesh operations. |
| Analysts to HypergraphAI | Web UI, SHQL, shell | Direct human access to the same knowledge the agents use. |
| Partner systems to HypergraphAI | REST, loaders | Partner data services map their data into the shared graph. |
| Site to site | Mesh federation | Separate servers, such as different sites or enclaves, are registered as a mesh and queried together. |

### 5.2 Deployment

- **Self-hosted and customer-controlled.** Data stays in the customer's own store, which is the intended posture for defense and national security use.
- **Container packaging.** A Docker deployment is provided, and the platform runs on standard Linux hosts.
- **Optional telemetry, off by default.** When enabled, it reports usage and error metadata only, never query text or knowledge content, with account and graph identifiers hashed by default. Every event names its actor, or `__system` when no account acted. It can be kept entirely local, in an admin-only graph inside the deployment, so nothing leaves the enclave.

## 6. Example Scenarios

1. **Multi-vendor agent team.** Agents from different partners share one job graph. One records a sensor-derived observation, another links it to a known asset, a third proposes a tasking. All read the same context, each write is attributed, and the record persists after the mission.
2. **Shift handover.** A new analyst or agent session opens the persisted graph and uses a point-in-time query to see what was believed and decided at the end of the last shift.
3. **Grounding an AI planner.** A partner's planning model queries HypergraphAI for readiness, doctrine and constraint knowledge, and writes its proposed plan and rationale back for analyst review.
4. **Fusing partner data.** A space-derived data service and a vehicle fleet feed are joined in one graph, so a query can ask which assets are in a region of interest and below a readiness threshold.
5. **Auditable machine conclusions.** An analyst reviews an agent-inferred relationship and sees the statements it was derived from and when each was recorded.

## 7. What We Bring and What We Ask

| We bring | We would work with Anduril and partners on |
|---|---|
| A working semantic hypergraph platform with MCP, REST, SHQL, shell and web UI | Lattice SDK interface details and connector design |
| Vendor-neutral agent memory and knowledge store | Access to Lattice sandboxes, representative data and testing and validation |
| Governance controls: RBAC, spaces, audit, point-in-time history | Data-handling, classification and accreditation requirements |
| Self-hosted deployment and a privacy-first optional telemetry design | Joint reference scenarios with interested partners, and joint marketing |

## 8. Status and Scope Notes

Stated plainly so reviewers can calibrate:

- **Product stage.** HypergraphAI is a working platform that is pre-revenue and pre-launch, with no paying customers yet.
- **Assurance.** There are no third-party benchmarks and no SOC 2 or comparable accreditation today. Accreditation for defense environments would be part of a joint plan.
- **Lattice connector.** The connector described here is a proposed integration and is not built. Its design depends on the Lattice SDK and terms the program provides after acceptance.
- **Partner relationships.** Partner types in section 4 come from the public program description. No agreement or discussion with any named company is implied.
- **In development.** SPARQL to SHQL translation is partial and in development.

## 9. Next Steps

1. Apply to the Lattice Developer Experience and obtain SDK and sandbox access.
2. Select one scenario from section 6 for a joint proof of concept.
3. Build and validate the Lattice SDK connector against sandbox data.
4. Identify one or two interested Lattice partners for a shared-memory demonstration.
5. Agree on deployment, security and data-handling constraints for a demonstration.
