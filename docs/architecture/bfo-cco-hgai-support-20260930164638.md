# How HypergraphAI Would Support BFO and CCO Based Ontologies

Report generated 2026-09-30. Status: analysis and proposal. Nothing in this document is implemented except where it says "works today", and every "works today" claim was checked against the code or run (see Appendix A).

## 1. Summary

**BFO** (Basic Formal Ontology, ISO/IEC 21838-2) is a small top-level ontology: continuants versus occurrents, independent and dependent entities, qualities, roles, dispositions, processes, and a handful of core relations (part of, participates in, inheres in, realizes). **CCO** (the Common Core Ontologies) is a suite of mid-level ontologies built on BFO, covering agents, artifacts, events, information entities, time, geospatial regions, units of measure and similar domains. Both are published as OWL 2 files.

**Bottom line.** HypergraphAI can already hold these ontologies faithfully, browse them, query them, and answer the most common structural questions about them. It cannot yet behave like an ontology platform: it does not reason about class hierarchies on its own, it does not export back to OWL, it does not validate data against ontology axioms, and in a multi-tenant deployment there is no way to share one copy of an ontology across tenants. Each of those gaps has a concrete, bounded fix.

| Area | Today | Needs work |
|---|---|---|
| Load an OWL file (Turtle, RDF/XML, JSON-LD, N3) | Works. Classes, properties, annotations and axioms become nodes and edges with no errors | Language tags are dropped; `owl:imports` is not followed |
| Inverse, transitive and symmetric properties (BFO `part of` / `has part`, `participates in` / `has participant`) | Works. Converted to axioms that `infer: true` uses | None for these three |
| Class hierarchy (`rdfs:subClassOf`) | Stored as edges. Ancestors are available with a one-line workaround (section 4.2) | Make the workaround automatic; add "instances of X including subclasses" |
| Property hierarchy (`rdfs:subPropertyOf`) | Stored as edges only | Map onto the existing superproperty axiom |
| Restrictions, disjointness, domain, range, cardinality | Stored faithfully as structure; no semantics | Validation module; optional external reasoner |
| Instance data using BFO and CCO | Works, with good fit: n-ary edges and point-in-time validity match how BFO treats participation and time | Conventions to document; optional member roles |
| Agents (MCP) | Works. Agents can look up definitions and ground their answers | Label-aware helpers |
| Export back to OWL, Protege and ROBOT round trip | Not available | New export |
| Share one ontology across tenants | Not available | Shared read-only graphs |

Recommended sequence (section 8): a small "ontology import profile" first, because it turns most of the partial items above into working ones; then class-subsumption queries, an ontology browser, and OWL export; then shared graphs, validation, and reasoner integration.

## 2. What BFO and CCO are, for this purpose

This section is background so the mapping below can be read on its own. Identifiers quoted here are the well-known BFO ones; check them against the release you adopt. CCO identifiers are deliberately not quoted, since they are opaque numeric ids that vary by release.

- **BFO.** Roughly three dozen classes and about a hundred relations. Examples: `entity` (BFO_0000001), `continuant` (BFO_0000002), `occurrent` (BFO_0000003), `independent continuant` (BFO_0000004), `material entity` (BFO_0000040), `process` (BFO_0000015), `quality` (BFO_0000019), `role` (BFO_0000023), `disposition` (BFO_0000016). Core relations: `part of` (BFO_0000050) and its inverse `has part` (BFO_0000051), `participates in` (BFO_0000056) and `has participant` (BFO_0000057), `inheres in` (BFO_0000197) and `bearer of` (BFO_0000196), `realizes` (BFO_0000055), `occurs in` (BFO_0000066). Several are transitive or have declared inverses. BFO 2020 adds temporally qualified relations, which matter for how time is modeled (section 5.3).
- **CCO.** A modular set of ontologies (agent, artifact, event, information entity, quality, time, geospatial, units of measure, and others) that specialize BFO classes with mid-level classes such as agents, organizations, artifacts, acts and measurements, plus their own relations and heavy use of OWL restrictions. As I understand it, it originated in the defense and intelligence community, which is why it is often used for operational data models. Scale is on the order of a thousand classes and a few hundred properties; confirm against the release.
- **Two uses.** *Schema use* (the ontology itself: classes, properties, axioms, definitions) and *data use* (instances described with those classes and relations). HypergraphAI serves both, in separate graphs.
- **Format.** OWL 2, distributed as RDF/XML or Turtle, with annotations such as definitions (`obo:IAO_0000115`), examples, editor notes and alternative terms, in English with language tags, and with `owl:imports` linking the CCO modules.

