---
title: "HypergraphAI — Live Demo: Acme Robotics Engineering Org"
description: "Step-by-step walkthrough of HypergraphAI's core features, from a clean install to point-in-time queries and AI-agent access"
---

# HypergraphAI
## Live Demo — "Acme Robotics" Engineering Org

A self-contained, hands-on tour of hypergraphs, HQL, SHQL, temporal queries,
and AI-native access — starting from a **clean HypergraphAI install with zero
demo artifacts**.

**Audience:** engineers new to HypergraphAI, and engineers who will run this
demo unassisted for others.

**Format:** each `---` below is one slide. Open this file in any Markdown
slide tool (Marp, reveal-md, Slides.com import, etc.) or just read it
top-to-bottom — every command is copy-pasteable either way.

**Files in this deck:**
```
docs/decks/demo-alpha/
├── deck-demo-alpha.md              this file
├── data/
│   └── acme-eng-import.yaml        24 hypernodes + 23 hyperedges to bulk-import
└── queries/
    ├── q01–q07  *.hql              HQL (filter / aggregate) examples
    └── q08–q14  *.shql             SHQL (pattern-matching) examples
```

Every query file in this deck has been executed against a live server as
part of writing this deck — the result counts quoted throughout are real,
not illustrative.

---

## Agenda

1. **What is HypergraphAI?** — the elevator pitch
2. **Core concepts** — hypernode, hyperedge, hypergraph, hyperkey
3. **Phase 0** — clean-install environment prep
4. **Phase 1** — create a hypergraph
5. **Phase 2** — model an org as a hypergraph, bulk-import it
6. **Phase 3** — explore it in the Web UI
7. **Phase 4** — HQL: filter & aggregate queries
8. **Phase 5** — point-in-time (temporal) queries
9. **Phase 6** — SHQL: pattern-matching & multi-hop joins
10. **Phase 7** — SHQL: FILTER, OPTIONAL, UNION
11. **Phase 8** — AI-native access via MCP tools
12. **Phase 9** — RBAC & Spaces (multi-tenant isolation) — *advanced, optional*
13. **Phase 10** — inferencing & roadmap — what's live vs. what's coming
14. **Wrap-up** — recap and where to go next

---

## 1. What Is HypergraphAI?

HypergraphAI is a **hybrid semantic hypergraph document platform**. It
combines:

- The semantic expressiveness of a **knowledge graph**
- The flexibility of a **document database**
- The mathematical power of **hypergraph logic**
- Native access for **AI agents** via MCP, alongside a REST API, Web UI, and
  CLI shell for humans

**Why it's different from a typical graph database:**

| Ordinary graph DB | HypergraphAI |
|---|---|
| An edge connects exactly 2 nodes | A **hyperedge** connects *n* nodes at once |
| Edges are usually just a typed pointer | Hyperedges are first-class documents — attributes, tags, their own ID |
| "Now" is usually the only state you can query | Every node/edge can carry a **valid_from / valid_to** window — query *any* point in time |
| Bolt-on integrations for AI agents | Every operation is natively exposed as an **MCP tool** |

Keep this table in mind — every phase below demonstrates one row of it.

---

## 2. Core Concepts (for people new to graphs/hypergraphs)

**Hypernode** — an entity (a noun): a person, a team, a skill, a project.
Has an `id`, `label`, `type`, a free-form `attributes` document, `tags`, and
a `status`.

**Hyperedge** — a semantic relationship (a verb) connecting **any number**
of hypernodes, not just two. Has a `relation` (e.g. `has-member`), an
ordered list of `members`, a `flavor` describing its shape (below), and its
own `attributes`.

> **Why this matters:** "Dana has skills Python, ROS, and Computer Vision"
> is naturally **one** hyperedge with four members (Dana + 3 skills) in
> HypergraphAI. In a plain graph database you'd need three separate
> `HAS_SKILL` edges, and there'd be no single object representing "Dana's
> skill set as of today" that you could tag, timestamp, or attach metadata
> to. That's the core advantage of hyperedges being *n*-ary and first-class.

