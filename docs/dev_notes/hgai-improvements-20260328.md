# hgai improvements

## MCP Services
- narrative queries converted to hql/shql

## Edge Hydration
- on get edge, allow for hydration levels
  - allow for hyrdation levels
  - populating member entities
  - recursive population of edge member entities
  - if hydration level is 1, populate first level members
  - if hydration level is 2, populate first level node members, and second level edge members
  - if hydration level is n, populate to the node member leaves up to n, and n level edge members 
