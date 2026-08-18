# q01 — every staffing fact ever recorded for TO-047, no point-in-time
# filter. Returns all 3 (Maria v1, Maria v2, Devon v1) — nothing is hidden
# by default, matching docs/decks/demo-alpha's PIT convention.
hql:
  from: defense-bd-demo
  match:
    type: hyperedge
    relation: staffed-on
  where:
    members:
      node_id: taskorder:to-047
  return:
    - id
    - members
    - attributes
    - valid_from
    - valid_to
  as: to047_staffing_all_versions
