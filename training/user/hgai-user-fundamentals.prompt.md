## Goal

Please generate a user self-paced training markdown file in './training/user/hgai-user-fundamentals.md' that steps a new user through creating spaces, hypergraphs, hypernodes, hyperedges, and hql and shql queries.

## Directions

Assume:
- user already has access to a running current hgai server and that the user has already logged into the hgai via their browser
- no pre-existing hypergraphs, hypernodes, or hyperedges.  

Directives:
- provide detailed instructions as to how to accomplish each step / task
- provide samples and other pertinent information in 
- please add whatever other tasks or topics/concepts that you feel are relevant for new hgai user fundamentals

## Sections

- Hypergraphs
- Hypernodes
- Hyperedges
- Queries
  - HQL (hypergraph query language)
  - SHQL (semantic hypergraph query language)

### Instruction

Provide information about each section topic with multiple examples from different domains to illustrate the concepts.

## Tasks (in the appropriate own sections) 

Please have the user create a hypergraph with id: 'hg-fun-a' and a hypergraph with id: 'hg-fun-b'

Please use the comedy group The Three Stooges 'group:three-stooges' as the use case for the fundamentals self-pace user course.
- The Three Stooges; 'group:three-stooges'; type: 'Group'

Please have the user create the 5 members of the group as 'Person' type nodes in the 'hg-fun-a' hypergraph:

- Moe Howard; 'person:moe'; valid from: '1897-06-19T12:01AM', valid to: '1975-05-04T11:59PM'; attributes: {"last_name" : "Howard", "first_name" : "Moe"}
- Larry Fine;  'person:larry'; valid from: '1902-10-04T12:01AM', valid to: '1975-01-24T11:59PM'; attributes: {"last_name" : "Fine", "first_name" : "Larry"}
- Shemp Howard; 'person:shemp'; valid from: '1895-03-11T12:01AM', valid to: '1955-11-22T11:59PM'; attributes: {"last_name" : "Howard", "first_name" : "Shemp"}
- Curly Howard; 'person:curly'; valid from: '1903-10-22T12:01AM', valid to: '1952-01-18T11:59PM'; attributes: {"last_name" : "Howard", "first_name" : "Curly"}
- Joe Besser; 'person:curly-joe'; valid from: '1902-10-04T12:01AM', valid to: '1975-01-24T11:59PM'; attributes: {"last_name" : "Besser", "first_name" : "Curly Joe"}
- Joe DeRita; 'person:derita'; valid from: '1907-08-12T12:01AM', valid to: '1988-03-01T11:59PM'; attributes: {"last_name" : "DeRita", "first_name" : "Joe"}

Please have the user create the Three Stooges as a 'Group' type node, id: "group:three-stooges', in the 'hg-fun-b' hypergraph.

Please have the user create various member lineups for the Three Stooges using multiple hyperedges in the 'hg-fun-b' hypergraph to denote the group members (relation: 'rel:member') based on valid from and valid to when each group membership for any point in time for use in 'at' filtered queries.

- relation: 'rel:member'
  flavor: 'hub'
  member[0]: 'group:three-stooges'
  member[1]: 'person:moe'
  member[2]: 'person:shemp'
  member[3]: 'person:larry'
  valid_from: '1922-01-01T12:01AM'
  valid_to: '1932-07-04T11:59PM'

- relation: 'rel:member'
  flavor: 'hub'
  member[0]: 'group:three-stooges'
  member[1]: 'person:moe'
  member[2]: 'person:curly'
  member[3]: 'person:larry'
  valid_from: '1932-07-05T12:01AM'
  valid_to: '1946-07-04T11:59PM'

- relation: 'rel:member'
  flavor: 'hub'
  member[0]: 'group:three-stooges'
  member[1]: 'person:moe'
  member[2]: 'person:shemp'
  member[3]: 'person:larry'
  valid_from: '1946-07-05T12:01AM'
  valid_to: '1956-07-04T11:59PM'

- relation: 'rel:member'
  flavor: 'hub'
  member[0]: 'group:three-stooges'
  member[1]: 'person:moe'
  member[2]: 'person:shemp'
  member[3]: 'person:curly-joe'
  valid_from: '1956-07-05T12:01AM'
  valid_to: '1958-07-04T11:59PM'

- relation: 'rel:member'
  flavor: 'hub'
  member[0]: 'group:three-stooges'
  member[1]: 'person:moe'
  member[2]: 'person:derita'
  member[3]: 'person:larry'
  valid_from: '1958-07-05T12:01AM'
  valid_to: '1970-12-31T11:59PM'

### Simple Queries

#### HQL

Please have the use write an HQL query to return all nodes in the 'hg-fun-a' hypergraph and provide the correct HQL so the user make check their work.

Please have the use write an HQL query to return all nodes in the 'hg-fun-b' hypergraph and provide the correct HQL so the user make check their work.

Please have the use write an HQL query to return all nodes in the 'hg-fun-a' and 'hg-fun-b' hypergraphs and provide the correct HQL so the user make check their work.

#### SHQL

Please have the use write an SHQL query to return all nodes in the 'hg-fun-a' hypergraph and provide the correct SHQL so the user make check their work.

Please have the use write an SHQL query to return all nodes in the 'hg-fun-b' hypergraph and provide the correct SHQL so the user make check their work.

Please have the use write an SHQL query to return all nodes in the 'hg-fun-a' and 'hg-fun-b' hypergraphs and provide the correct SHQL so the user make check their work.

### Matching exact values

#### HQL

HQL query to only return the Person nodes with 'Howard' as their 'last_name' attribute.

#### SHQL

SHQL query to only return the Person nodes with 'Howard' as their 'last_name' attribute.

### Matching partial values

#### HQL

HQL query to only return the Person nodes with 'Cur*'  as the start of their 'first_name' attribute.

#### SHQL

SHQL query to only return the Person nodes with 'Cur*' as the start of their 'first_name' attribute.

### Matching attribute values with regular expressions

#### HQL

HQL query to only return the Person nodes with '.*oe.*'  regex match on their 'first_name' attribute.

#### SHQL

SHQL query to only return the Person nodes with '.*oe.*'  regex match on their 'first_name' attribute.

### List group members

#### HQL

HQL query to return the Person nodes for all hyperedges with relation 'rel:member' and edge type 'hub' and members include 'group:three-stooges'.

#### SHQL

SHQL query to return the Person nodes for all hyperedges with relation 'rel:member' and edge type 'hub' and members include 'group:three-stooges'.

### List group members at point-in-time valid date

#### HQL

HQL query to return the Person nodes for all hyperedges with relation 'rel:member' and edge type 'hub' and members include 'group:three-stooges' at the point-in-time '1924-01-01T12:12:12Z'.

#### SHQL

SHQL query to return the Person nodes for all hyperedges with relation 'rel:member' and edge type 'hub' and members include 'group:three-stooges' at the point-in-time '1924-01-01T12:12:12Z'.

