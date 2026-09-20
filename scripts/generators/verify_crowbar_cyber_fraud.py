#!/usr/bin/env python3
"""
Post-load verification of a hypergraph produced by crowbar_cyber_fraud.py.

    python scripts/generators/verify_crowbar_cyber_fraud.py GRAPH_ID [--db hgai] [--port 8357] [--source ~/Downloads/crowbar] [--out verify.json]

Checks (all read-only):
  * hypergraph node_count / edge_count equal the stored documents;
  * every hypernode and hyperedge (and the graph) carries attributes.provenance;
  * referential integrity: every hyperedge member is a hypernode or hyperedge of the graph;
  * hypernodes that are a member of no hyperedge, by type;
  * 1,000 randomly sampled rows of each transaction CSV are compared (properties, source_row, and
    the hub hyperedges that carry the row's relationships) with what was stored;
  * ontology behaviour through the live API (transitive closure / path, inverse-of, symmetric,
    skos:broaderTransitive chain) and a few SHQL queries.
"""
import argparse
import csv
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pymongo import MongoClient  # noqa: E402

from hgai.config import get_settings  # noqa: E402

SAMPLE = 1000
SEED = 20260920


def num(t):
    f = float(t)
    return int(f) if f == int(f) and re.fullmatch(r"-?\d+(\.0+)?", t) else f


def flag(t):
    return float(t) != 0