## 3. How an ontology maps onto HypergraphAI today

I imported a 23-line fragment shaped like BFO and CCO (real BFO ids for the core classes and relations, a stand-in mid-level class with an existential restriction, and one instance) through the real RDF importer and then queried it with SHQL in a real engine. The fragment and the raw results are in Appendix A. The mapping is:

| OWL / RDF construct | Becomes in HypergraphAI | Usable today? |
|---|---|---|
| `owl:Class`, `owl:ObjectProperty`, `owl:AnnotationProperty` declarations | A hypernode. `id` is the full IRI (for example `http://purl.obolibrary.org/obo/BFO_0000040`), `label` is the `rdfs:label`, `type` is `Class` or `ObjectProperty`, and `attributes.rdf_type` holds the full type IRIs | Yes |
| `rdfs:subClassOf` between named classes | A hub hyperedge, relation = the full `rdfs:subClassOf` IRI, members = `[subclass, superclass]` | Stored. Ancestor and descendant closure needs one axiom (section 4.2) |
| `rdfs:subPropertyOf` | The same, relation = `rdfs:subPropertyOf` | Stored only. Not wired to the inference engine |
| `owl:inverseOf` | An `owl:inverse-of` axiom edge | Yes, used by `infer: true` |
| `owl:TransitiveProperty` (BFO `part of`) | An `owl:transitive` axiom edge | Yes |
| `owl:SymmetricProperty` | An `owl:symmetric` axiom edge, and its data edges get the `symmetric` flavor | Yes |
| Annotation literals (definitions, examples, `skos:altLabel`) | A node attribute keyed by a compact CURIE, for example `attributes["obo:IAO_0000115"]` | Yes, without language tags |
| `owl:Restriction` (`someValuesFrom`, `allValuesFrom`, cardinalities) on an anonymous class | A blank-node hypernode (`bnode:...`, type `Restriction`) joined by `onProperty` and `someValuesFrom` edges, and referenced from the subclass by an ordinary `rdfs:subClassOf` edge | Structure preserved, so it can be browsed and queried. No reasoning over it |
| `owl:disjointWith` | An ordinary edge | Stored only |
| `owl:equivalentClass`, property chains, `owl:imports`, domain and range | Domain and range and equivalence: ordinary edges. Chains: stored as blank-node structure. Imports: ignored | Stored only (chains are a listed roadmap item) |
| An instance `ex:alice a ex:Agent` | A hypernode. `type` is the short local name (`Agent`), and the full class IRI is in `attributes.rdf_type` | Yes |
| An object-property assertion `ex:alice BFO_0000056 ex:act1` | A hub hyperedge, relation = the property IRI | Yes |
| Language tags (`"entity"@en`) | Dropped | Gap (section 5) |

Two consequences are worth knowing before anything else. First, the structure of the ontology survives import intact, including the parts HypergraphAI cannot reason about, so nothing is lost and everything can be browsed and queried. Second, the import never invents semantics: the class hierarchy is stored, but no rule says it is transitive, which is why section 4.2 exists.

## 4. What works today

### 4.1 Load and browse

Use the existing import, one graph per ontology module:

```
hgsh> import-rdf -f bfo-core.owl -g bfo --format xml
hgsh> import-rdf -f cco-agent.ttl -g cco-agent --format ttl
```

