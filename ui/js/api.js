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
  // Space-scoped variants
  async function listSpaceNodes(spaceId, graphId, params = {}) { return request('GET', `/spaces/${spaceId}/graphs/${graphId}/nodes`, null, params); }
  async function getSpaceNode(spaceId, graphId, nodeId) { return request('GET', `/spaces/${spaceId}/graphs/${graphId}/nodes/${nodeId}`); }
  async function createSpaceNode(spaceId, graphId, data) { return request('POST', `/spaces/${spaceId}/graphs/${graphId}/nodes`, data); }
  async function updateSpaceNode(spaceId, graphId, nodeId, data) { return request('PUT', `/spaces/${spaceId}/graphs/${graphId}/nodes/${nodeId}`, data); }
  async function deleteSpaceNode(spaceId, graphId, nodeId) { return request('DELETE', `/spaces/${spaceId}/graphs/${graphId}/nodes/${nodeId}`); }

  // ── Hyperedges ────────────────────────────────────────────────────────────
  async function listEdges(graphId, params = {}) { return request('GET', `/graphs/${graphId}/edges`, null, params); }
  async function getEdge(graphId, edgeId) { return request('GET', `/graphs/${graphId}/edges/${edgeId}`); }
  async function createEdge(graphId, data) { return request('POST', `/graphs/${graphId}/edges`, data); }
  async function updateEdge(graphId, edgeId, data) { return request('PUT', `/graphs/${graphId}/edges/${edgeId}`, data); }
  async function deleteEdge(graphId, edgeId) { return request('DELETE', `/graphs/${graphId}/edges/${edgeId}`); }
  // Space-scoped variants
  async function listSpaceEdges(spaceId, graphId, params = {}) { return request('GET', `/spaces/${spaceId}/graphs/${graphId}/edges`, null, params); }
  async function getSpaceEdge(spaceId, graphId, edgeId) { return request('GET', `/spaces/${spaceId}/graphs/${graphId}/edges/${edgeId}`); }
  async function createSpaceEdge(spaceId, graphId, data) { return request('POST', `/spaces/${spaceId}/graphs/${graphId}/edges`, data); }
  async function updateSpaceEdge(spaceId, graphId, edgeId, data) { return request('PUT', `/spaces/${spaceId}/graphs/${graphId}/edges/${edgeId}`, data); }
  async function deleteSpaceEdge(spaceId, graphId, edgeId) { return request('DELETE', `/spaces/${spaceId}/graphs/${graphId}/edges/${edgeId}`); }

  // ── Inference ─────────────────────────────────────────────────────────────
  async function projectInference(targetGraphId, data) { return request('POST', `/graphs/${targetGraphId}/infer/project`, data); }

  // ── Notes ─────────────────────────────────────────────────────────────────
  async function listNotes(params = {}) { return request('GET', '/notes', null, params); }
  async function getNote(id) { return request('GET', `/notes/${id}`); }
  async function createNote(data) { return request('POST', '/notes', data); }
  async function updateNote(id, data) { return request('PUT', `/notes/${id}`, data); }
  async function deleteNote(id) { return request('DELETE', `/notes/${id}`); }
  async function listNoteShares(id) { return request('GET', `/notes/${id}/share`); }
  async function shareNote(id, data) { return request('POST', `/notes/${id}/share`, data); }
  async function unshareNote(id, username) { return request('DELETE', `/notes/${id}/share/${username}`); }

  // ── Parameterized Queries ────────────────────────────────────────────────
  async function listParameterizedQueries(params = {}) { return request('GET', '/parameterized-queries', null, params); }
  async function getParameterizedQuery(id) { return request('GET', `/parameterized-queries/${id}`); }
  async function createParameterizedQuery(data) { return request('POST', '/parameterized-queries', data); }
  async function updateParameterizedQuery(id, data) { return request('PUT', `/parameterized-queries/${id}`, data); }
  async function deleteParameterizedQuery(id) { return request('DELETE', `/parameterized-queries/${id}`); }
  async function executeParameterizedQuery(id, values, useCache = true) {
    return request('POST', `/parameterized-queries/${id}/execute`, { values, use_cache: useCache });
  }
  async function parseParameterizedQueryTemplate(shql) {
    return request('POST', '/parameterized-queries/parse', { shql });
  }

  // ── Media ─────────────────────────────────────────────────────────────────
  async function uploadMedia(file) {
    const url = new URL(BASE + '/media', window.location.origin);
    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const form = new FormData();
    form.append('file', file);

    const resp = await fetch(url.toString(), { method: 'POST', headers, body: form });
    if (resp.status === 401) {
      clearSession();
      window.dispatchEvent(new Event('hgai:unauthorized'));
      throw new Error('Unauthorized');
    }
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const msg = data.detail || data.message || `HTTP ${resp.status}`;
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  }

  async function downloadMedia(mediaId) {
    const url = new URL(BASE + `/media/${mediaId}`, window.location.origin);
    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const resp = await fetch(url.toString(), { headers });
    if (resp.status === 401) {
      clearSession();
      window.dispatchEvent(new Event('hgai:unauthorized'));
      throw new Error('Unauthorized');
    }
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      const msg = data.detail || data.message || `HTTP ${resp.status}`;
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return resp.blob();
  }

  async function deleteMedia(mediaId) { return request('DELETE', `/media/${mediaId}`); }
  async function listMedia(params = {}) { return request('GET', '/media', null, params); }
  async function updateMedia(mediaId, data) { return request('PUT', `/media/${mediaId}`, data); }

  // ── Query (SHQL) ──────────────────────────────────────────────────────────
  async function runShqlQuery(shql, useCache = true) {
    return request('POST', '/shql/query', { shql, use_cache: useCache });
  }
  async function validateShqlQuery(shql) { return request('POST', '/shql/validate', { shql }); }
  async function flushCache(graphId = null) {
    return request('POST', '/shql/cache/invalidate', null, graphId ? { graph_id: graphId } : {});
  }
  async function listShqlHistory() { return request('GET', '/shql/history'); }
  async function addShqlHistoryEntry(shql) { return request('POST', '/shql/history', { shql }); }
  async function clearShqlHistory() { return request('DELETE', '/shql/history'); }

  // ── Accounts ──────────────────────────────────────────────────────────────
  async function listAccounts(params = {}) { return request('GET', '/accounts', null, params); }
  async function getAccount(username) { return request('GET', `/accounts/${username}`); }
  async function createAccount(data) { return request('POST', '/accounts', data); }
  async function updateAccount(username, data) { return request('PUT', `/accounts/${username}`, data); }
  async function deleteAccount(username) { return request('DELETE', `/accounts/${username}`); }
  async function listAccountSpaces(username, params = {}) { return request('GET', `/accounts/${username}/spaces`, null, params); }
  async function assignAccountToSpace(username, spaceId, data) { return request('POST', `/accounts/${username}/spaces/${spaceId}`, data); }
  async function removeAccountFromSpace(username, spaceId) { return request('DELETE', `/accounts/${username}/spaces/${spaceId}`); }

  // ── Meshes ────────────────────────────────────────────────────────────────
  async function listMeshes(params = {}) { return request('GET', '/meshes', null, params); }
  async function getMesh(id) { return request('GET', `/meshes/${id}`); }
  async function createMesh(data) { return request('POST', '/meshes', data); }
  async function updateMesh(id, data) { return request('PUT', `/meshes/${id}`, data); }
  async function deleteMesh(id) { return request('DELETE', `/meshes/${id}`); }
  async function pingMesh(id) { return request('GET', `/meshes/${id}/ping`); }
  async function syncMesh(id) { return request('POST', `/meshes/${id}/sync`); }
  async function queryMesh(id, body) { return request('POST', `/meshes/${id}/query`, body); }

  // ── Spaces ────────────────────────────────────────────────────────────────
  async function listSpaces(params = {}) { return request('GET', '/spaces', null, params); }
  async function getSpace(id) { return request('GET', `/spaces/${id}`); }
  async function createSpace(data) { return request('POST', '/spaces', data); }
  async function updateSpace(id, data) { return request('PUT', `/spaces/${id}`, data); }
  async function deleteSpace(id) { return request('DELETE', `/spaces/${id}`); }
  async function listSpaceMembers(id) { return request('GET', `/spaces/${id}/members`); }
  async function addSpaceMember(spaceId, username, data) { return request('POST', `/spaces/${spaceId}/members/${username}`, data); }
  async function updateSpaceMemberRole(spaceId, username, data) { return request('PUT', `/spaces/${spaceId}/members/${username}`, data); }
  async function removeSpaceMember(spaceId, username) { return request('DELETE', `/spaces/${spaceId}/members/${username}`); }
  async function listSpaceGraphs(spaceId, params = {}) { return request('GET', `/spaces/${spaceId}/graphs`, null, params); }
  async function getSpaceGraph(spaceId, graphId) { return request('GET', `/spaces/${spaceId}/graphs/${graphId}`); }
  async function createSpaceGraph(spaceId, data) { return request('POST', `/spaces/${spaceId}/graphs`, data); }
  async function updateSpaceGraph(spaceId, graphId, data) { return request('PUT', `/spaces/${spaceId}/graphs/${graphId}`, data); }
  async function deleteSpaceGraph(spaceId, graphId) { return request('DELETE', `/spaces/${spaceId}/graphs/${graphId}`); }

  // ── Help ─────────────────────────────────────────────────────────────────
  async function listHelpTopics(params = {}) { return request('GET', '/help/topics', null, params); }
  async function getHelpTopic(id) { return request('GET', `/help/topics/${encodeURIComponent(id)}`); }
  async function getHelpHome() { return request('GET', '/help/home'); }
  // Help media is auth-protected like every other endpoint, so an <img src>
  // can't load it directly — fetch it with the token and hand back a Blob
  // (same approach as downloadMedia).
  async function downloadHelpMedia(path) {
    const url = new URL(BASE + '/help/media/' + path.split('/').map(encodeURIComponent).join('/'), window.location.origin);
    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(url.toString(), { headers });
    if (resp.status === 401) {
      clearSession();
      window.dispatchEvent(new Event('hgai:unauthorized'));
      throw new Error('Unauthorized');
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.blob();
  }

  // ── AI Agent (vendors/models/chat sessions/messages) ─────────────────────
  async function listAgentVendors(params = {}) { return request('GET', '/agent/vendors', null, params); }
  async function getAgentVendor(id) { return request('GET', `/agent/vendors/${id}`); }
  async function createAgentVendor(data) { return request('POST', '/agent/vendors', data); }
  async function updateAgentVendor(id, data) { return request('PUT', `/agent/vendors/${id}`, data); }
  async function deleteAgentVendor(id) { return request('DELETE', `/agent/vendors/${id}`); }

  async function listAgentModels(params = {}) { return request('GET', '/agent/models', null, params); }
  async function getAgentModel(id) { return request('GET', `/agent/models/${id}`); }
  async function createAgentModel(data) { return request('POST', '/agent/models', data); }
  async function updateAgentModel(id, data) { return request('PUT', `/agent/models/${id}`, data); }
  async function deleteAgentModel(id) { return request('DELETE', `/agent/models/${id}`); }

  async function listAgentSessions(params = {}) { return request('GET', '/agent/sessions', null, params); }
  async function getAgentSession(id) { return request('GET', `/agent/sessions/${id}`); }
  async function createAgentSession(data) { return request('POST', '/agent/sessions', data); }
  async function updateAgentSession(id, data) { return request('PUT', `/agent/sessions/${id}`, data); }
  async function deleteAgentSession(id) { return request('DELETE', `/agent/sessions/${id}`); }
  async function listAgentMessages(sessionId) { return request('GET', `/agent/sessions/${sessionId}/messages`); }
  async function sendAgentMessage(sessionId, prompt) { return request('POST', `/agent/sessions/${sessionId}/messages`, { prompt }); }
  async function saveAgentMessageAsNote(sessionId, messageId) {
    return request('POST', `/agent/sessions/${sessionId}/messages/${messageId}/save-note`);
  }

  async function listAgentPromptHistory() { return request('GET', '/agent/prompt-history'); }
  async function addAgentPromptHistoryEntry(prompt) { return request('POST', '/agent/prompt-history', { prompt }); }
  async function clearAgentPromptHistory() { return request('DELETE', '/agent/prompt-history'); }

  // SSE streaming needs a manual fetch — request() always awaits resp.json().
  // Frames are `\n\n`-delimited; a frame may span multiple `read()` chunks,
  // so a trailing partial frame is held in `buffer` until it completes.
  async function streamAgentMessage(sessionId, prompt, { onDelta, onDone, onError } = {}) {
    const url = new URL(`${BASE}/agent/sessions/${sessionId}/messages/stream`, window.location.origin);
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const resp = await fetch(url.toString(), { method: 'POST', headers, body: JSON.stringify({ prompt }) });
    if (resp.status === 401) {
      clearSession();
      window.dispatchEvent(new Event('hgai:unauthorized'));
      throw new Error('Unauthorized');
    }
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop();
      for (const frame of frames) {
        if (!frame.trim()) continue;
        let eventName = 'message';
        let dataLine = '';
        frame.split('\n').forEach(line => {
          if (line.startsWith('event:')) eventName = line.slice(6).trim();
          else if (line.startsWith('data:')) dataLine = line.slice(5).trim();
        });
        if (!dataLine) continue;
        const parsed = JSON.parse(dataLine);
        if (eventName === 'done') onDone && onDone(parsed);
        else if (eventName === 'error') onError && onError(parsed);
        else if (parsed.delta !== undefined) onDelta && onDelta(parsed.delta);
      }
    }
  }

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
    listSpaceNodes, getSpaceNode, createSpaceNode, updateSpaceNode, deleteSpaceNode,
    // edges
    listEdges, getEdge, createEdge, updateEdge, deleteEdge,
    listSpaceEdges, getSpaceEdge, createSpaceEdge, updateSpaceEdge, deleteSpaceEdge,
    // inference
    projectInference,
    // notes
    listNotes, getNote, createNote, updateNote, deleteNote, listNoteShares, shareNote, unshareNote,
    // parameterized queries
    listParameterizedQueries, getParameterizedQuery, createParameterizedQuery, updateParameterizedQuery,
    deleteParameterizedQuery, executeParameterizedQuery, parseParameterizedQueryTemplate,
    // media
    uploadMedia, downloadMedia, deleteMedia, listMedia, updateMedia,
    // query (SHQL)
    runShqlQuery, validateShqlQuery, flushCache,
    listShqlHistory, addShqlHistoryEntry, clearShqlHistory,
    // accounts
    listAccounts, getAccount, createAccount, updateAccount, deleteAccount,
    listAccountSpaces, assignAccountToSpace, removeAccountFromSpace,
    // meshes
    listMeshes, getMesh, createMesh, updateMesh, deleteMesh, pingMesh, syncMesh, queryMesh,
    // spaces
    listSpaces, getSpace, createSpace, updateSpace, deleteSpace,
    listSpaceMembers, addSpaceMember, updateSpaceMemberRole, removeSpaceMember,
    listSpaceGraphs, getSpaceGraph, createSpaceGraph, updateSpaceGraph, deleteSpaceGraph,
    // help
    listHelpTopics, getHelpTopic, getHelpHome, downloadHelpMedia,
    // AI agent
    listAgentVendors, getAgentVendor, createAgentVendor, updateAgentVendor, deleteAgentVendor,
    listAgentModels, getAgentModel, createAgentModel, updateAgentModel, deleteAgentModel,
    listAgentSessions, getAgentSession, createAgentSession, updateAgentSession, deleteAgentSession,
    listAgentMessages, sendAgentMessage, saveAgentMessageAsNote, streamAgentMessage,
    listAgentPromptHistory, addAgentPromptHistoryEntry, clearAgentPromptHistory,
  };
})();
