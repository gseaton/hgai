/**
 * HypergraphAI API Client
 * Handles all communication with the HypergraphAI REST API.
 */

const HGAI_API = (() => {
  const BASE = '/api/v1';
  let _token = null;
  let _username = null;
  let _roles = [];

  function getToken() { return _token || sessionStorage.getItem('hgai_token'); }
  function getUsername() { return _username || sessionStorage.getItem('hgai_username'); }
  function getRoles() {
    const r = _roles.length ? _roles : JSON.parse(sessionStorage.getItem('hgai_roles') || '[]');
    return r;
  }
  function isAdmin() { return getRoles().includes('admin'); }

  function setSession(token, username, roles) {
    _token = token; _username = username; _roles = roles;
    sessionStorage.setItem('hgai_token', token);
    sessionStorage.setItem('hgai_username', username);
    sessionStorage.setItem('hgai_roles', JSON.stringify(roles));
  }

  function clearSession() {
    _token = null; _username = null; _roles = [];
    sessionStorage.removeItem('hgai_token');
    sessionStorage.removeItem('hgai_username');
    sessionStorage.removeItem('hgai_roles');
  }

  async function request(method, path, body = null, params = {}) {
    const url = new URL(BASE + path, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
    });

    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const opts = { method, headers };
    if (body !== null) opts.body = JSON.stringify(body);

    const resp = await fetch(url.toString(), opts);

    if (resp.status === 401) {
      clearSession();
      window.dispatchEvent(new Event('hgai:unauthorized'));
      throw new Error('Unauthorized');
    }

    if (resp.status === 204) return null;

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const msg = data.detail || data.message || `HTTP ${resp.status}`;
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  }

  // ── Auth ──────────────────────────────────────────────────────────────────
  async function login(username, password) {
    const form = new URLSearchParams({ username, password, grant_type: 'password' });
    const resp = await fetch(`${BASE}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    const data = await resp.json();
    setSession(data.access_token, data.username, data.roles);
    return data;
  }

  async function getMe() { return request('GET', '/auth/me'); }

  // ── Server ────────────────────────────────────────────────────────────────
  async function getServerInfo() { return request('GET', '/server/info'); }

  // ── Hypergraphs ───────────────────────────────────────────────────────────
  async function listGraphs(params = {}) { return request('GET', '/graphs', null, params); }
  async function getGraph(id) { return request('GET', `/graphs/${id}`); }
  async function createGraph(data) { return request('POST', '/graphs', data); }
  async function updateGraph(id, data) { return request('PUT', `/graphs/${id}`, data); }
  async function deleteGraph(id) { return request('DELETE', `/graphs/${id}`); }
  async function getGraphStats(id) { return request('GET', `/graphs/${id}/stats`); }
  async function exportGraph(id) { return request('POST', `/graphs/${id}/export`); }
  async function importGraph(id, data) { return request('POST', `/graphs/${id}/import`, data); }

  // ── Hypernodes ────────────────────────────────────────────────────────────
  async function listNodes(graphId, params = {}) { return request('GET', `/graphs/${graphId}/nodes`, null, params); }
  async function getNode(graphId, nodeId) { return request('GET', `/graphs/${graphId}/nodes/${nodeId}`); }
  async function createNode(graphId, data) { return request('POST', `/graphs/${graphId}/nodes`, data); }
  async function updateNode(graphId, nodeId, data) { return request('PUT', `/graphs/${graphId}/nodes/${nodeId}`, data); }
  async function deleteNode(graphId, nodeId) { return request('DELETE', `/graphs/${graphId}/nodes/${nodeId}`); }

  // ── Hyperedges ────────────────────────────────────────────────────────────
  async function listEdges(graphId, params = {}) { return request('GET', `/graphs/${graphId}/edges`, null, params); }
  async function getEdge(graphId, edgeId) { return request('GET', `/graphs/${graphId}/edges/${edgeId}`); }
  async function createEdge(graphId, data) { return request('POST', `/graphs/${graphId}/edges`, data); }
  async function updateEdge(graphId, edgeId, data) { return request('PUT', `/graphs/${graphId}/edges/${edgeId}`, data); }
  async function deleteEdge(graphId, edgeId) { return request('DELETE', `/graphs/${graphId}/edges/${edgeId}`); }

  // ── Query ─────────────────────────────────────────────────────────────────
  async function runQuery(hql, useCache = true) {
    return request('POST', '/query', { hql, use_cache: useCache });
  }
  async function validateQuery(hql) { return request('POST', '/query/validate', { hql }); }
  async function flushCache(graphId = null) {
    return request('POST', '/query/cache/invalidate', null, graphId ? { graph_id: graphId } : {});
  }

  // ── Accounts ──────────────────────────────────────────────────────────────
  async function listAccounts(params = {}) { return request('GET', '/accounts', null, params); }
  async function getAccount(username) { return request('GET', `/accounts/${username}`); }
  async function createAccount(data) { return request('POST', '/accounts', data); }
  async function updateAccount(username, data) { return request('PUT', `/accounts/${username}`, data); }
  async function deleteAccount(username) { return request('DELETE', `/accounts/${username}`); }

  // ── Meshes ────────────────────────────────────────────────────────────────
  async function listMeshes(params = {}) { return request('GET', '/meshes', null, params); }
  async function getMesh(id) { return request('GET', `/meshes/${id}`); }
  async function createMesh(data) { return request('POST', '/meshes', data); }
  async function updateMesh(id, data) { return request('PUT', `/meshes/${id}`, data); }
  async function deleteMesh(id) { return request('DELETE', `/meshes/${id}`); }

  return {
    // session
    getToken, getUsername, getRoles, isAdmin, setSession, clearSession,
    // auth
    login, getMe,
    // server
    getServerInfo,
    // graphs
    listGraphs, getGraph, createGraph, updateGraph, deleteGraph, getGraphStats, exportGraph, importGraph,
    // nodes
    listNodes, getNode, createNode, updateNode, deleteNode,
    // edges
    listEdges, getEdge, createEdge, updateEdge, deleteEdge,
    // query
    runQuery, validateQuery, flushCache,
    // accounts
    listAccounts, getAccount, createAccount, updateAccount, deleteAccount,
    // meshes
    listMeshes, getMesh, createMesh, updateMesh, deleteMesh,
  };
})();