The fragment imported with 16 nodes, 15 edges and 0 errors. IRI ids (which contain dots and slashes) are accepted throughout: REST paths, SHQL, the Web UI. Definitions land in attributes and appear in the node editor. The 3D visualization shows the hierarchy as a graph. A 5,000-node ontology is well inside the platform's normal range; only the default SHQL candidate caps (2,000 nodes and edges per pattern, `HGAI_SHQL_MAX_NODE_CANDIDATES` and `HGAI_SHQL_MAX_EDGE_CANDIDATES`) matter for a CCO-sized graph, and they can be raised.

### 4.2 Ancestors of a class, with one axiom

Transitive closure in HypergraphAI is a property of a relation, declared as an `owl:transitive` axiom edge, and `rdfs:subClassOf` is an ordinary relation. So declaring it transitive, in data rather than code, makes the whole class hierarchy walkable. Two records are needed: a node for the predicate and an axiom edge naming it. I ran exactly this:

```
node   id: http://www.w3.org/2000/01/rdf-schema#subClassOf   type: RelationType
edge   relation: owl:transitive   members: [ that node ]
```

and then queried for the superclasses of the stand-in `Agent` class:

```yaml
shql:
  from: bfo
  infer: true
  select:
    - ?e.members
    - ?e._inferred
  where:
    - edge:
        bind: ?e
        relation: http://www.w3.org/2000/01/rdf-schema#subClassOf
        members:
          - node_id: http://example.org/mid#Agent
            seq: 0
```

Result: `material entity` (stated), then `independent continuant`, `continuant` and `entity` (all returned as `_inferred: true`), plus the stated link to the restriction blank node. The full chain up to `entity` was derived without storing it. The same works for descendants by putting the class at `seq: 1`, and for any other transitive relation such as BFO `part of` (already a generated axiom).

### 4.3 Properties that BFO declares transitive, inverse or symmetric

`part of` / `has part` and `participates in` / `has participant` arrive as inverse and transitive axioms with no extra work. Asking for `has participant` facts returns those derived from stored `participates in` facts, marked `_inferred`. This covers the most used part of BFO's relation reasoning.

### 4.4 Instance data in BFO and CCO terms

Two platform features line up well with how BFO thinks:

- **Participation and other n-ary facts.** A hyperedge joins any number of nodes, so "this act has these participants" can be one edge rather than a cluster of binary ones, and a hyperedge can itself be a member of another edge, which gives a natural home for reified relations and relational qualities.
- **Time.** Nodes and edges carry `valid_from` and `valid_to`, and every query accepts a point in time (`at:`). That matches BFO's treatment of continuants, where relations hold at times, without inventing a time-indexing convention in the data.

### 4.5 Composition, multi-ontology and versioning

- CCO is modular. Import each module into its own graph and define a **logical hypergraph** composing them, so `from: cco-all` queries the whole suite while each module stays separately loadable.
- SHQL `from:` accepts several graphs at once, so BFO, CCO modules and an application graph can be queried together.
- Keep each ontology *version* in its own graph (`bfo-2020`, `cco-2024`). The point-in-time feature is for when facts were true, not for ontology releases.

### 4.6 Agents

Every query and lookup is an MCP tool, so an AI agent can fetch a class definition, list subclasses, or check a relation's axioms before it writes data. An ontology graph therefore works as grounding context for agent memory, with access governed by the same account and tenant rules as any graph.

## 5. Gaps

Severity reflects how much each gap hurts a BFO and CCO user, not how hard it is to fix.

