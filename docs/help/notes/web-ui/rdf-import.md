---
id: help-rdf-import
label: Importing RDF (concepts, examples, caveats)
name: rdf-import
description: How RDF/OWL (Turtle, RDF/XML, JSON-LD, Notation3) maps onto hypernodes and hyperedges — the full mapping model, worked examples, and what's not handled.
tags: ["//Using the Web UI", rdf, turtle, owl, rdfs, jsonld, semantic-web, import]
status: active
---

# Importing RDF (concepts, examples, caveats)

HypergraphAI can import an existing RDF file — **Turtle** (`.ttl`), **RDF/XML** (`.rdf`, `.xml`), **JSON-LD** (`.jsonld`) or **Notation3** (`.n3`) — mapping every triple onto hypernodes and hyperedges. This topic is the deep dive: the full mapping model, worked examples (including OWL axioms feeding straight into [Inferencing](help:help-inferencing)), and every documented caveat. For the short reference table and the create/merge/entry-point mechanics shared with native export/import, see [Exporting and importing hypergraphs](help:help-export-import).

## Where to start it

| Surface | How |
|---|---|
| Web UI | **Hypergraphs → Import**, choose the RDF file — the **Hypergraph ID** field becomes required (RDF has no hypergraph id of its own) |
| Shell | `import-rdf -f data.ttl -g my-graph [--format ttl\|n3\|rdf\|xml\|jsonld] [--merge]` — format is inferred from the file extension if omitted ([The hgsh shell](help:help-shell)) |
| REST | `POST /api/v1/graphs/import/rdf?graph_id=my-graph&format=ttl` (body: the raw file); space-scoped graphs use `/spaces/{space_id}/graphs/import/rdf` ([REST API](help:help-rest-api)) |

Same per-item error handling (first 25 errors reported, everything else still loads), the same `create`/`merge` modes, and the same 100 MB size limit as a native export import — see [Exporting and importing hypergraphs](help:help-export-import) for those shared mechanics.

## Concepts

RDF has no native n-ary relationships, so the mapping is deliberately simple: **every triple becomes one two-member hyperedge**, never a fused multi-member one.

### Identity: prefixes always expand

Every subject, and every object that's an IRI or blank node (never a literal), becomes a **hypernode**. Its id is the term's **full, expanded IRI** — a `prefix:local` shorthand always expands to the complete IRI, never left compacted:

```turtle
@prefix ex: <http://example.com/> .
ex:adam a ex:Person .
```

