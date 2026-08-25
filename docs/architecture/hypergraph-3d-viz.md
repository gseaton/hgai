# HypergraphX 3D Visualization


## Hyperedge Visualization

```yaml

id: edge:original-stooges
relation: rel:member
flavor: flavor:hub
label: Original Three Stooges
status: active
valid_from: 01/01/1992, 4:01 PM
valid_to: 07/01/1932, 3:59PM
members:
  - id: group:three-stooges
  - id: person:moe
  - id: person:larry
  - id: person:shemp
```

## 3D Graph visualization

### 3D Graph Elements
- `edge:original-stooges` : NODE
- `hyperedge:members` : NODE (virtual for 3D visualation; should only be 1 per hyperedge)
- `group:three-stooges` : NODE
- `person:moe` : NODE
- `person:larry` : NODE
- `flavor:hub` : EDGE (virtual for 3D visualization)
- `rel:member` : EDGES (virtual; visualizing hyperedge)

### Graphical Representation of Hyperedge
```
                      id=edge:original-stooges (node)
                              |
                           "hyperedge" (virtual edge)
                              |
                              v
                           "members" (virtual node)
                   /------/  |  |  \
                  /         /   \   \
                 /         |      \   \-------------\        
                /          |        \                \
        id=rel:member id=rel:member  id=rel:member   id=rel:member
           |               |              |               |
           v               v              v               v
id=group:three-stooges  id=person:moe   id=person:larry  id:person:shemp
```