| # | Gap | Severity | What it means in practice |
|---|---|---|---|
| G1 | The class hierarchy is not reasoned over by default | High | Every user has to know the section 4.2 axiom. "All instances of Material Entity" misses instances of its subclasses, because an instance stores only its direct class |
| G2 | `rdfs:subPropertyOf` is not wired to inference | Medium | BFO has property hierarchies (for example continuant part of under part of); a query on the super-property misses facts stated with the sub-property |
| G3 | No OWL export | High | Users cannot return to Protege or ROBOT, and cannot share a curated ontology as OWL |
| G4 | No validation against ontology axioms | High | Disjointness (continuant versus occurrent), domain and range, and required relations are stored but never checked against instance data |
| G5 | Restrictions and other class expressions have no semantics | Medium | Stored and browsable, but `Agent subClassOf participates-in some Process` does not produce or check anything |
| G6 | Language tags on labels and definitions are dropped | Medium | Multilingual ontologies lose the language. BFO and CCO are mostly English, so this matters less for them |
| G7 | `owl:imports` is not followed | Medium | Each CCO module must be downloaded and imported by hand, in order |
| G8 | Instance `type` is the short local name, and ontology ids are opaque | Medium | Screens show `ont00000xxx`-style ids rather than "Organization". Labels exist but are not used when displaying a type |
| G9 | No shared read-only graphs across tenants | High for multi-tenant deployments | With tenancy on, a tenant cannot see another tenant's graphs, so each tenant needs its own copy of the ontology. The multi-tenancy plan lists this as an open question and it was not built |
| G10 | SPARQL property paths such as `rdf:type/rdfs:subClassOf*` are out of scope | Medium | That path is the standard way ontology users ask "instances including subclasses". The planned SPARQL translator deliberately excludes general paths |
| G11 | No DL reasoner | Medium | No consistency checking, classification of defined classes, or property chains. The engine's rules are a small fixed set |
| G12 | Hyperedge members have no role | Low | CCO patterns often name the role of each participant. A member has a node id and a sequence number only, so roles have to be encoded by convention (section 6.4) |
| G13 | Import adds no ontology-specific help | Low | No class tree view, no definition panel, no search by definition |

## 6. Recommended approach

### 6.1 Graph layout

| Graph | Holds | Notes |
|---|---|---|
| `bfo-<version>` | BFO | One graph per ontology release |
| `cco-<module>-<version>` | Each CCO module | Mirrors CCO's own modularity |
| `cco-<version>` (logical) | Composition of the modules above, and of BFO | Query this for the whole suite |
| `<application>` | Instance data and any application-specific classes | Conforms to the above; a separate graph, possibly in a space |

Keep ontologies and instance data apart so an ontology can be reloaded or upgraded without touching data.

### 6.2 Bootstrap that applies after every import (works today)

For each ontology graph: create the `rdfs:subClassOf` predicate node and its `owl:transitive` axiom (section 4.2). For each `rdfs:subPropertyOf` pair, nothing yet (G2). This step should become part of the import (R1).

### 6.3 Class queries

Until R2 exists, "instances of X including subclasses" is two steps: fetch the descendants of X with the section 4.2 query (class at `seq: 1`), then match instances whose `attributes.rdf_type` is in that list (`attributes: {rdf_type: {$in: [...]}}`). Materializing the closure with the existing Project Inference feature is an alternative when queries are frequent: it persists the inferred subclass edges so they can be read without `infer: true`.

### 6.4 Modeling instance data

- **Participation and similar n-ary facts.** One hub edge per fact, the first member as the hub (for example the process), relation = the BFO or CCO property IRI.
- **Time.** Put the period in `valid_from` and `valid_to` on the edge. "At all times" relations are edges with no end; "at some time" relations are edges with a period.
- **Roles of participants (G12).** Until members can carry roles, choose one: fix a role per `seq` position and document it per relation; record roles in the edge's `attributes` (`{"roles": {"agent": 1, "patient": 2}}`), keyed to `seq`; or use one binary edge per role. The second keeps everything in one edge and is the recommended default.
- **Measurements and qualities.** Model the quality as its own node, related to its bearer by `inheres in`, with the value and unit as attributes or further nodes. A hyperedge member may itself be an edge, which fits relational qualities.

### 6.5 Agents and operational data

CCO's agent, artifact and act classes suit systems that track assets, tasks and events. As an illustration, in an integration such as the Anduril Lattice work described in `docs/marketing`, a tracked asset would be an instance of a CCO artifact subclass, a tasking an act, and their relations BFO and CCO properties, so agents and analysts share vocabulary. This is an option to evaluate, not something that has been built or agreed.

### 6.6 Reasoning beyond the built-in rules