**Hypergraph** — a named container of hypernodes and hyperedges. Can be
`instantiated` (a real collection) or `logical` (a virtual view composed of
other hypergraphs).

**Hyperkey** — a SHA-256 hash generated from a hyperedge's normalized
structure (relation + members). It's how HypergraphAI deduplicates
semantically identical edges even if you didn't supply an explicit `id`.

**Edge flavor** — describes the *shape* of a relationship. Used in this demo:

| Flavor | Meaning | Used for |
|---|---|---|
| `hub` | one-to-many: first member is the "hub" | team rosters, skills, project staffing |
| `direct` | directed, first member → last member | reports-to, mentorship |
| `symmetric` | order doesn't imply direction | peer collaboration |

(`transitive` and `inverse-transitive` also exist — see Phase 10 for what
they do today vs. what's on the roadmap.)

---

## 3. Phase 0 — Clean-Install Environment Prep

**Goal:** get a running HypergraphAI server with zero graphs in it.
**Concept note:** HypergraphAI ships with one bootstrapped `admin` account
and nothing else — there is no seed data unless you explicitly load it.

```bash
git clone <repo-url>
cd hgai
cp .env.example .env

docker-compose up -d
```

This starts MongoDB and the HypergraphAI server. Give it a few seconds, then
confirm it's healthy:

```bash
curl http://localhost:8000/health
# {"status":"ok","server_id":"hgai-docker","server_name":"HypergraphAI Docker","version":"0.1.0"}
```

- Web UI: <http://localhost:8000/ui/>
- API docs: <http://localhost:8000/api/docs>
- MCP server: <http://localhost:8000/mcp/>
- Default login: `admin` / `pwd357`

> **Note:** local (non-Docker) dev is also supported via `./hgai.sh`
> (defaults to port **8357** instead of 8000) if you'd rather not use
> Docker. All commands below use port 8000 (Docker) — swap in 8357 if
> you're running locally. Everything in this deck was validated against a
> local (non-Docker) instance during authoring; the behavior is identical.

**Authenticate** (JWT — this is how a human/interactive session
authenticates; Phase 8 covers the API-key path used by AI agents):

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=pwd357"
# {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 28800}
```

Save that token — every following `curl` example uses
`-H "Authorization: Bearer <token>"`. Export it for convenience:

```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=pwd357" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

**Confirm the install is clean:**

```bash
curl -s http://localhost:8000/api/v1/graphs -H "Authorization: Bearer $TOKEN"
# {"total":0,"skip":0,"limit":..., "items":[]}
```

Zero graphs. That's our starting point.

---

## 4. Phase 1 — Create the Hypergraph

**Concept note:** a hypergraph is a namespace. Every hypernode/hyperedge you
create belongs to exactly one. We'll build one called `acme-eng`.

```bash
curl -X POST http://localhost:8000/api/v1/graphs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "id": "acme-eng",
    "label": "Acme Robotics — Engineering Org",
    "description": "Demo hypergraph modeling Acme Robotics engineering org",
    "type": "instantiated",
    "tags": ["demo", "org-chart"]
  }'
```

`type: instantiated` means this is a real, physical collection (as opposed
to `logical`, a virtual composition of other graphs — see the README's
"Architecture" section for that pattern).

**Alternative — the interactive shell.** If you'd rather work hands-on:

```bash
./hgsh.sh --server http://localhost:8000 --user admin --password pwd357
> create graph
  (paste the same fields as YAML, end with a line containing only ---)
```

Either path produces the same result — we'll use `curl` for setup steps and
the shell for exploration steps throughout this deck, so you see both.

---

## 5. Phase 2 — Model an Org as a Hypergraph

**The scenario:** Acme Robotics has 3 engineering teams, 7 people, 5 skills,
2 active projects, and a handful of semantic relationships between them.
This dataset intentionally exercises every major HypergraphAI feature:

| Data element | Feature it demonstrates |
|---|---|
| `has-skill` hub edges (1 person → several skills) | n-ary hyperedges — the core advantage over binary-edge graphs |
| `has-member` team-roster edges with `valid_from`/`valid_to` | temporal knowledge — Dana Kim moved from the Perception team to the Platform team on 2024-03-01, and **both** facts stay in the graph |
| `reports-to` (`direct`) and `collaborates-with` (`symmetric`) | edge *flavors* — the shape of a relationship is explicit, queryable metadata |
| `RelationType` hypernodes (e.g. `rel:has-member`) with an `inverse` attribute | semantic relation modeling — see Phase 10 for how this is (and isn't yet) used |
| free-form `attributes` (title, level, hired_year...) | document-database flexibility — no rigid schema per node type |

Open `data/acme-eng-import.yaml` and skim it now — it's plain, readable
YAML: a top-level `nodes:` list and `edges:` list, matching the same shape
the REST API's create endpoints accept.

**Load it in one shot** via the shell's bulk importer:

```bash
./hgsh.sh --server http://localhost:8000 --user admin --password pwd357
> use acme-eng
> import -f docs/decks/demo-alpha/data/acme-eng-import.yaml
  Import complete: 24 nodes, 23 edges imported (0 errors)
```

(The same file can be POSTed directly to `/api/v1/graphs/acme-eng/import`
if you prefer scripting over the shell — the shell command is a thin
wrapper around that same endpoint.)

**Sanity check:**

```
> ls nodes
  Hypernodes in 'acme-eng' (24 total)
> ls edges
  Hyperedges in 'acme-eng' (23 total)
```

---

## 6. Phase 3 — Explore in the Web UI

**Concept note:** everything you just did with `curl`/the shell has a GUI
equivalent — useful for stakeholders who won't touch a terminal.

Open <http://localhost:8000/ui/> and log in (`admin` / `pwd357`). Walk
through:

1. **Dashboard** — graph overview, node/edge counts for `acme-eng`
2. **Hypergraphs** — see `acme-eng` listed with its 24/23 counts
3. **Hypernodes** — browse the 24 nodes; open `person:dana-kim` and note the
   `attributes` document (title, level, hired_year, location)
4. **Hyperedges** — open `edge-skills-dana` and point out the **3-member**
   `members` array (Dana + 3 skills) in one edge — this is the hyperedge
   advantage from slide 2, made visible
5. **Query** — the interactive HQL editor; we'll use this (or the shell) for
   every query in Phases 4–7

> If you're doing a live demo, this is a good moment to let the audience
> click around before returning to the terminal for the query phases.

---

## 7. Phase 4 — HQL: Filter & Aggregate Queries

**Concept note:** HQL is HypergraphAI's primary query language, written in
YAML and modeled after MongoDB's filter semantics: `match` narrows by
type/relation, `where` applies field filters (including MongoDB operators
like `$gt`, `$in`, `$or`), `return` projects fields. Use HQL when you know
roughly *what* you're filtering for and don't need multi-hop traversal.

Run any of these with:
```bash
> query -f docs/decks/demo-alpha/queries/q01-list-people.hql
```

**q01 — list every Person** (`queries/q01-list-people.hql`)
```yaml
hql:
  from: acme-eng
  match:
    type: hypernode
    node_type: Person
  return:
    - id
    - label
    - attributes
  as: all_people
```
→ 7 results, one per engineer.

**q04 — numeric WHERE operator** (`queries/q04-where-numeric.hql`) — people
hired in 2020 or earlier:
```yaml
hql:
  from: acme-eng
  match:
    type: hypernode
    node_type: Person
  where:
    attributes.hired_year:
      $lte: 2020
  return:
    - id
    - label
    - attributes.title
    - attributes.hired_year
  as: tenured_employees
```
→ 4 results (Alex, Jamie, Sam, Leo).

**q05 — boolean `$or`** (`queries/q05-where-boolean-or.hql`) — edges that
are either a mentorship or a peer collaboration:
```yaml
hql:
  from: acme-eng
  match:
    type: hyperedge
  where:
    $or:
      - relation: mentors
      - relation: collaborates-with
  return:
    - id
    - relation
    - members
    - attributes
  as: mentorship_or_collaboration_edges
```
→ 3 results.

> **Concept note — `$or`/`$and`/`$nor`/`$not`:** any `where` key HQL doesn't
> recognize is passed straight through to MongoDB. This pass-through is
> wired up for **hyperedge** queries (as above). For **hypernode** queries,
> put boolean logic on `attributes.<field>` values instead (see q04) —
> that path is fully supported; only bare top-level boolean operators
> (`$or` etc.) directly against node attributes should be avoided today.

**q06 / q07 — matching by hyperedge member** — "which edges involve either
Dana or Priya" (`$in`, 11 results) vs. "which edge involves *both* of them"
(`$all`, 1 result — the Project Sentinel staffing edge). Run both and
compare:
```bash
> query -f docs/decks/demo-alpha/queries/q06-members-node-id-in.hql
> query -f docs/decks/demo-alpha/queries/q07-members-node-id-all.hql
```

---

## 8. Phase 5 — Point-in-Time (Temporal) Queries

**Concept note:** this is the feature that most differentiates HypergraphAI
from a typical graph database. Nodes and edges can carry `valid_from` /
`valid_to`. **Without** an `at:` clause, a query returns every version that
matches — nothing is silently hidden by default. **With** `at:`, HypergraphAI
filters to whatever was true at that instant. History is never overwritten;
it accumulates.

Recall from the import: the Perception team's roster changed on
2024-03-01, when Dana Kim moved to the Platform team.

**q02 — see every version, no `at:` clause**
(`queries/q02-team-membership-history.hql`):
```yaml
hql:
  from: acme-eng
  match:
    type: hyperedge
    relation: has-member
  where:
    members:
      node_id: team:perception
  return:
    - id
    - members
    - attributes
    - valid_from
    - valid_to
  as: perception_team_all_versions
```
→ **2 results** — both the pre- and post-move rosters, each with its own
`valid_from`/`valid_to`. This is the "nothing is hidden by default" point
made concrete.

**q03 — pin it to mid-2023** (`queries/q03-team-roster-pit.hql`) — same
filter, plus `at: "2023-06-01T00:00:00Z"`:
```yaml
hql:
  from: acme-eng
  at: "2023-06-01T00:00:00Z"
  match:
    type: hyperedge
    relation: has-member
  where:
    members:
      node_id: team:perception
  return:
    - id
    - members
    - attributes
  as: perception_roster_mid_2023
```
→ **1 result** — the roster that included Dana, Sam, and Priya. Run q02 and
q03 back-to-back; the difference is the whole point of temporal queries.

---

## 9. Phase 6 — SHQL: Pattern-Matching & Multi-Hop Joins

**Concept note:** SHQL ("shekel") is HypergraphAI's second query language —
a pattern-matching language inspired by SPARQL, not MongoDB. Instead of
filtering one collection, you describe a **shape**: nodes and edges with
`?variables`, where the same variable used in two patterns is an **implicit
join**. Use SHQL when the question involves traversal — "which X are
connected to which Y through Z" — something HQL's flat filters can't
express.

Run with `shql -f <file>` instead of `query -f`.

**q08 — join people to their teams** (`queries/q08-people-and-teams.shql`):
```yaml
shql:
  from: acme-eng
  select:
    - ?person.label
    - ?team.label
    - ?membership.valid_from
    - ?membership.valid_to
  where:
    - node:
        bind: ?person
        type: Person
    - edge:
        bind: ?membership
        relation: has-member
        members:
          - node: { bind: "?team", type: Team }
          - node: { bind: "?person" }
  order_by: ?team.label
  as: people_and_their_teams
```
`?person` is bound once by the `node` pattern, then reused inside the
`edge` pattern's members list — that shared variable *is* the join. →
**10 results** (every person × every team-roster edge they've ever
belonged to, including Dana Kim's two team memberships across time).

**q09 — expand a hub edge over every skill** (`queries/q09-skills-lookup.shql`):
```yaml
shql:
  from: acme-eng
  select:
    - ?person.label
    - ?skill.label
  where:
    - node:
        bind: ?person
        type: Person
    - edge:
        relation: has-skill
        members:
          - node: { bind: "?person" }
          - node: { bind: "?skill" }
  order_by: ?person.label
  as: person_skill_matrix
```
→ **14 results** — the full person↔skill matrix (Dana alone contributes 3
rows: Python, ROS, Computer Vision).

> **Concept note — anchoring an already-bound variable.** `?person` was
> already bound by the `node` pattern above, so when the same variable
> reappears in the `edge` pattern's members list, the engine treats that
> slot as pinned to the person we already have and lets the *other* slot
> (`?skill`) expand freely across every remaining member. This is what
> makes multi-member hyperedges (several skills, several project staff)
> safe to join against — q10 below relies on the same behavior for two
> variables at once.

**q10 — project staffing** (`queries/q10-staffing-by-project.shql`) — the
same join pattern, applied to both `?project` and `?person`:
```yaml
shql:
  from: acme-eng
  select:
    - ?project.label
    - ?person.label
    - ?person.attributes.title
  where:
    - node:
        bind: ?project
        type: Project
    - node:
        bind: ?person
        type: Person
    - edge:
        relation: staffed-on
        members:
          - node: { bind: "?project" }
          - node: { bind: "?person" }
  order_by: ?project.label
  as: project_staffing
```
→ **7 results** — Project Atlas (4 staff) + Project Sentinel (3 staff),
correctly attributing each person to the right project even though Dana
Kim is staffed on both.

---

## 10. Phase 7 — SHQL: FILTER, OPTIONAL, UNION

**q11 — FILTER expression** (`queries/q11-filter-hired-before-2021.shql`):
plain node match, then a string-based filter expression evaluated against
the bound variable:
```yaml
shql:
  from: acme-eng
  select:
    - ?person.label
    - ?person.attributes.title
    - ?person.attributes.hired_year
  where:
    - node:
        bind: ?person
        type: Person
    - filter: "?person.attributes.hired_year < 2021"
  order_by: ?person.label
  as: people_hired_before_2021
```
→ **4 results**. FILTER also supports `CONTAINS(...)`, `STARTS_WITH(...)`,
`IN [...]`, `AND`/`OR`/`NOT`, and more.

**q12 — OPTIONAL** (`queries/q12-optional-mentor.shql`) — **concept note:**
OPTIONAL is a left outer join: it tries to extend each binding, and if it
can't, keeps the original binding with the optional variable left
unbound (`null`) rather than dropping the row. Deliberately, not everyone
in this dataset has a mentor:
```yaml
shql:
  from: acme-eng
  select:
    - ?person.label
    - ?mentor.label
  where:
    - node:
        bind: ?person
        type: Person
    - optional:
        - edge:
            relation: mentors
            members:
              - node: { bind: "?mentor" }
              - node: { bind: "?person" }
  order_by: ?person.label
  as: people_with_optional_mentor
```
→ **7 results** — every person appears exactly once; only Noor
(`mentor.label: "Leo Martins"`) and Priya (`"Dana Kim"`) have a non-null
mentor. Compare this to an inner join, which would have silently dropped
the other 5 people.

**q13 — UNION** (`queries/q13-union-python-or-lead.shql`) — **concept
note:** UNION merges the results of independent pattern branches (each
branch can bind variables completely differently) and de-duplicates by
binding, when combined with `distinct: true`. Here: everyone who either
knows Python *or* holds a "lead" title:
```yaml
shql:
  from: acme-eng
  select:
    - ?person.id
    - ?person.label
  where:
    - union:
        - patterns:
            - node:
                bind: ?person
                type: Person
            - edge:
                relation: has-skill
                members:
                  - node: { bind: "?person" }
                  - node: { id: skill:python }
        - patterns:
            - node:
                bind: ?person
                type: Person
            - filter: "?person.attributes.level = 'lead'"
  distinct: true
  order_by: ?person.label
  as: python_or_lead
```
→ **6 distinct results** (5 Python users ∪ 3 leads, with Jamie and Sam
counted once despite matching both branches).

**q14 — PIT query in SHQL** (`queries/q14-pit-team-roster.shql`) — the same
`at:` clause from Phase 5 works in SHQL too:
```yaml
shql:
  from: acme-eng
  at: "2023-06-01T00:00:00Z"
  select:
    - ?person.label
    - ?team.label
  where:
    - edge:
        relation: has-member
        members:
          - node: { id: team:perception, bind: "?team" }
          - node: { bind: "?person", type: Person }
  order_by: ?person.label
  as: perception_roster_mid_2023_shql
```
→ **3 results** (Dana, Priya, Sam) — same answer as HQL's q03, expressed as
a pattern-match instead of a filter.

---

## 11. Phase 8 — AI-Native Access via MCP

**Concept note:** MCP (Model Context Protocol) is how AI agents (Claude
Desktop, custom agents, etc.) call tools. HypergraphAI exposes every
CRUD/query operation as an MCP tool at `http://localhost:8000/mcp/` — an
agent doesn't need a bespoke integration; it gets the same 14 tools a human
would use via curl.

**Machine-to-machine auth uses an API key, not a JWT login.** Generate one:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Add it to `.env` as `HGAI_PRIMARY_API_KEY=<value>` and restart the server.
Unlike a JWT, an API key doesn't expire and skips the login step entirely —
appropriate for a long-running agent process, not for a human's browser
session.

**List available tools:**
```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

**Call a tool** — fetch Dana Kim's node exactly as an agent would:
```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <api-key>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "hgai_hypernode_get",
      "arguments": {"graph_id": "acme-eng", "node_id": "person:dana-kim"}
    }
  }'
```

**Run an HQL/SHQL query as a tool call** — this is the same q01 from Phase
4, called as `hgai_query_execute` instead of the REST `/query` endpoint:
```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <api-key>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "hgai_query_execute",
      "arguments": {
        "query_yaml": "hql:\n  from: acme-eng\n  match:\n    type: hypernode\n    node_type: Person\n  return:\n    - id\n    - label\n  limit: 50"
      }
    }
  }'
