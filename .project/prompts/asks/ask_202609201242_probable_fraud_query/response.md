# Response Summary

## Question / Intent
Produce an SHQL query, limited to 20 rows, that finds *probable* fraud transactions — transactions that look like fraud from their risk signals — in the generated `alchemy-cyber-fraud-generated-20260920190053` hypergraph.

## Answer / Recommendation
Two queries over the fraud-detection transactions (tag `fraud-detection`, the only dataset with risk-signal columns), both run against the live graph and returning 20 rows:

1. **Risk-signal query** (5 s): `type: Transaction`, `tags: [fraud-detection]`, attributes `ip_risk_score >= 70`, `velocity_1h >= 4`, `amount_vs_avg_ratio >= 3`; selects the id, timestamp, amount, the three signals, `card_present`, `device_known`, `has_2fa` and the `is_fraud` label; `order_by` ip_risk_score desc then amount_vs_avg_ratio desc; `limit: 20`.
2. **Same rule plus `is_fraud: false`** (9 s): probable fraud that is *not yet labeled* — the analyst's review queue.

Thresholds were calibrated on the data: labeled-fraud transactions average ip risk 55 vs 21, 1-hour velocity 4.0 vs 1.0 and amount-to-average ratio 13 vs 3 for legitimate ones. The rule selects 944 transactions of which 908 (96%) carry the fraud label, leaving 36 unlabeled probable cases.

## Key Points
- Node-pattern `attributes` accept MongoDB operators (`{ $gte: 70 }`), so no `filter:` expression is needed.
- A first, stricter rule (ip ≥ 80, velocity ≥ 5, ratio ≥ 5, no device, no 2FA, card not present, unlabeled) returned 0 rows and took 23 s; adding `tags: [fraud-detection]` uses the tag index and cut the run time.
- The synthetic-banking dataset has no risk-score columns, so its "probable" signals would be structural (shared cards/devices/IPs via `rel:shares-*-with`); not included.
- Whole-graph SHQL without `infer` is fine at this size; results depend on `order_by` over all matches, which is why the rule is selective.

## Context
Graph and attribute names come from the generation run (transaction properties stored in `attributes`; provenance under `attributes.provenance`).