For class classification, consistency checks, or property chains, run an external reasoner (ELK for the OWL EL profile, HermiT or similar for full DL) through ROBOT, and load the result: import the inferred hierarchy as a new graph version, or persist it with Project Inference. This needs G3 (export) for the round trip, so export comes first.

### 6.7 Multi-tenant deployments

Until G9 is solved, load the ontology per tenant. An ontology loaded by a system admin without a tenant is system level and invisible to tenant accounts. Load it into each tenant through that tenant's own import, and treat the ontology as tenant data.

## 7. Proposed work items

Sizes are rough effort: S is days, M is one to two weeks, L is several weeks. Each lists how to tell it is done.

| Id | Item | Size | Closes | Done when |
|---|---|---|---|---|
| R1 | **Ontology import profile.** An `ontology=true` import option (REST, shell, UI) that: creates the `rdfs:subClassOf` predicate node and transitive axiom; maps `rdfs:subPropertyOf` onto the existing superproperty axiom (direction to be confirmed against `skos:broaderTransitive` semantics in the inference engine); preserves language tags as `attributes["<key>#lang"]`; labels restriction blank nodes | S to M | G1 (partly), G2, G6 | Importing the real BFO release gives ancestors and sub-property facts with no manual step |
| R2 | **Class subsumption in queries.** A node pattern option (for example `type: X` with `subclasses: true`, or `infer: true` honored on `type`) that matches instances of X and its subclasses by expanding the class closure before matching. Cache the closure per graph | M | G1 | "Instances of Material Entity" returns instances of every subclass with one query |
| R3 | **Ontology browser.** A class tree in the Web UI with definitions and labels, labels shown for type chips and ids, search over labels and definitions | M | G8, G13 | A user can navigate BFO and CCO without reading IRIs |
| R4 | **OWL export.** Turtle, RDF/XML and JSON-LD export of a graph, mapping the internal axiom edges back to their real predicates and restoring blank-node restrictions | M | G3 | Import, edit, export, and open in Protege with the same axioms |
| R5 | **Imports.** Follow `owl:imports` on import, creating one graph per module and a logical composition | M | G7 | Importing the top CCO file yields all modules with no manual step |
| R6 | **Shared read-only graphs.** A flag on a system-level graph making it readable (never writable) by every tenant | M | G9 | A tenant account queries the ontology; none can change it |
| R7 | **SPARQL path special cases.** In the planned SPARQL translator, map `rdf:type/rdfs:subClassOf*` and `rdfs:subClassOf*` onto R2's class closure instead of rejecting them | M | G10 | Standard ontology SPARQL patterns run |
| R8 | **Validation, first as queries.** A library of saved parameterized queries for disjointness violations, missing required relations and domain and range; then a validation module reporting them | S (queries), L (module) | G4, G5 | A report lists instances that violate BFO and CCO axioms |
| R9 | **Reasoner round trip.** Documented ROBOT and ELK pipeline using R4, with inferred results loaded as a graph version | M | G11 | A scripted run classifies an ontology and loads the result |
| R10 | **Member roles.** An optional `role` on hyperedge members, carried through import, export, SHQL and the UI | M | G12 | CCO-style n-ary facts keep roles without conventions |
| R11 | **Property chains.** The inference roadmap item | L | G11 | A CCO chain derives its implied relation |

### Suggested order

1. **R1, R2, R8 (queries only).** Small, and they convert the most "stored only" rows into "works". After these, BFO and CCO are genuinely usable for schema queries and validation.
2. **R4, R3, R5.** Make the platform a complete place to work on an ontology: export, browse, load by reference.
3. **R6, R7, R9.** Multi-tenant sharing, ontology-style SPARQL, and external reasoning.
4. **R10, R11, and the R8 module.** Larger changes to the model and inference engine; do them when a concrete use case demands them.

## 8. Risks and open questions

