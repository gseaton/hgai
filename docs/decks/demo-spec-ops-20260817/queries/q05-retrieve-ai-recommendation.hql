# q05 — retrieve the AI agent's distilled recommendation. The expensive
# step (an agent fusing the upgraded request with the independent ISR
# confirmation) already happened once and was captured as a normal
# hyperedge; this query costs nothing and can be run by a different
# agent, a different watch shift, or a human controller, at any point
# after the fact. The recommendation is decision support for a human —
# note it does not trigger any action by itself.
hql:
  from: defense-bd-demo-specops
  match:
    type: hyperedge
    relation: recommendation
  where:
    tags:
      $in: ["ai-generated"]
  return:
    - id
    - members
    - attributes
  as: ai_generated_recommendations