`ex:adam` becomes hypernode id `http://example.com/adam` — not `ex:adam`. A blank node's id is `bnode:<rdflib's blank node label>` (it has no IRI to expand).

> **Why expand ids but not attribute keys?** An id is a plain *value* — the dots an IRI routinely contains (`example.com`) are harmless there. An attribute key becomes a literal MongoDB subdocument field name, and SHQL's `attributes: {key: value}` pattern filter builds a dot-path query from it — a dotted key would silently address the wrong, nonexistent nested path. So attribute keys are the one deliberate exception: they stay sanitized `prefix:local` CURIEs (`attributes["foaf:age"]`), never expanded.

### `rdf:type`, labels

`rdf:type` sets the hypernode's `type` (the first type's short local name, sorted for determinism if there are several — a display category, not an identifier) and is also kept in full in `attributes.rdf_type` (a list of expanded IRIs). A label comes from the first of `rdfs:label`, `skos:prefLabel`, `foaf:name`, `dc:title`, `dcterms:title` found on the subject, else the IRI's own local name.

### Literal-valued triples → attributes

Any other literal-valued predicate becomes a hypernode **attribute**, keyed by its sanitized CURIE (see above). The **value** is classified by its own lexical text, not its RDF/XSD datatype:

| Lexical form starts with… | Becomes |
|---|---|
| A digit (`0`–`9`) | A **number** — `int` if it parses as one, else `float`; **`-1`** if neither parse succeeds. This applies even to a value RDF typed as a plain string, e.g. a quoted `"12345"` with no datatype still becomes the number `12345` |
| Anything else | **Text** (the lexical string) |

Booleans (`xsd:boolean`) and dates/timestamps (`xsd:date`, `xsd:dateTime`) are checked first and exempted from the digit rule — a boolean stays a native `bool`, a `dateTime` converts to a native Python `datetime`, and a bare `date` falls back to its lexical string (BSON can't store a bare date). Multiple values for the same predicate become a list.

**A resource-valued object is never swept into an attribute**, regardless of what it looks like — `ex:Eve ex:sibling ex:Cain` (object is an IRI, not a literal) always becomes a hyperedge, per the next section.

### Resource-valued triples → hyperedges

Every triple whose object is an IRI or blank node becomes a `hub` hyperedge: `relation` = the predicate's full expanded IRI, `members` = `[subject (seq 0), object (seq 1)]`.

### OWL axioms → axiom hyperedges recognized by `infer: true`

Three OWL property declarations are recognized by their real, canonical OWL IRI — regardless of what prefix a file happens to bind to the OWL namespace — and mapped onto HypergraphAI's own axiom control vocabulary, so an ontology's own declarations are usable by [Inferencing](help:help-inferencing) immediately on import, exactly like an axiom hand-asserted in a seed file:

| OWL triple | Synthesized axiom hyperedge(s) |
|---|---|
| `<P> a owl:TransitiveProperty` | *(in addition to the ordinary `rdf:type` handling above)* a `hub` edge: relation `owl:transitive`, single member (seq 0) `<P>` |
| `<P> owl:inverseOf <Q>` | A `hub` edge: relation `owl:inverse-of` (HypergraphAI's own hyphenated spelling — never the real predicate's own CURIE `owl:inverseOf`), members `[<P> (seq 0), <Q> (seq 1)]` |
| `<P> a owl:SymmetricProperty` | Two things, together: every *data* triple already using `<P>` gets flavor `symmetric` instead of `hub` (a direct, infer-free translation — a `symmetric` edge already reads both directions unconditionally); **and** a `hub` axiom edge: relation `owl:symmetric`, single member (seq 0) `<P>` — a safety net for `infer: true` if `<P>` is ever also asserted through a `hub`-flavored edge this import never sees |

## Worked examples

### 1. A simple entity with typed attributes

```turtle
@prefix ex: <http://example.com/> .
ex:Eve ex:sex "female" .
ex:Eve ex:rating 12.2 .
```

Produces one hypernode:

```yaml
id: http://example.com/Eve
label: Eve
type: Entity
attributes:
  ex:sex: "female"      # text — not digit-led
  ex:rating: 12.2        # number — digit-led, parses as a float
