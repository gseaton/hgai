# Prompt

Turn 1: Please add support of importing RDF Turtle Triple Language (.ttl), RDF/XML (.rdf, .xml), JSON-LD (.jsonld) , and Notation 3 (.n3) files to a hypergraph.

---

Turn 2: Please add support of importing RDF Turtle Triple Language (.ttl), RDF/XML (.rdf, .xml), JSON-LD (.jsonld) , and Notation 3 (.n3) files to a hypergraph with the approprivate mappings into hyperedges and hypernodes.

---

Turn 3: Please add support of importing RDF Turtle Triple Language (.ttl), RDF/XML (.rdf, .xml), JSON-LD (.jsonld) , and Notation 3 (.n3) files to a hypergraph with the appropriate mappings into hyperedges and hypernodes. If an RDF triple Object is a data literal, those should be converted / mapped to an attribute on the Subject hypernode. RDF triples should be translated as a 'hub' hyperedge with relation being the RDF triple Predicate, the Subject the primary (0) member, and the Object (if it's not a data literal and is a resource reference) should be the second (0) member.
