-- Comparison query for the HypergraphAI business briefing.
--
-- "Who's requesting what MEDEVAC support, for which patients, tasked to
-- which asset, right now?" -- against specops-sql-comparison.sql's
-- schema.
--
-- Four joins (including a bridge table just to reassemble the
-- variable-length patient list), a GROUP_CONCAT to collapse that bridge
-- join back into one row per request, and a temporal condition that has
-- to be hand-written correctly here and in every other query that ever
-- needs "current as of now" against this table.

SELECT
    e.element_name,
    l.location_name,
    a.asset_callsign,
    GROUP_CONCAT(p.full_name SEPARATOR ', ') AS patients,
    mr.precedence
FROM medevac_request mr
JOIN element e                    ON e.element_id = mr.element_id
JOIN location l                   ON l.location_id = mr.location_id
JOIN evac_asset a                 ON a.asset_id = mr.asset_id
JOIN medevac_request_patient mrp  ON mrp.request_id = mr.request_id
JOIN person p                     ON p.patient_id = mrp.patient_id
WHERE l.location_id = 'loc_pz_bravo'
  AND CURRENT_TIMESTAMP BETWEEN mr.valid_from AND mr.valid_to
GROUP BY mr.request_id, e.element_name, l.location_name, a.asset_callsign, mr.precedence;

-- To answer "what did the request look like BEFORE the reassessment" (the
-- point-in-time question q02/q03 answer in one line each via HQL's
-- "at:"), replace CURRENT_TIMESTAMP above with a literal timestamp -- and
-- remember to make that same substitution correctly in every other
-- report/query in the codebase that touches this table.