- **Only a fragment was tested.** The probe used real BFO identifiers but not the full BFO or any CCO release. Before committing to the plan, import the actual files and check: import time and errors, how many restriction blank nodes appear, and whether the SHQL candidate caps need raising. Treat the claims in section 3 as verified for the constructs in the fragment and expected, not proven, for the rest.
- **Blank-node restrictions are numerous in CCO.** They appear as superclasses in the section 4.2 results. Queries for "superclasses" need to exclude `Restriction` nodes, which R1's labeling supports.
- **Property direction in R1.** The inference engine's `skos:broaderTransitive` axiom has a specific direction convention. Mapping `rdfs:subPropertyOf` onto it must be confirmed against the engine and covered by a test before shipping.
- **Type naming.** An instance's `type` is the local name of its class, which can collide across ontologies that reuse local names. Queries that need precision should match `attributes.rdf_type` (the full IRI), which R2 should do.
- **Expectations about reasoning.** HypergraphAI's inference is deliberately a small, fixed, live set of rules. Users coming from OWL reasoners should be told plainly that classification and consistency checking need R9.
- **Versioning policy.** Decide whether ontology releases are separate graphs (recommended) or separate spaces, and how instance data is migrated when a release renames or merges a class.
- **Licensing.** Confirm the license terms of the BFO and CCO releases you redistribute with a deployment.

## Appendix A. The probe

**Fragment imported** (abridged to its distinct parts; 23 lines in all):

```turtle
obo:BFO_0000001 a owl:Class ; rdfs:label "entity"@en .
obo:BFO_0000002 a owl:Class ; rdfs:label "continuant"@en ; rdfs:subClassOf obo:BFO_0000001 ; owl:disjointWith obo:BFO_0000003 .
obo:BFO_0000040 a owl:Class ; rdfs:label "material entity"@en ; rdfs:subClassOf obo:BFO_0000004 .
obo:BFO_0000050 a owl:ObjectProperty, owl:TransitiveProperty ; rdfs:label "part of"@en ; owl:inverseOf obo:BFO_0000051 .
obo:BFO_0000176 a owl:ObjectProperty ; rdfs:subPropertyOf obo:BFO_0000050 .
obo:BFO_0000040 obo:IAO_0000115 "An independent continuant that is spatially extended ..."@en .
ex:Agent a owl:Class ; rdfs:subClassOf obo:BFO_0000040 ,
   [ a owl:Restriction ; owl:onProperty obo:BFO_0000056 ; owl:someValuesFrom obo:BFO_0000015 ] .
ex:alice a ex:Agent ; obo:BFO_0000056 ex:act1 .
```

**Import result** (real importer, 0 errors): 16 nodes and 15 edges, including:

- node `http://purl.obolibrary.org/obo/BFO_0000040`: label `material entity`, type `Class`, `attributes["obo:IAO_0000115"]` holding the definition (language tag dropped);
- node `http://example.org/mid#alice`: type `Agent`, `attributes.rdf_type` = the full `Agent` IRI;
- a blank-node node of type `Restriction` with `onProperty` and `someValuesFrom` edges, referenced by an ordinary `subClassOf` edge from `Agent`;
- `subClassOf` edges, a `subPropertyOf` edge, a `disjointWith` edge, all stored as plain hub edges;
- generated axioms: `owl:inverse-of` for both inverse pairs and `owl:transitive` for `part of`.

**Class closure query** (section 4.2) after adding the `subClassOf` predicate node and an `owl:transitive` axiom edge: five rows for `Agent`, namely the restriction blank node (stated), `material entity` (stated), and `independent continuant`, `continuant`, `entity` (inferred).

## Appendix B. Code and documents this report relies on

- RDF import mapping: `hgai/core/rdf_import.py`, README section "RDF Import".
- Inference rules and the axiom vocabulary: `hgai/core/inference.py`, README section "Inferencing".
- SHQL: `hgai_module_shql/engine.py`, README section "SHQL".
- SPARQL plan and its non-goals (general property paths, language and datatype): `docs/architecture/sparql-to-shql-conversion-plan.md`, `docs/architecture/sparql-vs-shql-gaps.md`.
- Tenancy and the shared reference graph question: `docs/architecture/hypergraph-ai-multi-tenancy-20260930120844.md`, section 10, question 4.
