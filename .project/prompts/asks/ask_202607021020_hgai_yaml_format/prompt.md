# Prompt

Please suggest a YAML-based format (that can be reproduced easily in JSON) to represent hypernodes and hyperedges given the HypergraphAI semantic knowledge hypergraph approach.  Please reference the RDF TTL for terseness ideas but enforce the YAML format.  Properties and attributes of hypernodes (e.g. last_name, dob, enabled, etc) are NOT represented as hyperedges.  Hyperedges ONLY relate hypernodes to hypernodes.  Hyperedges are representated as a special type of hypernode. Please ask me 3-4 questions to clarify the ask.

---

**Clarifying question answers:**

- Primary authoring context: Both equally (human authoring AND machine exchange)
- Hyperedge-as-hypernode structure: Node type drives it — special reserved type (e.g. type: Rel) activates edge semantics
- Prefix/namespace support: Optional — prefixes allowed but not required
- File scope: Just nodes/edges with no graph declaration (graph assignment at import time)