def sample_rows(path, n, total, rng):
    picks = set(rng.sample(range(2, total + 2), n))
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for i, r in enumerate(csv.DictReader(fh), start=2):
            if i in picks:
                out[i] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graph_id")
    ap.add_argument("--db", default=None)
    ap.add_argument("--port", default="8357")
    ap.add_argument("--source", default=str(Path.home() / "Downloads" / "crowbar"))
    ap.add_argument("--out", default="verify.json")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default="pwd357")
    a = ap.parse_args()
    G = a.graph_id
    rng = random.Random(SEED)
    settings = get_settings()
    db = MongoClient(settings.mongo_uri)[a.db or settings.mongo_db]
    D = Path(a.source)
    res = {"graph_id": G, "checks": {}}
    t0 = time.time()

    g = db.hypergraphs.find_one({"id": G}, {"_id": 0})
    n_nodes = db.hypernodes.count_documents({"hypergraph_id": G})
    n_edges = db.hyperedges.count_documents({"hypergraph_id": G})
    res["checks"]["counts_match_graph_document"] = {"graph.node_count": g["node_count"], "graph.edge_count": g["edge_count"], "counted_nodes": n_nodes,
                                                    "counted_edges": n_edges, "ok": (g["node_count"], g["edge_count"]) == (n_nodes, n_edges)}
    res["checks"]["missing_provenance"] = {
        "hypernodes": db.hypernodes.count_documents({"hypergraph_id": G, "attributes.provenance": {"$exists": False}}),
        "hyperedges": db.hyperedges.count_documents({"hypergraph_id": G, "attributes.provenance": {"$exists": False}}),
        "graph": "provenance" not in g["attributes"]}

    node_ids = {d["id"]: d["type"] for d in db.hypernodes.find({"hypergraph_id": G}, {"id": 1, "type": 1, "_id": 0}, batch_size=50000)}
    edge_ids = {d["id"] for d in db.hyperedges.find({"hypergraph_id": G}, {"id": 1, "_id": 0}, batch_size=50000)}
    dangling, slots, member_ids = set(), 0, set()
    for e in db.hyperedges.find({"hypergraph_id": G}, {"members.node_id": 1, "_id": 0}, batch_size=50000):
        for m in e["members"]:
            slots += 1
            member_ids.add(m["node_id"])
            if m["node_id"] not in node_ids and m["node_id"] not in edge_ids:
                dangling.add(m["node_id"])
    res["checks"]["referential_integrity"] = {"member_slots_checked": slots, "distinct_hypernodes": len(node_ids), "distinct_hyperedges": len(edge_ids),
                                              "dangling_member_ids": len(dangling), "dangling_sample": sorted(dangling)[:5]}
    unlinked = {}
    for nid, typ in node_ids.items():
        if nid not in member_ids:
            unlinked[typ] = unlinked.get(typ, 0) + 1
    res["checks"]["hypernodes_not_in_any_hyperedge_by_type"] = unlinked

    def hub_of(rel, tid):
        e = db.hyperedges.find_one({"hypergraph_id": G, "relation": rel, "members.node_id": tid}, {"members": 1})
        return e["members"][0]["node_id"] if e else None

    fd = sample_rows(D / "fraud-detection/transactions.csv", SAMPLE, 1_000_000, rng)
    bad = 0
    for row, r in fd.items():
        tid = "txn:fd:" + r["transaction_id"]
        n = db.hypernodes.find_one({"hypergraph_id": G, "id": tid})
        at = n["attributes"]
        exp = {"amount": num(r["amount"]), "timestamp": r["timestamp"].replace(" ", "T"), "is_fraud": flag(r["is_fraud"]), "ip_risk_score": num(r["ip_risk_score"]),
               "card_present": flag(r["card_present"]), "mcc_code": r["mcc_code"], "velocity_1h": num(r["velocity_1h"])}
        ok = all(at[k] == v for k, v in exp.items()) and at["provenance"]["source_row"] == row and at["provenance"]["source_record_id"] == r["transaction_id"]
        ok = ok and hub_of("rel:initiated", tid) == "acct:" + r["account_id"]
        cat = db.hyperedges.find_one({"hypergraph_id": G, "relation": "rel:categorizes-transaction", "members.node_id": tid, "id": {"$regex": "^edge:categorizes-transaction:fd:mcat:"}}, {"members": 1})
        ok = ok and cat is not None and cat["members"][0]["node_id"] == "mcat:" + r["merchant_category"].replace("_", "-")
        bad += not ok
    res["checks"]["fraud_detection_transaction_sample"] = {"rows_sampled": len(fd), "mismatches": bad}

    sb = sample_rows(D / "synthetic-banking-txns/fraud-detection-dataset.csv", SAMPLE, 1_000_000, rng)
    bad = 0
    for row, r in sb.items():
        tid = "txn:sb:" + r["transaction_id"]
        at = db.hypernodes.find_one({"hypergraph_id": G, "id": tid})["attributes"]
        ok = (at["amount"] == num(r["amount"]) and at["timestamp"] == r["timestamp"] and at["is_fraud"] == flag(r["is_fraud"])
              and at["provenance"]["source_row"] == row and at["merchant_latitude"] == num(r["merchant_latitude"]))
        for rel, hub in (("rel:initiated", "cust:" + r["customer_id"]), ("rel:charged-card", "card:" + r["card_id"]), ("rel:originated-device", "dev:" + r["device_id"]),
                         ("rel:originated-ip", "ip:" + r["ip_address"].replace(".", "-")), ("rel:received-transaction", "merch:" + r["merchant_id"])):
            ok = ok and hub_of(rel, tid) == hub
        bad += not ok
    res["checks"]["synthetic_banking_transaction_sample"] = {"rows_sampled": len(sb), "mismatches": bad}

    def call(method, path, body=None, token=None, form=None):
        headers, data = {}, None
        if form:
            data = urllib.parse.urlencode(form).encode()
        elif body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(f"http://localhost:{a.port}/api/v1" + path, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.load(resp)

    token = call("POST", "/auth/token", form={"username": a.user, "password": a.password})["access_token"]
    tr = lambda body: call("POST", f"/graphs/{G}/infer/transitive", body, token)["result"]
    ex = lambda edge_id: call("POST", f"/graphs/{G}/infer/expand", {"edge_id": edge_id}, token)["inferred"]
    api = {
        "transitive_contains_world_to_city": tr({"relation": "rel:contains", "start_id": "region:world", "end_id": "city:aaronberg-es", "mode": "path"}),
        "skos_broader_closure_pharmacy": tr({"relation": "skos:broader", "start_id": "mcat:pharmacy", "mode": "closure"}),
        "skos_broader_closure_card_testing": tr({"relation": "skos:broader", "start_id": "fraud:card-testing", "mode": "closure"}),
        "skos_narrower_closure_fraud": sorted(tr({"relation": "skos:narrower", "start_id": "fraud:fraud", "mode": "closure"})),
        "subclass_closure_account": tr({"relation": "rel:subclass-of", "start_id": "class:Account", "mode": "closure"}),
        "expand_symmetric_link_broaderTransitive_chain": [(i["relation"], i["_axiom"]) for i in ex("edge:link:phone:ACC0017803--ACC0040032")],
        "expand_initiated_inverse": [(i["relation"], i["members"][0]["node_id"], i["members"][1]["node_id"], i["_axiom"]) for i in ex("edge:initiated:fd:acct:ACC0016173~1")],
        "expand_exactMatch": [(i["relation"], i["_axiom"]) for i in ex("edge:match:mcat-restaurant--mcat-restaurants")],
    }
    res["checks"]["ontology_inference_api"] = api

    def q(shql):
        t = time.time()
        r = call("POST", "/shql/query", {"shql": shql, "use_cache": False}, token)
        return {"count": r.get("count"), "items": r.get("items", [])[:5], "seconds": round(time.time() - t, 2), "meta": {"groups": r.get("meta", {}).get("groups")}}

    res["checks"]["shql_queries"] = {
        "accounts_in_ring_RING0001": q(f"shql:\n  from: {G}\n  where:\n    - edge:\n        relation: rel:has-ring-member\n        members:\n          - node_id: ring:RING0001\n            seq: 0\n          - node_id: ?acct_id\n    - node:\n        bind: ?acct\n        id: ?acct_id\n  select:\n    - ?acct.id\n    - ?acct.attributes.is_fraudster\n    - ?acct.attributes.risk_score\n  limit: 5\n"),
        "customers_sharing_a_card": q(f"shql:\n  from: {G}\n  limit: 3\n  where:\n    - edge:\n        bind: ?e\n        relation: rel:shares-card-with\n  select:\n    - ?e.label\n    - ?e.members\n"),
        "edges_by_relation": q(f"shql:\n  from: {G}\n  select:\n    - ?e.relation\n  where:\n    - edge:\n        bind: ?e\n        tags: [axiom]\n  aggregate:\n    count: true\n    group_by: e.relation\n"),
        "fraud_typology_leaves": q(f"shql:\n  from: {G}\n  where:\n    - node:\n        bind: ?f\n        type: FraudPattern\n        attributes:\n          concept_role: leaf\n  select:\n    - ?f.id\n    - ?f.attributes.datasets\n"),
    }
    res["verification_seconds"] = round(time.time() - t0, 1)
    Path(a.out).write_text(json.dumps(res, indent=2, default=str))
    c = res["checks"]
    print(json.dumps({"counts_ok": c["counts_match_graph_document"]["ok"], "missing_provenance": c["missing_provenance"],
                      "dangling": c["referential_integrity"]["dangling_member_ids"], "unlinked": unlinked,
                      "fd_sample_mismatches": c["fraud_detection_transaction_sample"]["mismatches"], "sb_sample_mismatches": c["synthetic_banking_transaction_sample"]["mismatches"],
                      "seconds": res["verification_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