```

### 2. Mixing an attribute with a relationship

```turtle
@prefix ex: <http://example.com/> .
ex:Eve ex:sex "female" .
ex:Eve ex:sibling ex:Cain .
```

`ex:sex` (a literal object) becomes an attribute on `Eve` as above; `ex:sibling` (a resource object) becomes a `hub` hyperedge instead — it is never treated as an attribute, no matter what the object's own id looks like:

```yaml
relation: http://example.com/sibling
flavor: hub
members:
  - { node_id: http://example.com/Eve, seq: 0 }
  - { node_id: http://example.com/Cain, seq: 1 }
```

### 3. A digit-led value that fails to parse

```turtle
@prefix ex: <http://example.com/> .
ex:Eve ex:code "12.2abc" .
```

`"12.2abc"` starts with a digit, but neither `int()` nor `float()` can parse it — the attribute value falls back to `-1` (a number, not the lexical text) rather than raising or silently keeping the malformed string.

### 4. OWL axioms feeding `infer: true`

```turtle
@prefix ex: <http://example.com/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
ex:sibling a owl:SymmetricProperty .
ex:cain ex:sibling ex:abel .
```

Produces **two** hyperedges:

```yaml
- relation: http://example.com/sibling   # the data fact
  flavor: symmetric
  members: [{node_id: .../cain, seq: 0}, {node_id: .../abel, seq: 1}]
- relation: owl:symmetric                 # the axiom
  flavor: hub
  members: [{node_id: http://example.com/sibling, seq: 0}]
```

Because the data edge is already `symmetric`-flavored, `cain`↔`abel` reads in both directions with no `infer: true` needed. The `owl:symmetric` axiom edge is the safety net: if `ex:sibling` is *also* asserted somewhere else through an ordinary `hub`-flavored edge (e.g. one added by hand later, or from a different import), `infer: true` still recognizes it as symmetric and derives the missing direction — see [Inferencing](help:help-inferencing) for how axiom expansion works.

## Caveats

**Not handled** (documented limitations — not silent data loss; everything below still round-trips as ordinary triples/attributes):

- **RDF Collections** (`rdf:first`/`rdf:rest`/`rdf:nil` list structures) import as plain triples on their blank-node cells, not flattened into a native list attribute or an n-ary hyperedge.
- **JSON-LD named graphs** (`@graph` blocks with multiple graphs) are merged into one triple set — the graph name is dropped. HypergraphAI hyperedges aren't a general quad store; use one import per named graph if you need them kept apart.
- **RDF reification** (`rdf:Statement`/`rdf:subject`/… quadruples describing a triple) round-trips as ordinary triples on the reification node, not as edge-level provenance.
- Other OWL/RDFS axioms (`rdfs:subPropertyOf`, `owl:equivalentClass`, …) are **not** specially recognized — only `owl:TransitiveProperty`, `owl:inverseOf` and `owl:SymmetricProperty` synthesize axiom edges (see Concepts above). Everything else round-trips as ordinary triples/attributes.

**Surprising-but-intentional behavior**, worth knowing before you rely on it:

- **A digit-led value wins even when RDF typed it as a string.** `ex:Eve ex:zip "12345"` (a *quoted* string, `xsd:string`) still becomes the number `12345`, not text — classification is driven by the lexical form, not the declared datatype.
- **A failed numeric parse becomes `-1`, not text.** `"12.2abc"` doesn't fall back to keeping the lexical string; it becomes the number `-1`. If you need to distinguish "genuinely -1" from "failed to parse," don't rely on this value alone — check the source data.
- **A bare `xsd:date` (no time) still becomes text**, not a native date type — BSON can't store a bare `datetime.date`. Only `xsd:dateTime` (with a time component) converts to a native, queryable datetime.
- **Attribute keys never expand**, even though every id in the graph does. A predicate's attribute key stays a sanitized CURIE (`attributes["foaf:age"]`) specifically so SHQL's `attributes: {key: value}` pattern filter keeps working — expanding it to the full IRI would make that filter's MongoDB dot-path query address the wrong nested field. If you don't want the `prefix:` (or, for a native export file, a full-IRI-shaped key) at all, check **Suppress Attribute Prefixes** on the Import window (or pass `strip_attribute_prefixes=true` over REST) — it rewrites every node/edge attribute key to its local name (`ex:sex` → `sex`, `http://example.org/description` → `description`). A key whose local name would collide with another key's in the same document — its own or another's — is left untouched rather than silently merged (e.g. `foaf:name` and `dc:name` both stay prefixed, since both would strip to `name`).
- **A class referenced only by `rdf:type` triples gets no node of its own.** `rdf:type`'s *object* (the class) is folded into the subject's `type`/`attributes.rdf_type` fields, not turned into a hyperedge — so a class with no other use in the file (no `rdfs:label`, no `rdfs:subClassOf`, …) never becomes a disconnected node. A class that *is* also used as an ordinary subject or object elsewhere still gets one.
- **Merge mode never overwrites**, same as a native export import: a node whose id already exists, or an edge whose identity (relation + members + validity window) already exists, is skipped. To replace previously-imported RDF data, delete the graph first or import under a new id.

## Coming from SPARQL?

If you're used to writing SPARQL against this data and reach for `VALUES` to match a field against a list of candidates, SHQL already covers the common case today — no translation layer needed:

- `filter: "?var.field IN [a, b, c]"` in an SHQL query's `where:` list
- `attributes: {field: {$in: [a, b, c]}}` inside a `node:`/`edge:` pattern (raw MongoDB operators pass straight through)

Neither is full SPARQL `VALUES` — SPARQL's version can bind several variables at once per row, and can inject a binding for a variable with no backing pattern at all, which nothing in SHQL does — but for "does this field match one of these values," both of the above already work against RDF-imported attributes and ids exactly as described above (CURIE-keyed attribute names, digit/quote-led value typing, and all). A fuller SPARQL-to-SHQL conversion plan, including translating `VALUES` itself for the general case, is tracked separately in `docs/architecture/sparql-to-shql-conversion-plan.md` and `docs/architecture/sparql-vs-shql-gaps.md`.

## See also

- [Exporting and importing hypergraphs](help:help-export-import) — the shared create/merge mechanics, REST/shell/UI entry points, and the condensed mapping table
- [Inferencing](help:help-inferencing) — how `owl:transitive`/`owl:inverse-of`/`owl:symmetric` axiom edges get used at query time
- [Hyperedges](help:help-hyperedges) and [Edge flavors](help:help-edge-flavors) — what `hub` and `symmetric` mean
- [REST API](help:help-rest-api) — the full `/graphs/import/rdf` endpoint reference
