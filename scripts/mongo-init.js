// HypergraphAI MongoDB Cold-Start Initialization Script
// This script runs automatically when MongoDB container starts for the first time.
// It creates the hgai database, collections, indexes, and the application admin account.
//
// MongoDB admin credentials: admin / pwd357
// Application admin account: admin / pwd357 (bcrypt hashed below)

// ─── Switch to hgai database ──────────────────────────────────────────────────
db = db.getSiblingDB('hgai');

// ─── Create hgai database user ────────────────────────────────────────────────
db.createUser({
  user: 'hgai_app',
  pwd: 'hgai_app_pwd357',
  roles: [
    { role: 'readWrite', db: 'hgai' },
    { role: 'dbAdmin', db: 'hgai' }
  ]
});

// ─── Create collections ───────────────────────────────────────────────────────
db.createCollection('hypergraphs');
db.createCollection('hypernodes');
db.createCollection('hyperedges');
db.createCollection('accounts');
db.createCollection('meshes');
db.createCollection('query_cache');
db.createCollection('audit_log');

// ─── Indexes: hypergraphs ─────────────────────────────────────────────────────
db.hypergraphs.createIndex({ "id": 1 }, { unique: true, name: "idx_graphs_id" });
db.hypergraphs.createIndex({ "status": 1 }, { name: "idx_graphs_status" });
db.hypergraphs.createIndex({ "tags": 1 }, { name: "idx_graphs_tags" });
db.hypergraphs.createIndex({ "type": 1 }, { name: "idx_graphs_type" });
db.hypergraphs.createIndex({ "system_created": -1 }, { name: "idx_graphs_created" });

// ─── Indexes: hypernodes ──────────────────────────────────────────────────────
db.hypernodes.createIndex({ "id": 1, "hypergraph_id": 1 }, { unique: true, name: "idx_nodes_id_graph" });
db.hypernodes.createIndex({ "hypergraph_id": 1 }, { name: "idx_nodes_graph" });
db.hypernodes.createIndex({ "type": 1 }, { name: "idx_nodes_type" });
db.hypernodes.createIndex({ "status": 1 }, { name: "idx_nodes_status" });
db.hypernodes.createIndex({ "tags": 1 }, { name: "idx_nodes_tags" });
db.hypernodes.createIndex({ "label": 1 }, { name: "idx_nodes_label" });
db.hypernodes.createIndex({ "valid_from": 1 }, { name: "idx_nodes_valid_from" });
db.hypernodes.createIndex({ "valid_to": 1 }, { name: "idx_nodes_valid_to" });
db.hypernodes.createIndex({ "system_created": -1 }, { name: "idx_nodes_created" });
// Compound: graph + status (common query pattern)
db.hypernodes.createIndex({ "hypergraph_id": 1, "status": 1 }, { name: "idx_nodes_graph_status" });

// ─── Indexes: hyperedges ──────────────────────────────────────────────────────
db.hyperedges.createIndex({ "id": 1, "hypergraph_id": 1 }, { unique: true, name: "idx_edges_id_graph" });
db.hyperedges.createIndex({ "hyperkey": 1 }, { name: "idx_edges_hyperkey" });
db.hyperedges.createIndex({ "hypergraph_id": 1 }, { name: "idx_edges_graph" });
db.hyperedges.createIndex({ "relation": 1 }, { name: "idx_edges_relation" });
db.hyperedges.createIndex({ "flavor": 1 }, { name: "idx_edges_flavor" });
db.hyperedges.createIndex({ "status": 1 }, { name: "idx_edges_status" });
db.hyperedges.createIndex({ "tags": 1 }, { name: "idx_edges_tags" });
db.hyperedges.createIndex({ "members.node_id": 1 }, { name: "idx_edges_member_nodes" });
db.hyperedges.createIndex({ "valid_from": 1 }, { name: "idx_edges_valid_from" });
db.hyperedges.createIndex({ "valid_to": 1 }, { name: "idx_edges_valid_to" });
db.hyperedges.createIndex({ "system_created": -1 }, { name: "idx_edges_created" });
// Compound: graph + relation (most common query pattern)
db.hyperedges.createIndex({ "hypergraph_id": 1, "relation": 1 }, { name: "idx_edges_graph_relation" });
db.hyperedges.createIndex({ "hypergraph_id": 1, "status": 1 }, { name: "idx_edges_graph_status" });

// ─── Indexes: accounts ────────────────────────────────────────────────────────
db.accounts.createIndex({ "username": 1 }, { unique: true, name: "idx_accounts_username" });
db.accounts.createIndex({ "email": 1 }, { unique: true, sparse: true, name: "idx_accounts_email" });
db.accounts.createIndex({ "roles": 1 }, { name: "idx_accounts_roles" });
db.accounts.createIndex({ "status": 1 }, { name: "idx_accounts_status" });

// ─── Indexes: meshes ──────────────────────────────────────────────────────────
db.meshes.createIndex({ "id": 1 }, { unique: true, name: "idx_meshes_id" });
db.meshes.createIndex({ "status": 1 }, { name: "idx_meshes_status" });

// ─── Indexes: query_cache ─────────────────────────────────────────────────────
db.query_cache.createIndex({ "cache_key": 1 }, { unique: true, name: "idx_cache_key" });
db.query_cache.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0, name: "idx_cache_ttl" });

// ─── Indexes: audit_log ───────────────────────────────────────────────────────
db.audit_log.createIndex({ "timestamp": -1 }, { name: "idx_audit_timestamp" });
db.audit_log.createIndex({ "username": 1 }, { name: "idx_audit_username" });
db.audit_log.createIndex({ "action": 1 }, { name: "idx_audit_action" });

// ─── Bootstrap: system hypergraph ────────────────────────────────────────────
// The system configuration is stored as a hypergraph (per design tenets)
var now = new Date();
db.hypergraphs.insertOne({
  id: "hgai-system",
  label: "HypergraphAI System",
  description: "Internal system configuration hypergraph",
  type: "instantiated",
  composition: [],
  attributes: { system: true },
  tags: ["system", "internal"],
  status: "active",
  system_created: now,
  system_updated: now,
  created_by: "system",
  version: 1
});

// ─── Bootstrap: admin account ─────────────────────────────────────────────────
// The admin account is created by the Python application on first startup via
// bootstrap_admin() using passlib/bcrypt to correctly hash the password.
// HGAI_ADMIN_USERNAME / HGAI_ADMIN_PASSWORD env vars control the credentials
// (defaults: admin / pwd357).

// ─── Bootstrap: hello-world hypergraph (placeholder) ─────────────────────────
db.hypergraphs.insertOne({
  id: "hello-world",
  label: "Hello, World!",
  description: "A simple example hypergraph demonstrating HypergraphAI concepts",
  type: "instantiated",
  composition: [],
  attributes: { example: true },
  tags: ["example", "demo"],
  status: "active",
  system_created: now,
  system_updated: now,
  created_by: "admin",
  version: 1
});

print("HypergraphAI MongoDB initialization complete.");
print("  Database: hgai");
print("  Collections: hypergraphs, hypernodes, hyperedges, accounts, meshes, query_cache, audit_log");
print("  Admin account: admin / pwd357");
print("  IMPORTANT: Change the admin password after first login!");
