# Prompt

Please during RDF import, convert OWL symmetric properties to HypergraphAI symmetic hyperedges (e.g. ex:sibling a owl:SymmetricProperty, ex:cain ex:sibling ex:abel -> 2 hyperedges: flavor of 'symmetric', relation of 'ex:sibling', prime member (0) ex:cain, and second member (1) ex:abel (fully prefix expanded to HypergraphAI reference); flavor of 'hub', relation of 'owl:symmetric' and prime member (0) of 'ex:sibling' (fully prefix expanded to HypergraphAI reference).
