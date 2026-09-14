# HypergraphAI User Fundamentals

**Self-Paced Training Course**

---

## Overview

Welcome to HypergraphAI (hgAI) — a semantic hypergraph knowledge platform that lets you model complex, multi-way relationships between entities. Unlike traditional graphs where an edge connects exactly two nodes, hyperedges in hgAI can connect *any number* of nodes simultaneously, letting you represent rich real-world relationships faithfully and query them with precision.

This course walks you through the fundamentals using a fun, familiar use case: **The Three Stooges** comedy group. By the end you will have hands-on experience creating hypergraphs, hypernodes, hyperedges, and writing SHQL queries.

**Prerequisites:** You have a running hgAI server and have already signed into the web application in your browser.

**Estimated time:** 60–90 minutes

---

## Table of Contents

1. [Navigating the UI](#1-navigating-the-ui)
2. [Core Concepts](#2-core-concepts)
3. [Hypergraphs](#3-hypergraphs)
4. [Hypernodes](#4-hypernodes)
5. [Hyperedges](#5-hyperedges)
6. [Queries — SHQL](#6-queries--shql-semantic-hypergraph-query-language)
7. [Reference Summary](#7-reference-summary)

---

## 1. Navigating the UI

When you sign in, you land on the **Dashboard** — a summary view showing your server's total hypergraph, hypernode, and hyperedge counts alongside a list of active hypergraphs.

### Sidebar Navigation

The left sidebar is your primary navigation. Sections are divided into **Knowledge** (available to all users) and **Administration** (admin-only).

| Sidebar Item | Icon | Purpose |
|---|---|---|
| Dashboard | Grid | Summary statistics and server info |
| Hypergraphs | Diagram | Create and manage hypergraphs |
| Hypernodes | Circle | Browse and manage nodes |
| Hyperedges | Share | Browse and manage edges |
| Query (SHQL) | Braces | Write and run SHQL queries |
| Spaces *(admin)* | Collection | Multi-tenant space management |
| Accounts *(admin)* | People | User account management |
| Meshes *(admin)* | Network | Distributed server federation |
| System *(admin)* | Gear | Server config, cache, API explorer |

> **Tip:** Click the hamburger button (`≡`) in the top bar to collapse or expand the sidebar, giving more room for the query editor.

### Active Graph Selector

The top bar contains an **Active Graph** dropdown. Selecting a graph here sets the default context for the Hypernodes and Hyperedges screens, so you do not need to pick the graph each time you browse.

### Screens

Every main section opens in its own screen area. Clicking a sidebar link switches the visible screen — no page reload occurs since hgAI is a single-page application.

---

## 2. Core Concepts

Before you start creating data, it helps to understand the building blocks.

### Hypergraph

A **hypergraph** is a named container — think of it as a database or namespace. All hypernodes and hyperedges belong to exactly one hypergraph. You can query across multiple hypergraphs simultaneously.

**Real-world analogies:**
- A hypergraph for "company-org-chart" containing employees, departments, and reporting relationships
- A hypergraph for "movie-database" containing films, actors, directors, and roles
- A hypergraph for "medical-records" containing patients, diagnoses, treatments, and providers

### Hypernode

A **hypernode** is an entity — a noun in your knowledge model. Every hypernode has a **type** that classifies it (e.g., `Person`, `Organization`, `Concept`, `Event`, `Place`, `Group`). A node's flexible `attributes` field holds any additional structured data as a JSON document.

**Real-world analogies:**
- A `Person` node for an employee with attributes `{ "department": "Engineering", "start_date": "2021-03-01" }`
- A `Concept` node for a product category with attributes `{ "code": "ELEC-42", "taxable": true }`
- An `Event` node for a conference with attributes `{ "venue": "Chicago", "capacity": 3000 }`

### Hyperedge

A **hyperedge** is a relationship that connects *n* hypernodes at once. This is what makes hypergraphs more expressive than ordinary graphs. One edge can represent "Person A, Person B, and Person C are all members of Group G" without creating multiple pairwise edges.

Every hyperedge has:
- **relation** — a semantic label for what the relationship means (e.g., `has-member`, `sibling`, `broader`)
- **flavor** — the structural pattern of the relationship (see [Edge Flavors](#edge-flavors))
- **members** — the ordered list of hypernodes participating in the edge
- **valid_from / valid_to** — optional timestamps that scope the relationship to a time window, enabling **point-in-time queries**

**Real-world analogies:**
- A `hub` edge with relation `has-member` connecting a `Team` node to all its current employees
- A `symmetric` edge with relation `sibling` connecting three `Person` nodes who share a parent
- A 2-member `hub` edge with relation `reports-to` — first member (`seq: 0`) reports to the second — is how a directed fact like "employee reports to manager" is modeled

### Edge Flavors

Only two flavors exist — deliberately, each describes a genuine N-ary fact
that can't be decomposed into independent binary facts without losing what
it asserts:

| Flavor | Pattern | Example Use Case |
|---|---|---|
| `hub` | First member (`seq: 0`) is the hub; every other member is an independent (hub, spoke) fact | Group membership, project team — and, with exactly 2 members, any directed fact: reports-to, mentorship |
| `symmetric` | Every member is mutually equivalent to every other | Siblings, co-authors, collaborators |

A directed *chain* (A reports to B, B reports to C, ...) is not one N-ary
fact — it's several independent 2-member `hub` edges. Reasoning across such
a chain ("is A transitively under C?") is a relation-level property,
declared via an `owl:transitive` axiom hyperedge and enabled per query with
`infer: true` (see Module 6's inferencing note) — not a per-edge flavor.

### Time-Scoped Relationships

One of hgAI's most powerful features is **bitemporal (point-in-time) querying**. When you set `valid_from` and `valid_to` on a hyperedge, you record *when* that relationship was true in the real world. You can then query the graph with an `at` timestamp to retrieve only the relationships that were valid at that specific moment — perfect for modeling organizational histories, legislative changes, or evolving group memberships.

---

## 3. Hypergraphs

### What You'll Learn

- How to create a hypergraph
- Key fields and their meaning
- How hypergraph IDs are used in queries

### Field Reference

| Field | Required | Notes |
|---|---|---|
| ID | Yes | Unique identifier; no dots allowed. Use hyphens or underscores. |
| Label | Yes | Human-readable display name |
| Type | No | `instantiated` (physical, default) or `logical` (virtual composition) |
| Space | No | Assign to a tenant space (if spaces are configured) |
| Description | No | Free-text description |
| Tags | No | Comma-separated searchable tags |
| Attributes | No | JSON document for custom metadata |

> **ID naming convention:** Use lowercase kebab-case: `company-org-2024`, `product-catalog`, `hg-fun-a`. Dots are reserved for mesh federation notation.

### Creating a Hypergraph — Step by Step

1. Click **Hypergraphs** in the left sidebar.
2. Click the **New Hypergraph** button (top right of the screen).
3. A modal dialog appears. Fill in the fields.
4. Click **Save Hypergraph**.

The new hypergraph appears in the table with 0 nodes and 0 edges.

---

### Task 3.1 — Create `hg-fun-a`

Create your first hypergraph using these values:

| Field | Value |
|---|---|
| ID | `hg-fun-a` |
| Label | `Three Stooges — People` |
| Type | `instantiated` |
| Description | `Person nodes for the Three Stooges training exercise` |
| Tags | `training, fun` |

Click **Save Hypergraph**. You should see `hg-fun-a` appear in the hypergraph list.

---

### Task 3.2 — Create `hg-fun-b`

Create a second hypergraph:

| Field | Value |
|---|---|
| ID | `hg-fun-b` |
| Label | `Three Stooges — Group & Memberships` |
| Type | `instantiated` |
| Description | `Group node and membership hyperedges for the Three Stooges training exercise` |
| Tags | `training, fun` |

Click **Save Hypergraph**. Both `hg-fun-a` and `hg-fun-b` should now appear in the list.

---

### Other Hypergraph Examples

To illustrate that hypergraphs are simply containers, here are examples from other domains:

```
hg-id: "biomedical-ontology"
label: "Biomedical Ontology Graph"
description: "Gene-disease-drug relationships for research"
tags: ["biomedical", "ontology", "research"]

hg-id: "supply-chain-q1-2025"
label: "Supply Chain Q1 2025"
description: "Supplier, product, and logistics relationships"
tags: ["supply-chain", "2025", "logistics"]

hg-id: "us-congress-119th"
label: "119th US Congress"
description: "Legislators, committees, and bill co-sponsorships"
tags: ["government", "congress", "legislation"]
```

---

## 4. Hypernodes

### What You'll Learn

- How to create hypernodes
- How to set the `type` and `attributes` fields
- How `valid_from` / `valid_to` scopes a node's existence in time

### Field Reference

| Field | Required | Notes |
|---|---|---|
| Hypergraph | Yes | Select from dropdown; the graph that owns this node |
| ID | Yes | Unique within the hypergraph. Use a readable slug: `person:moe` |
| Label | Yes | Human-readable display name |
| Type | No | Entity type string. Common values: `Person`, `Organization`, `Group`, `Concept`, `Event`, `Place` |
| Status | No | `active` (default), `draft`, or `archived` |
| Valid From | No | Datetime when this entity became real-world valid |
| Valid To | No | Datetime when this entity ceased to be valid (leave blank = still valid) |
| Description | No | Free-text description |
| Tags | No | Comma-separated tags |
| Attributes | No | JSON document with any additional structured fields |

> **ID convention:** Prefixing with a type hint makes IDs self-documenting and avoids collisions: `person:moe`, `org:acme`, `concept:machine-learning`, `event:conference-2024`.

### Creating a Hypernode — Step by Step

1. Click **Hypernodes** in the left sidebar.
2. Select the target hypergraph from the **filter bar** at the top of the screen, or click **New Hypernode** and choose the graph in the modal.
3. Click **New Hypernode**.
4. Fill in the fields. Pay attention to:
   - **Hypergraph** — make sure the correct graph is selected
   - **Attributes** — enter valid JSON, e.g. `{"first_name": "Moe", "last_name": "Howard"}`
5. Click **Save Hypernode**.

---

### Task 4.1 — Create Six Person Nodes in `hg-fun-a`

You will create six `Person` hypernodes — one for each member who appeared in The Three Stooges over the group's history. All go in the **`hg-fun-a`** hypergraph.

Navigate to **Hypernodes**, then click **New Hypernode** for each entry below.

---

**Node 1 — Moe Howard**

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-a` |
| ID | `person:moe` |
| Label | `Moe Howard` |
| Type | `Person` |
| Status | `active` |
| Attributes | `{"first_name": "Moe", "last_name": "Howard"}` |

---

**Node 2 — Larry Fine**

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-a` |
| ID | `person:larry` |
| Label | `Larry Fine` |
| Type | `Person` |
| Status | `active` |
| Attributes | `{"first_name": "Larry", "last_name": "Fine"}` |

---

**Node 3 — Shemp Howard**

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-a` |
| ID | `person:shemp` |
| Label | `Shemp Howard` |
| Type | `Person` |
| Status | `active` |
| Attributes | `{"first_name": "Shemp", "last_name": "Howard"}` |

---

**Node 4 — Curly Howard**

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-a` |
| ID | `person:curly` |
| Label | `Curly Howard` |
| Type | `Person` |
| Status | `active` |
| Attributes | `{"first_name": "Curly", "last_name": "Howard"}` |

---

**Node 5 — Joe Besser**

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-a` |
| ID | `person:curly-joe` |
| Label | `Joe Besser` |
| Type | `Person` |
| Status | `active` |
| Attributes | `{"first_name": "Curly Joe", "last_name": "Besser"}` |

---

**Node 6 — Joe DeRita**

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-a` |
| ID | `person:derita` |
| Label | `Joe DeRita` |
| Type | `Person` |
| Status | `active` |
| Attributes | `{"first_name": "Joe", "last_name": "DeRita"}` |

---

**Verify:** After saving all six nodes, go to the **Hypernodes** screen, select `hg-fun-a` in the graph filter, and confirm all six nodes appear in the table.

---

### Task 4.2 — Create the Group Node in `hg-fun-b`

Now create the group entity that represents The Three Stooges as a collective. This goes in the **`hg-fun-b`** hypergraph.

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-b` |
| ID | `group:three-stooges` |
| Label | `The Three Stooges` |
| Type | `Group` |
| Status | `active` |
| Description | `American vaudeville and comedy act active 1922–1970` |
| Tags | `comedy, vaudeville, film` |
| Attributes | `{"founded": "1922", "origin": "USA", "genre": "slapstick"}` |

---

### Hypernode Examples from Other Domains

**Person node (biomedical researcher):**
```json
{
  "id": "person:marie-curie",
  "label": "Marie Curie",
  "type": "Person",
  "attributes": {
    "first_name": "Marie",
    "last_name": "Curie",
    "nationality": "Polish-French",
    "field": "Physics and Chemistry"
  }
}
```

**Organization node (company):**
```json
{
  "id": "org:acme-corp",
  "label": "ACME Corporation",
  "type": "Organization",
  "attributes": {
    "industry": "Manufacturing",
    "headquarters": "Phoenix, AZ",
    "founded": 1947,
    "employees": 12000
  }
}
```

**Concept node (knowledge graph):**
```json
{
  "id": "concept:machine-learning",
  "label": "Machine Learning",
  "type": "Concept",
  "attributes": {
    "domain": "Computer Science",
    "subfield_of": "Artificial Intelligence",
    "key_techniques": ["supervised", "unsupervised", "reinforcement"]
  }
}
```

**Event node (time-scoped):**
```json
{
  "id": "event:apollo-11",
  "label": "Apollo 11 Moon Landing",
  "type": "Event",
  "valid_from": "1969-07-16T13:32:00Z",
  "valid_to": "1969-07-24T16:51:00Z",
  "attributes": {
    "mission": "Apollo 11",
    "crew": ["Armstrong", "Aldrin", "Collins"],
    "outcome": "First crewed lunar landing"
  }
}
```

---

## 5. Hyperedges

### What You'll Learn

- How to create hyperedges
- How to add multiple members to a single edge
- How `valid_from` / `valid_to` enables point-in-time queries
- How the `hub` flavor works for group membership

### Field Reference

| Field | Required | Notes |
|---|---|---|
| Hypergraph | Yes | The graph that owns this edge |
| ID | No | Auto-generated if left blank (recommended for most use cases) |
| Relation | Yes | Semantic label: `has-member`, `sibling`, `broader`, `reports-to`, etc. |
| Flavor | Yes | `hub` or `symmetric` |
| Label | No | Human-readable label for this specific edge instance |
| Status | No | `active`, `draft`, or `archived` |
| Valid From | No | When this relationship became valid |
| Valid To | No | When this relationship ended (blank = still valid) |
| Tags | No | Comma-separated tags |
| Members | Yes | Use the Members builder to add hypernode IDs in order |
| Attributes | No | JSON document with edge-level metadata |

### The Members Builder

The **Members** section in the edge modal has an **Add Member** button. Each time you click it, a new row appears with fields for:
- **Node ID** — type the hypernode ID (e.g., `group:three-stooges`)
- **Role** — optional semantic role label for this member's position (e.g., `hub`, `member`)
- **Seq** — sequence position; member[0] is the hub in a `hub` edge

> **Hub edge convention:** For a `hub` flavor edge, member at position 0 (seq 0) is the **hub node** — the central entity that "owns" the relationship. All subsequent members (seq 1, 2, 3 …) are the spokes.

### Creating a Hyperedge — Step by Step

1. Click **Hyperedges** in the left sidebar.
2. Click **New Hyperedge**.
3. Select the **Hypergraph**.
4. Enter the **Relation** (e.g., `rel:member`).
5. Select the **Flavor** (`hub`).
6. Set **Valid From** and **Valid To** if the relationship is time-scoped.
7. Click **Add Member** for each participating node, entering the node ID in order.
8. Click **Save Hyperedge**.

---

### Task 5.1 — Create Five Membership Hyperedges in `hg-fun-b`

The Three Stooges had different lineups over the decades. You will create five time-scoped `hub` hyperedges — one for each lineup era — all in the **`hg-fun-b`** hypergraph. Each edge uses:
- **Relation:** `rel:member`
- **Flavor:** `hub`
- **member[0]:** `group:three-stooges` (the hub)

> **Important:** The `group:three-stooges` node was created in `hg-fun-b` (Task 4.2). The `person:*` nodes live in `hg-fun-a`. In hgAI, hyperedge members can reference node IDs across hypergraphs when querying with multi-graph `from` clauses. For simplicity in this exercise, enter the node IDs exactly as shown.

---

**Edge 1 — Original Lineup (1922–1932): Moe, Shemp, Larry**

This is the earliest Three Stooges era when Shemp was the third stooge before his brother Curly joined.

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-b` |
| Relation | `rel:member` |
| Flavor | `hub` |
| Label | `Three Stooges — Moe, Shemp, Larry (1922–1932)` |
| Valid From | `1922-01-01T00:01:00` |
| Valid To | `1932-07-04T23:59:00` |
| Tags | `lineup-1, original` |

**Members (in order):**

| Seq | Node ID | Role |
|---|---|---|
| 0 | `group:three-stooges` | `hub` |
| 1 | `person:moe` | `member` |
| 2 | `person:shemp` | `member` |
| 3 | `person:larry` | `member` |

---

**Edge 2 — Classic Lineup (1932–1946): Moe, Curly, Larry**

Curly Howard (Moe's younger brother) replaced Shemp and became the most famous Stooge of the classic era.

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-b` |
| Relation | `rel:member` |
| Flavor | `hub` |
| Label | `Three Stooges — Moe, Curly, Larry (1932–1946)` |
| Valid From | `1932-07-05T00:01:00` |
| Valid To | `1946-07-04T23:59:00` |
| Tags | `lineup-2, classic` |

**Members (in order):**

| Seq | Node ID | Role |
|---|---|---|
| 0 | `group:three-stooges` | `hub` |
| 1 | `person:moe` | `member` |
| 2 | `person:curly` | `member` |
| 3 | `person:larry` | `member` |

---

**Edge 3 — Shemp Returns (1946–1956): Moe, Shemp, Larry**

After Curly suffered a stroke, Shemp returned to the act.

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-b` |
| Relation | `rel:member` |
| Flavor | `hub` |
| Label | `Three Stooges — Moe, Shemp, Larry (1946–1956)` |
| Valid From | `1946-07-05T00:01:00` |
| Valid To | `1956-07-04T23:59:00` |
| Tags | `lineup-3, shemp-returns` |

**Members (in order):**

| Seq | Node ID | Role |
|---|---|---|
| 0 | `group:three-stooges` | `hub` |
| 1 | `person:moe` | `member` |
| 2 | `person:shemp` | `member` |
| 3 | `person:larry` | `member` |

---

**Edge 4 — Joe Besser Era (1956–1958): Moe, Joe Besser, Shemp**

After Shemp's death, Joe Besser joined for a brief stint.

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-b` |
| Relation | `rel:member` |
| Flavor | `hub` |
| Label | `Three Stooges — Moe, Shemp, Joe Besser (1956–1958)` |
| Valid From | `1956-07-05T00:01:00` |
| Valid To | `1958-07-04T23:59:00` |
| Tags | `lineup-4, joe-besser` |

**Members (in order):**

| Seq | Node ID | Role |
|---|---|---|
| 0 | `group:three-stooges` | `hub` |
| 1 | `person:moe` | `member` |
| 2 | `person:shemp` | `member` |
| 3 | `person:curly-joe` | `member` |

---

**Edge 5 — Curly-Joe DeRita Era (1958–1970): Moe, Joe DeRita, Larry**

Joe DeRita (nicknamed "Curly-Joe") joined for the final era, including the popular cartoon series.

| Field | Value |
|---|---|
| Hypergraph | `hg-fun-b` |
| Relation | `rel:member` |
| Flavor | `hub` |
| Label | `Three Stooges — Moe, Joe DeRita, Larry (1958–1970)` |
| Valid From | `1958-07-05T00:01:00` |
| Valid To | `1970-12-31T23:59:00` |
| Tags | `lineup-5, derita` |

**Members (in order):**

| Seq | Node ID | Role |
|---|---|---|
| 0 | `group:three-stooges` | `hub` |
| 1 | `person:moe` | `member` |
| 2 | `person:derita` | `member` |
| 3 | `person:larry` | `member` |

---

**Verify:** Go to the **Hyperedges** screen, select `hg-fun-b`, and confirm all five edges appear. Filter by **Relation** `rel:member` to narrow the list.

---

### Hyperedge Examples from Other Domains

**Hub — Project Team (organization):**
```yaml
relation: has-member
flavor: hub
members:
  - node_id: "project:apollo-ai"
    role: hub
  - node_id: "person:alice"
    role: member
  - node_id: "person:bob"
    role: member
  - node_id: "person:carol"
    role: member
valid_from: "2024-01-15T00:00:00Z"
attributes:
  team_size: 3
  budget_usd: 500000
```

**Symmetric — Sibling Relationship (genealogy):**
```yaml
relation: sibling
flavor: symmetric
members:
  - node_id: "person:moe"
    role: sibling
  - node_id: "person:shemp"
    role: sibling
  - node_id: "person:curly"
    role: sibling
attributes:
  family: "Howard"
```

**Hub, 2-member — Reporting Relationship (HR):**
```yaml
relation: reports-to
flavor: hub
members:
  - node_id: "person:alice"
    seq: 0
    role: report
  - node_id: "person:carol"
    seq: 1
    role: manager
valid_from: "2023-06-01T00:00:00Z"
```
A 2-member `hub` edge is how any simple directed fact is modeled — the
first member (`seq: 0`) is the hub, the second is its one spoke.

**Hub, 2-member — Taxonomy (knowledge graph):**
```yaml
relation: is-a
flavor: hub
members:
  - node_id: "concept:golden-retriever"
    seq: 0
  - node_id: "concept:dog"
    seq: 1
```
To make chains of `is-a` facts transitively reachable ("is a golden
retriever an animal?", several hops up the hierarchy), declare
`owl:transitive` on the `is-a` relation as a separate axiom hyperedge — see
Module 6's inferencing note. That's a property of the *relation*, not a
per-edge flavor.

---

## 6. Queries — SHQL (Semantic Hypergraph Query Language)

### What is SHQL?

SHQL (Semantic Hypergraph Query Language) is a SPARQL-inspired, **pattern-matching** query language — HypergraphAI's query language. It's equally comfortable doing direct attribute filtering (one pattern, no joins — Tasks 6.1–6.4) and **graph traversal** — binding variables to nodes and edges, following relationships across the graph, and composing multi-step join patterns in a single query.

Key SHQL concepts:
- **Variables** start with `?` (e.g., `?person`, `?edge`, `?group`)
- A **node pattern** (`- node: ?var`) matches hypernodes and binds results to the variable
- An **edge pattern** (`- edge: ?var`) matches hyperedges and binds results to the variable
- A **filter expression** (`- filter: ...`) applies boolean logic to already-bound variables
- Variables bound in one pattern can be referenced in subsequent patterns — this is how **joins** work
- The `select` clause controls which variable fields appear in the output

### Running an SHQL Query

1. Click **Query (SHQL)** in the left sidebar.
2. Enter your SHQL query in the YAML editor on the left.
3. Click **Run Query**. Results appear on the right as JSON.
4. Use **Validate** to check syntax, **Examples** for sample queries.

### SHQL Structure

```yaml
shql:
  from: <graph-id>               # required: graph ID or list [id1, id2]
  at: <ISO-8601-datetime>        # optional: point-in-time filter
  where:                          # list of patterns (evaluated in order)
    - node: ?var                  # node pattern
      id: <literal-id>            # optional: match specific node ID
      node_type: <type>           # optional: filter by type
      attributes:                 # optional: filter by attribute values
        <field>: <value>
    - edge: ?edge_var             # edge pattern
      relation: <relation>
      flavor: <flavor>
      members:
        - node_id: ?var           # reference a bound variable
        - node_id: <literal-id>   # anchor to a literal node ID
    - filter: <expression>        # boolean filter expression
    - optional: [...]             # left-outer-join (include results even if pattern fails)
    - union:                       # set union of alternative branches
        - [branch-1-patterns]
        - [branch-2-patterns]
  select:                         # output projection
    - ?var.id
    - ?var.label
    - ?var.attributes
    - ?var.attributes.first_name  # nested attribute access
  distinct: false                 # optional: deduplicate
  limit: 500                      # optional: max results
  offset: 0                       # optional: pagination
  order_by: ?var.label            # optional: sort key(s) — a single field, or a list for
                                   # multi-key sort (primary first); each may carry a trailing
                                   # " asc"/" desc" (default asc), e.g. "?var.label desc"
  infer: true                     # optional: opt-in axiom-driven inferencing (see below)
  aggregate:                      # optional: computed over the full matched result, pre-pagination
    count: true
    group_by: <projected-row-key>
```

### Filter Functions

| Function | Syntax | Description |
|---|---|---|
| CONTAINS | `?var.label CONTAINS "text"` | Substring match |
| STARTS_WITH | `STARTS_WITH(?var.label, "prefix")` | Prefix match |
| ENDS_WITH | `ENDS_WITH(?var.label, "suffix")` | Suffix match |
| MATCHES | `MATCHES(?var.attributes.name, "regex")` | Regex match |
| BOUND | `BOUND(?var)` | True if variable was bound |
| IS_TYPE | `IS_TYPE(?var, "TypeName")` | True if node type matches |

Comparison operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `IN`

Boolean operators: `AND`, `OR`, `NOT`

---

### 6.1 Simple Queries — Return All Nodes

---

#### Task 6.1.1 — SHQL: All Nodes in `hg-fun-a`

**Your task:** Write an SHQL query that returns all hypernodes in `hg-fun-a`.

<details>
<summary>Answer — Click to reveal</summary>

```yaml
shql:
  from: hg-fun-a
  where:
    - node: ?n
  select:
    - ?n.id
    - ?n.label
    - ?n.type
    - ?n.attributes
```

**Expected result:** All six `Person` nodes.

> **Note:** The `- node: ?n` pattern without any constraints matches *every* hypernode in the graph and binds each to the variable `?n`. The `select` clause then projects specific fields.

</details>

---

#### Task 6.1.2 — SHQL: All Nodes in `hg-fun-b`

**Your task:** Write an SHQL query that returns all hypernodes in `hg-fun-b`.

<details>
<summary>Answer — Click to reveal</summary>

```yaml
shql:
  from: hg-fun-b
  where:
    - node: ?n
  select:
    - ?n.id
    - ?n.label
    - ?n.type
    - ?n.attributes
```

**Expected result:** One `Group` node (`group:three-stooges`).

</details>

---

#### Task 6.1.3 — SHQL: All Nodes in Both `hg-fun-a` and `hg-fun-b`

**Your task:** Write an SHQL query that returns all hypernodes across both hypergraphs.

<details>
<summary>Answer — Click to reveal</summary>

```yaml
shql:
  from:
    - hg-fun-a
    - hg-fun-b
  where:
    - node: ?n
  select:
    - ?n.id
    - ?n.label
    - ?n.type
    - ?n.attributes
```

**Expected result:** All seven nodes — six `Person` nodes plus the `Group` node.

</details>

---

### 6.2 Matching Exact Values

---

#### Task 6.2.1 — SHQL: Filter by Exact Attribute Value

**Your task:** Write an SHQL query that returns only the `Person` nodes where `last_name` is exactly `Howard`.

<details>
<summary>Answer — Click to reveal</summary>

```yaml
shql:
  from: hg-fun-a
  where:
    - node: ?person
      node_type: Person
      attributes:
        last_name: Howard
  select:
    - ?person.id
    - ?person.label
    - ?person.attributes
```

**Expected result:** Moe Howard, Shemp Howard, Curly Howard.

> **Note:** In SHQL, exact attribute matching goes inside the `attributes:` block of a node pattern, expressed as a node pattern constraint rather than a flat `where:` clause.

</details>

---

### 6.3 Matching Partial Values (Wildcard/Prefix)

---

#### Task 6.3.1 — SHQL: Filter by Prefix Using STARTS_WITH

**Your task:** Write an SHQL query that returns only the `Person` nodes whose `first_name` starts with `Cur`.

<details>
<summary>Answer — Click to reveal</summary>

```yaml
shql:
  from: hg-fun-a
  where:
    - node: ?person
      node_type: Person
    - filter: STARTS_WITH(?person.attributes.first_name, "Cur")
  select:
    - ?person.id
    - ?person.label
    - ?person.attributes.first_name
    - ?person.attributes.last_name
```

**Expected result:** Curly Howard and Joe Besser (whose `first_name` is `Curly Joe`).

> **Pattern:** A node pattern binds `?person` to all `Person` nodes, then the `filter` pattern restricts the bound set using the `STARTS_WITH` function. Filters are always applied *after* the preceding pattern.

</details>

---

### 6.4 Matching with Regular Expressions

---

#### Task 6.4.1 — SHQL: Filter by Regex Using MATCHES

**Your task:** Write an SHQL query that returns only the `Person` nodes whose `first_name` matches `.*oe.*` (contains `oe`).

<details>
<summary>Answer — Click to reveal</summary>

```yaml
shql:
  from: hg-fun-a
  where:
    - node: ?person
      node_type: Person
    - filter: MATCHES(?person.attributes.first_name, ".*oe.*")
  select:
    - ?person.id
    - ?person.label
    - ?person.attributes.first_name
```

**Expected result:** Moe Howard (`first_name: Moe`) and Joe DeRita (`first_name: Joe`).

</details>

---

### 6.5 List Group Members

---

#### Task 6.5.1 — SHQL: All Membership Edges for `group:three-stooges`

**Your task:** Write an SHQL query that returns all `rel:member` / `hub` edges that include `group:three-stooges` as a member.

<details>
<summary>Answer — Click to reveal</summary>

```yaml
shql:
  from: hg-fun-b
  where:
    - edge: ?edge
      relation: rel:member
      flavor: hub
      members:
        - node_id: group:three-stooges
  select:
    - ?edge.id
    - ?edge.relation
    - ?edge.members
    - ?edge.valid_from
    - ?edge.valid_to
    - ?edge.tags
```

**Expected result:** All five membership edges.

> **Pattern:** When you include a literal node ID in the `members:` list of an edge pattern, SHQL anchors the match — only edges that include `group:three-stooges` as one of their members are returned.

</details>

---

### 6.6 List Group Members at Point-in-Time

---

#### Task 6.6.1 — SHQL: Who Were the Stooges on January 1, 1924?

**Your task:** Write an SHQL query that returns the membership edge(s) for `group:three-stooges` valid at `1924-01-01T12:12:12Z`.

<details>
<summary>Answer — Click to reveal</summary>

```yaml
shql:
  from: hg-fun-b
  at: "1924-01-01T12:12:12Z"
  where:
    - edge: ?edge
      relation: rel:member
      flavor: hub
      members:
        - node_id: group:three-stooges
  select:
    - ?edge.id
    - ?edge.relation
    - ?edge.members
    - ?edge.valid_from
    - ?edge.valid_to
```

**Expected result:** One edge — the original lineup (1922–1932) with Moe, Shemp, and Larry.

> **The `at` clause applies to all patterns in the query.** Any hypernode or hyperedge with `valid_from`/`valid_to` set will be automatically time-filtered.

</details>

---

### Advanced SHQL: Variable Binding and Graph Traversal

One of SHQL's most powerful features is **multi-pattern graph traversal** — binding a variable in one pattern and using it as an anchor in a subsequent pattern. This enables join-like behavior across nodes and edges.

**Example: Find all person nodes who are members of `group:three-stooges` in 1940**

```yaml
shql:
  from:
    - hg-fun-a
    - hg-fun-b
  at: "1940-01-01T00:00:00Z"
  where:
    - edge: ?edge
      relation: rel:member
      flavor: hub
      members:
        - node_id: group:three-stooges
        - node_id: ?person_id
    - node: ?person
      id: ?person_id
      node_type: Person
  select:
    - ?person.id
    - ?person.label
    - ?person.attributes.first_name
    - ?person.attributes.last_name
```

**How this works:**
1. The edge pattern finds all `rel:member` edges containing `group:three-stooges` (filtered to 1940)
2. `?person_id` is bound to each *other* member node ID in those edges
3. The node pattern uses `id: ?person_id` to fetch the full node document for each bound ID
4. The `select` clause projects the person's attributes

**Expected result at 1940:** Moe Howard, Curly Howard, Larry Fine (the classic lineup).

---

**Example: Optional pattern — list all Stooges and their last_name if available**

```yaml
shql:
  from: hg-fun-a
  where:
    - node: ?person
      node_type: Person
    - optional:
        - node: ?person
          attributes:
            last_name: Howard
  select:
    - ?person.id
    - ?person.label
    - ?person.attributes
```

> **Optional patterns** are left-outer-joins. All `Person` nodes are returned, and the optional block adds extra filtering only when the condition matches. Nodes that don't match the optional block are still included in the results.

---

**Example: Union — find all nodes that are either a Person or a Group**

```yaml
shql:
  from:
    - hg-fun-a
    - hg-fun-b
  where:
    - union:
        - - node: ?entity
            node_type: Person
        - - node: ?entity
            node_type: Group
  select:
    - ?entity.id
    - ?entity.label
    - ?entity.type
```

---

### 6.7 Inferencing — Deriving Facts You Never Stored

Relation semantics (which relations are transitive, symmetric, each other's
inverse, or broader/narrower) are never hardcoded — they're declared as
ordinary **axiom hyperedges** asserting a control-vocabulary relation
(`owl:transitive`, `owl:symmetric`, `owl:inverse-of`,
`skos:broaderTransitive`/`narrowerTransitive`) between two `RelationType`
hypernodes. Add `infer: true` to a query, and the engine synthesizes
derived facts live from whatever axioms exist — nothing inferred is ever
persisted, and every inferred result is tagged `_inferred: true`.

**Example:** if an axiom hyperedge asserts `owl:inverse-of [rel:member, rel:member-of]`, this query returns both the literal `rel:member` edges *and* a synthesized `rel:member-of` edge for each one — and, since the literal search itself is relation-agnostic under `infer: true`, querying `relation: rel:member-of` directly instead would return the same synthesized edges without needing to know that `rel:member` is the asserted side:

```yaml
shql:
  from: hg-fun-b
  infer: true
  where:
    - edge:
        bind: ?e
        relation: rel:member
  select:
    - ?e.relation
    - ?e.members
    - ?e._inferred
    - ?e._source_edge
    - ?e._axiom
```

> **Note:** without a matching axiom hyperedge in the graph, `infer: true` has no effect — it never invents semantics that weren't declared as data. See the [README's Inferencing section](../../README.md#inferencing) for the full axiom vocabulary and mechanics.

---

## 7. Reference Summary

### Key Concepts Cheat Sheet

| Term | Description |
|---|---|
| Hypergraph | Named container for nodes and edges |
| Hypernode | An entity (noun) with a type and JSON attributes |
| Hyperedge | A relationship connecting *n* nodes simultaneously |
| Relation | Semantic label on an edge (`has-member`, `sibling`, etc.) |
| Flavor | Structural pattern: `hub` (first member is the hub) or `symmetric` (all members equivalent) — only two exist |
| `valid_from` / `valid_to` | Time window during which a node or edge is real-world valid |
| `at` | Point-in-time filter applied to the entire query |
| `from` | Specifies which hypergraph(s) to query |
| `node:` / `edge:` | Pattern that binds matching entities to a variable |
| `filter:` | Boolean expression applied to bound variables |
| `?variable` | Named binding; can be referenced in subsequent patterns — the same variable in two patterns is an implicit join |
| `select` | Output projection of variable fields |
| `infer: true` | Opt-in axiom-driven inferencing (inverse-of, symmetric, SKOS broader/narrower, transitive closure) — see [7.7](#67-inferencing--deriving-facts-you-never-stored) |
| `aggregate` | `count`/`group_by`, computed over the full matched result before pagination |

---

### Date/Time Format

All timestamps in hgAI use **ISO 8601** format:

```
YYYY-MM-DDTHH:MM:SSZ       UTC (recommended)
YYYY-MM-DDTHH:MM:SS+HH:MM  With timezone offset
YYYY-MM-DDTHH:MM:SS        Local (avoid in production)
```

Examples:
- `1924-01-01T12:12:12Z`
- `1932-07-05T00:01:00Z`
- `1970-12-31T23:59:00Z`

---

### Multi-Graph `from` Syntax

```yaml
# Single graph
from: hg-fun-a

# Multiple graphs (YAML list)
from:
  - hg-fun-a
  - hg-fun-b

# Space-scoped graph (space-id/graph-id)
from: my-space/my-graph

# Multiple space-scoped graphs
from:
  - space-a/graph-1
  - space-b/graph-2
  - global-graph          # unowned graph (no space prefix)
```

---

### Congratulations!

You have completed the hgAI User Fundamentals course. You can now:

- Create and manage **hypergraphs** as named containers for your knowledge
- Create **hypernodes** with typed entities and flexible JSON attributes
- Create **hyperedges** with multi-node membership, semantic relations, and time-scoped validity
- Write **SHQL** queries — from simple attribute filters and aggregation to pattern-based graph traversal and variable binding
- Use **point-in-time** (`at`) filtering to query historical states of your knowledge graph
- Use **axiom-driven inferencing** (`infer: true`) to derive facts that were never explicitly stored

**Next steps to explore:**
- The **API Explorer** (System → Swagger UI) to call hgAI programmatically
- **Logical hypergraphs** — create a graph that composes `hg-fun-a` and `hg-fun-b` into a unified view
- **Spaces** — organize hypergraphs into tenant namespaces with role-based access control
- **MCP integration** — connect hgAI to AI agents via the Model Context Protocol server
