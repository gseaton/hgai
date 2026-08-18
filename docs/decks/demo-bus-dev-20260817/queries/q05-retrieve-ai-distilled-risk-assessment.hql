# q05 — retrieve the AI agent's distilled staffing-risk conclusion. The
# expensive step (an agent reasoning over the roster + LCAT history above)
# already happened once and was captured as a normal hyperedge; this
# query costs nothing and can be run by a different agent, a different
# session, or a human analyst, at any point in the future.
hql:
  from: defense-bd-demo
  match:
    type: hyperedge
    relation: risk-assessment
  where:
    tags:
      $in: ["ai-generated"]
  return:
    - id
    - members
    - attributes
  as: ai_generated_risk_assessments