```

**Wire it into Claude Desktop or another MCP client:**
```json
{
  "mcpServers": {
    "hgai": {
      "url": "http://localhost:8000/mcp/",
      "headers": { "Authorization": "Bearer <api-key>" }
    }
  }
}
```
Once configured, an agent can ask "who's staffed on Project Sentinel?" and
the model will call `hgai_query_execute` with an SHQL query resembling q10,
with no custom integration code required.

---

## 12. Phase 9 — RBAC & Spaces *(advanced, optional)*

**Concept note:** everything so far lived in one "unowned" hypergraph
(`acme-eng`), accessible to any account with the right `permissions.graphs`
entry. **Spaces** add multi-tenant isolation: a named group of hypergraphs
with per-member roles (`owner`, `admin`, `member`, `viewer`). Space
membership is the sole access gate for a space-scoped graph — a global
`permissions.graphs: ["*"]` wildcard does **not** leak across tenants.

Skip this phase for a quick demo; include it when the audience cares about
multi-tenant deployment.

```bash
# Create a space
curl -X POST http://localhost:8000/api/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"id": "acme-robotics", "label": "Acme Robotics"}'

# Add a member
curl -X POST http://localhost:8000/api/v1/spaces/acme-robotics/members \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username": "alice", "role": "member"}'

