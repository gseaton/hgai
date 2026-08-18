-- Comparison query for the HypergraphAI business briefing.
--
-- "Who is CURRENTLY staffed on TO-047, in what labor category, and who's
-- their manager?" -- against staffing-sql-comparison.sql's schema.
--
-- Three joins, plus a temporal condition that has to be hand-written
-- correctly here and in every other query that ever needs "current as of
-- now" against this table -- nothing in the schema enforces it.

SELECT
    p.full_name   AS person,
    lc.lcat_name  AS labor_category,
    mgr.full_name AS manager
FROM staffing_assignment sa
JOIN person p           ON p.person_id = sa.person_id
JOIN labor_category lc  ON lc.lcat_id = sa.lcat_id
LEFT JOIN reports_to rt ON rt.person_id = p.person_id
LEFT JOIN person mgr    ON mgr.person_id = rt.manager_id
WHERE sa.task_order_id = 'TO-047'
  AND CURRENT_TIMESTAMP BETWEEN sa.valid_from AND sa.valid_to;

-- To answer "what did the roster look like on 1 January 2025 instead of
-- right now" (the point-in-time question q02/q03 answer in one line each
-- via HQL's "at:"), replace CURRENT_TIMESTAMP above with a literal
-- timestamp -- and remember to make that same substitution correctly in
-- every other report/query in the codebase that touches this table.
