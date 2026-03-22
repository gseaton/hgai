Please generate a second HypergraphAI YAML-based query language `SHQL` (pronounced: shekel; semantic hypergraph query language)
and HypergraphAI SHQL query engine that is more consistent with SPARQL using pattern matching but in the 
context of hypergraphs, including a new SHQL README documentation section explaining SHQL and 
provide SHQL query examples. Please implement SHQL query support as a module.

---

Please add a 'Query (SHQL)' SHQL query page similar to the 'Query (HQL)' page in style and functionality, but for handling SHQL queries. Please
generate all necessary APIs to support SHQL query handling.  

---

Please fix. When executing the following SHQL query in the UI:

```yaml
shql:
  from: hg-alpha
  where:
    - node: ?person
      node_type: Person
  select:
    - ?person
```

The following error was displayed in Results pane:

SHQL execution error: 'str' object has no attribute 'get'