# Create a graph inside the space — same graph ID can exist in other spaces
curl -X POST http://localhost:8000/api/v1/spaces/acme-robotics/graphs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"id": "acme-eng", "label": "Acme Eng (space-scoped copy)"}'
```

Space-scoped graphs are referenced in HQL/SHQL with a slash:
`from: acme-robotics/acme-eng` instead of the bare `from: acme-eng` we used
throughout this deck. Everything else — HQL, SHQL, PIT, MCP tools — works
identically once you're inside a space.

---

## 13. Phase 10 — Inferencing & Roadmap: What's Live vs. What's Coming

**Concept note for newcomers:** *inferencing* means deriving facts that
were never explicitly stored — e.g., if "Team has-member Dana" is stored
and `has-member`'s inverse is declared as `member-of`, an inference engine
can produce "Dana member-of Team" without you writing that edge yourself.

Our dataset includes the scaffolding for this: `rel:has-member` and
`rel:mentors` both declare an `inverse` attribute, and several edges use
the `transitive`-capable flavor system. **Be precise with your audience
about what this means today:**

| Capability | Status |
|---|---|
| Edge `flavor` field (`hub`, `direct`, `symmetric`, `transitive`, `inverse-transitive`) | **Live** — stored, queryable as plain metadata via `match.flavor` |
| `RelationType.attributes.inverse` declaration | **Live** — stored as data, human/agent-readable |
| Automatic inverse-edge generation at query time | Implemented at the engine level (`hgai/core/inference.py`), **not yet wired into HQL, SHQL, the REST API, or MCP tools** |
| Transitive-closure reachability checks | Same — engine function exists, **not yet exposed** through any query path |
| SKOS (`broader`/`narrower`/`related`) semantic inferencing | **Roadmap** — planned via hyperedge hub relations |
| HQL `infer:` clause | **Roadmap** |

**Why this matters for your demo:** don't promise a live audience that
querying will "automatically" produce `member-of` from `has-member` today —
it won't. What you *can* honestly say: the data model already captures
everything needed for that inference (the `inverse` attribute is sitting
right there on `rel:has-member`), and turning it on is a matter of the
query engine catching up to data that's already shaped correctly. That's a
genuinely strong story about designing for the future without over-claiming
what runs today.

---

## 14. Wrap-Up

**What we demonstrated, in order:**

- A **hypergraph** namespace (`acme-eng`) created from nothing
- **Hypernodes** across 6 types (Organization, Team, Person, Skill,
  Project, RelationType) with free-form `attributes`
- **Hyperedges** with 2–5 members each, across 3 **flavors** (`hub`,
  `direct`, `symmetric`) — the n-ary advantage made concrete via
  `edge-skills-dana` (1 edge, 4 members)
- **Temporal validity** (`valid_from`/`valid_to`) and **point-in-time**
  queries in both HQL (q03) and SHQL (q14) — nothing overwritten, ever
- **HQL** — filters, numeric operators, boolean `$or`, member-list
  matching (`$in`/`$all`)
- **SHQL** — multi-hop joins via shared `?variables`, `FILTER`,
  `OPTIONAL` (left outer join), `UNION`
- The **Web UI** for non-technical stakeholders
- **MCP tools** — the exact mechanism an AI agent uses, with no custom
  integration code
- *(optional)* **Spaces** for multi-tenant isolation
- An honest look at what's **live** vs. **roadmap** in the inferencing engine

**Where to go next:**

- `README.md` at the repo root — the full reference this deck was built
  from (architecture, complete API reference, all WHERE operators, mesh
  federation for multi-server deployments)
- `docs/api-reference.md` — full REST API reference
- `scripts/seed_data.py` — a second, smaller example dataset (Three
  Stooges) if you want a different demo story
- `tests/` — `test_engine.py`, `test_query.py`, `test_mesh.py` for engine
  internals

**Cleanup, if you loaded this into a shared/persistent server:**
```bash
curl -X DELETE http://localhost:8000/api/v1/graphs/acme-eng \
  -H "Authorization: Bearer $TOKEN"
```
