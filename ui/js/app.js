/**
 * HypergraphAI Web UI - Main Application
 */

// ── State ──────────────────────────────────────────────────────────────────
const State = {
  currentScreen: 'dashboard',
  activeGraphId: null,
  nodesPage: 0,
  edgesPage: 0,
  mediaPage: 0,
  mediaPickerPage: 0,
  nodePageSize: 50,
  edgePageSize: 50,
  mediaPageSize: 50,
  mediaPickerPageSize: 10,
  confirmCallback: null,
  editorCM: null,
  graphsCache: {},       // id -> graph object (includes space_id)
  mediaCache: {},        // id -> media object, from the last list load
  activeSpaceDetailId: null,
  nodesSort: [{ field: 'label', dir: 'asc' }],  // [{field, dir: 'asc'|'desc'}, ...] — priority order, first = primary sort key
  edgesSort: [{ field: 'label', dir: 'asc' }],  // default until the user clicks a column header, then their choice persists for the session
  mediaSort: [],
  viz3d: null,
};

// ── Utilities ──────────────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  const id = 'toast-' + Date.now();
  const icons = { success: 'check-circle-fill', danger: 'x-circle-fill', warning: 'exclamation-triangle-fill', info: 'info-circle-fill' };
  const html = `
    <div id="${id}" class="toast align-items-center text-bg-${type} border-0 mb-2" role="alert">
      <div class="d-flex">
        <div class="toast-body"><i class="bi bi-${icons[type]||'info'} me-2"></i>${msg}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`;
  document.getElementById('toast-container').insertAdjacentHTML('beforeend', html);
  const el = document.getElementById(id);
  const t = new bootstrap.Toast(el, { delay: 4000 });
  t.show();
  el.addEventListener('hidden.bs.toast', () => el.remove());
}

function statusBadge(s) {
  const map = { active: 'badge-status-active', draft: 'badge-status-draft', archived: 'badge-status-archived' };
  return `<span class="badge ${map[s]||'bg-secondary'}">${s||'—'}</span>`;
}

function tagBadges(tags = []) {
  return tags.map(t => `<span class="badge-tag">${t}</span>`).join('');
}

function roleBadges(roles = []) {
  return roles.map(r => `<span class="badge-role">${r}</span>`).join('');
}

function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}

function truncate(s, n = 32) {
  if (!s) return '—';
  return s.length > n ? s.slice(0, n) + '…' : s;
}

// Free-form fields (filenames, uploader-supplied content types, ...) go through
// this before landing in an innerHTML template — unlike `id` fields elsewhere
// in this app, these come straight from user-controlled upload metadata.
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function parseTags(str) {
  return (str || '').split(',').map(t => t.trim()).filter(Boolean);
}

function parseJSON(str, fallback = {}) {
  try { return JSON.parse(str || '{}'); } catch { return fallback; }
}

function showDetail(title, obj) {
  document.getElementById('modal-detail-title').textContent = title;
  document.getElementById('modal-detail-content').textContent = JSON.stringify(obj, null, 2);
  new bootstrap.Modal(document.getElementById('modal-detail')).show();
}

function confirmDelete(msg, cb) {
  document.getElementById('modal-confirm-body').textContent = msg;
  State.confirmCallback = cb;
  new bootstrap.Modal(document.getElementById('modal-confirm')).show();
}

// ── Router ─────────────────────────────────────────────────────────────────
function showScreen(name) {
  document.querySelectorAll('.screen').forEach(s => s.classList.add('d-none'));
  const el = document.getElementById(`screen-${name}`);
  if (el) el.classList.remove('d-none');

  document.querySelectorAll('.sidebar-link').forEach(l => {
    l.classList.toggle('active', l.dataset.screen === name);
  });

  const titles = {
    dashboard: 'Dashboard', graphs: 'Hypergraphs', nodes: 'Hypernodes',
    edges: 'Hyperedges', media: 'Media', viz: 'Visualize', query: 'HQL Query', shql: 'SHQL Query',
    spaces: 'Spaces', accounts: 'Accounts', meshes: 'Meshes', system: 'System',
  };
  document.getElementById('topbar-screen-title').textContent = titles[name] || name;
  State.currentScreen = name;

  // Load screen data
  const loaders = {
    dashboard: loadDashboard,
    graphs: loadGraphs,
    nodes: () => { State.nodesPage = 0; populateNodesGraphSelect(); loadNodes(); },
    edges: () => { State.edgesPage = 0; populateEdgesGraphSelect(); loadEdges(); },
    media: () => { State.mediaPage = 0; loadMedia(); },
    viz: loadVizScreen,
    query: initQueryEditor,
    shql: initShqlEditor,
    spaces: loadSpaces,
    accounts: loadAccounts,
    meshes: loadMeshes,
    system: loadSystem,
  };
  if (loaders[name]) loaders[name]();
}

// ── Sidebar toggle ─────────────────────────────────────────────────────────
document.getElementById('btn-sidebar-toggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('collapsed');
});

document.querySelectorAll('.sidebar-link[data-screen]').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    showScreen(link.dataset.screen);
  });
});

document.getElementById('btn-logout').addEventListener('click', e => {
  e.preventDefault();
  HGAI_API.clearSession();
  location.reload();
});

document.getElementById('btn-confirm-delete').addEventListener('click', () => {
  if (State.confirmCallback) {
    State.confirmCallback();
    State.confirmCallback = null;
  }
  bootstrap.Modal.getInstance(document.getElementById('modal-confirm'))?.hide();
});

window.addEventListener('hgai:unauthorized', () => {
  HGAI_API.clearSession();
  location.reload();
});

// ── Active graph selector ──────────────────────────────────────────────────
document.getElementById('active-graph-select').addEventListener('change', function() {
  State.activeGraphId = this.value || null;
  document.getElementById('nodes-graph-select').value = this.value;
  document.getElementById('edges-graph-select').value = this.value;
  if (State.currentScreen === 'nodes') { State.nodesPage = 0; loadNodes(); }
  if (State.currentScreen === 'edges') { State.edgesPage = 0; loadEdges(); }
});

// Returns space_id for the given graph ID (or active graph) using the cache
function graphSpaceId(graphId) {
  const gid = graphId || State.activeGraphId;
  return gid ? (State.graphsCache[gid]?.space_id || null) : null;
}

async function _fetchAndCacheGraphs() {
  const resp = await HGAI_API.listGraphs({ status: 'active', limit: 200 });
  (resp.items || []).forEach(g => { State.graphsCache[g.id] = g; });
  return resp.items || [];
}

async function populateGraphSelector() {
  const sel = document.getElementById('active-graph-select');
  try {
    const items = await _fetchAndCacheGraphs();
    sel.innerHTML = '<option value="">— Select Graph —</option>';
    items.forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id;
      opt.textContent = g.space_id ? `${g.label} (${g.space_id}/${g.id})` : `${g.label} (${g.id})`;
      if (g.id === State.activeGraphId) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch {}
}

async function populateNodesGraphSelect(selectedId) {
  const sel = document.getElementById('nodes-graph-select');
  const pick = selectedId !== undefined ? selectedId : (sel.value || State.activeGraphId);
  try {
    const items = await _fetchAndCacheGraphs();
    sel.innerHTML = '<option value="">— Select Hypergraph —</option>';
    items.forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id;
      opt.textContent = g.space_id ? `${g.label} (${g.space_id}/${g.id})` : `${g.label} (${g.id})`;
      if (g.id === pick) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch {}
}

document.getElementById('nodes-graph-select').addEventListener('change', function() {
  State.activeGraphId = this.value || null;
  document.getElementById('active-graph-select').value = this.value;
  document.getElementById('edges-graph-select').value = this.value;
  State.nodesPage = 0;
  loadNodes();
});

async function populateEdgesGraphSelect(selectedId) {
  const sel = document.getElementById('edges-graph-select');
  const pick = selectedId !== undefined ? selectedId : (sel.value || State.activeGraphId);
  try {
    const items = await _fetchAndCacheGraphs();
    sel.innerHTML = '<option value="">— Select Hypergraph —</option>';
    items.forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id;
      opt.textContent = g.space_id ? `${g.label} (${g.space_id}/${g.id})` : `${g.label} (${g.id})`;
      if (g.id === pick) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch {}
}

document.getElementById('edges-graph-select').addEventListener('change', function() {
  State.activeGraphId = this.value || null;
  document.getElementById('active-graph-select').value = this.value;
  document.getElementById('nodes-graph-select').value = this.value;
  State.edgesPage = 0;
  loadEdges();
});

// ── Login ──────────────────────────────────────────────────────────────────
document.getElementById('form-login').addEventListener('submit', async e => {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  const spinner = document.getElementById('login-spinner');

  errEl.classList.add('d-none');
  spinner.classList.remove('d-none');

  try {
    await HGAI_API.login(username, password);
    initApp();
  } catch (err) {
    errEl.textContent = err.message || 'Login failed';
    errEl.classList.remove('d-none');
  } finally {
    spinner.classList.add('d-none');
  }
});

// ── App Init ───────────────────────────────────────────────────────────────
function initApp() {
  const token = HGAI_API.getToken();
  if (!token) {
    document.getElementById('screen-login').classList.remove('d-none');
    document.getElementById('app-shell').classList.add('d-none');
    return;
  }

  document.getElementById('screen-login').classList.add('d-none');
  document.getElementById('app-shell').classList.remove('d-none');

  const username = HGAI_API.getUsername();
  document.getElementById('sidebar-username').textContent = username || '—';

  // Show/hide admin sections
  const isAdmin = HGAI_API.isAdmin();
  document.querySelectorAll('.admin-only').forEach(el => {
    el.style.display = isAdmin ? '' : 'none';
  });

  populateGraphSelector();
  showScreen('dashboard');
}

// ── Dashboard ──────────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [graphsResp, serverInfo] = await Promise.allSettled([
      HGAI_API.listGraphs({ status: 'active', limit: 200 }),
      HGAI_API.getServerInfo(),
    ]);

    const graphs = graphsResp.value || { total: 0, items: [] };
    document.getElementById('stat-graphs').textContent = graphs.total;

    let totalNodes = 0, totalEdges = 0;
    const graphList = document.getElementById('dash-graphs-list');
    graphList.innerHTML = '';

    (graphs.items || []).forEach(g => {
      totalNodes += g.node_count || 0;
      totalEdges += g.edge_count || 0;
      const a = document.createElement('a');
      a.href = '#';
      a.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
      a.innerHTML = `
        <div>
          <div class="fw-semibold">${g.label}</div>
          <small class="text-muted">${g.id}</small>
        </div>
        <div class="d-flex gap-3 text-muted small">
          <span><i class="bi bi-circle-fill text-success"></i> ${g.node_count||0}</span>
          <span><i class="bi bi-share-fill text-info"></i> ${g.edge_count||0}</span>
        </div>`;
      a.addEventListener('click', e => {
        e.preventDefault();
        State.activeGraphId = g.id;
        document.getElementById('active-graph-select').value = g.id;
        showScreen('nodes');
      });
      graphList.appendChild(a);
    });

    document.getElementById('stat-nodes').textContent = totalNodes;
    document.getElementById('stat-edges').textContent = totalEdges;

    // Accounts count (admin only)
    if (HGAI_API.isAdmin()) {
      try {
        const accs = await HGAI_API.listAccounts({ limit: 1 });
        document.getElementById('stat-accounts').textContent = accs.total;
      } catch {}
    } else {
      document.getElementById('stat-accounts').textContent = '—';
    }

    // Server info
    if (serverInfo.value) {
      const si = serverInfo.value;
      const table = document.getElementById('dash-server-info');
      table.innerHTML = Object.entries({
        'Server ID': si.server_id,
        'Server Name': si.server_name,
        'Version': si.version,
        'Capabilities': (si.capabilities || []).join(', '),
      }).map(([k,v]) => `<tr><th class="fw-normal text-muted" style="width:40%">${k}</th><td>${v||'—'}</td></tr>`).join('');
    }
  } catch (err) {
    console.error('Dashboard load error:', err);
  }
}

// ── Hypergraphs ────────────────────────────────────────────────────────────
async function loadGraphs() {
  const tbody = document.getElementById('tbody-graphs');
  tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  try {
    const resp = await HGAI_API.listGraphs({ status: '', limit: 200 });
    tbody.innerHTML = '';
    State.graphsCache = {};
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">No hypergraphs found</td></tr>';
      return;
    }
    resp.items.forEach(g => {
      State.graphsCache[g.id] = g;
      const spaceLabel = g.space_id
        ? `<span class="badge bg-info text-dark">${g.space_id}</span>`
        : '<span class="text-muted small">—</span>';
      const sid = g.space_id ? `'${g.space_id}'` : 'null';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="table-id-link" onclick="editGraph('${g.id}', ${sid})"><code>${g.id}</code></td>
        <td>${g.label}</td>
        <td><span class="badge bg-light text-dark">${g.type}</span></td>
        <td>${spaceLabel}</td>
        <td>${g.node_count||0}</td>
        <td>${g.edge_count||0}</td>
        <td>${statusBadge(g.status)}</td>
        <td>${tagBadges(g.tags)}</td>
        <td class="text-end">
          <button class="btn btn-xs btn-outline-secondary me-1" onclick="viewGraph('${g.id}', ${sid})"><i class="bi bi-eye"></i></button>
          <button class="btn btn-xs btn-outline-primary me-1" onclick="editGraph('${g.id}', ${sid})"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-xs btn-outline-danger" onclick="deleteGraph('${g.id}', ${sid})"><i class="bi bi-trash"></i></button>
        </td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-create-graph').addEventListener('click', () => openGraphModal());

async function _populateSpaceSelect(selectedSpaceId = null, locked = false) {
  const sel = document.getElementById('graph-space-id');
  sel.innerHTML = '<option value="">— None (global) —</option>';
  sel.disabled = locked;
  try {
    const resp = await HGAI_API.listSpaces({ status: 'active', limit: 200 });
    (resp.items || []).forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id; opt.textContent = `${s.label} (${s.id})`;
      if (s.id === selectedSpaceId) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch {}
}

async function openGraphModal(graphId = null, spaceId = null) {
  const modal = new bootstrap.Modal(document.getElementById('modal-graph'));
  const isEdit = !!graphId;
  document.getElementById('graph-form-mode').value = isEdit ? 'edit' : 'create';
  document.getElementById('modal-graph-title').textContent = isEdit ? 'Edit Hypergraph' : 'New Hypergraph';
  document.getElementById('graph-space-id-hidden').value = spaceId || '';

  if (isEdit) {
    try {
      const g = spaceId
        ? await HGAI_API.getSpaceGraph(spaceId, graphId)
        : await HGAI_API.getGraph(graphId);
      await _populateSpaceSelect(g.space_id, true);  // locked on edit
      document.getElementById('graph-id').value = g.id;
      document.getElementById('graph-id').readOnly = true;
      document.getElementById('graph-label').value = g.label || '';
      document.getElementById('graph-type').value = g.type || 'instantiated';
      document.getElementById('graph-description').value = g.description || '';
      document.getElementById('graph-tags').value = (g.tags || []).join(', ');
      document.getElementById('graph-attributes').value = JSON.stringify(g.attributes || {}, null, 2);
    } catch {}
  } else {
    document.getElementById('form-graph').reset();
    document.getElementById('graph-id').readOnly = false;
    document.getElementById('graph-attributes').value = '{}';
    await _populateSpaceSelect(null, false);
  }
  modal.show();
}

window.editGraph = (id, spaceId) => openGraphModal(id, spaceId || null);
window.viewGraph = async (id, spaceId) => {
  const g = spaceId
    ? await HGAI_API.getSpaceGraph(spaceId, id).catch(()=>null)
    : await HGAI_API.getGraph(id).catch(()=>null);
  const stats = spaceId ? null : await HGAI_API.getGraphStats(id).catch(()=>null);
  showDetail(`Hypergraph: ${id}`, stats ? { ...g, stats } : g);
};
window.deleteGraph = (id, spaceId) => {
  confirmDelete(`Delete hypergraph "${id}" and ALL its nodes and edges?`, async () => {
    try {
      if (spaceId) {
        await HGAI_API.deleteSpaceGraph(spaceId, id);
      } else {
        await HGAI_API.deleteGraph(id);
      }
      toast(`Hypergraph "${id}" deleted`);
      loadGraphs();
      populateGraphSelector();
    } catch (err) { toast(err.message, 'danger'); }
  });
};

document.getElementById('btn-save-graph').addEventListener('click', async () => {
  const mode = document.getElementById('graph-form-mode').value;
  const id = document.getElementById('graph-id').value.trim();
  // On create, use the dropdown; on edit, use the hidden field (locked)
  const spaceId = mode === 'create'
    ? (document.getElementById('graph-space-id').value || null)
    : (document.getElementById('graph-space-id-hidden').value || null);
  const data = {
    id,
    label: document.getElementById('graph-label').value.trim(),
    type: document.getElementById('graph-type').value,
    description: document.getElementById('graph-description').value.trim() || null,
    tags: parseTags(document.getElementById('graph-tags').value),
    attributes: parseJSON(document.getElementById('graph-attributes').value),
  };
  try {
    if (mode === 'create') {
      if (spaceId) {
        await HGAI_API.createSpaceGraph(spaceId, data);
      } else {
        await HGAI_API.createGraph(data);
      }
      toast('Hypergraph created');
    } else {
      if (spaceId) {
        await HGAI_API.updateSpaceGraph(spaceId, id, data);
      } else {
        await HGAI_API.updateGraph(id, data);
      }
      toast('Hypergraph updated');
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-graph'))?.hide();
    loadGraphs();
    populateGraphSelector();
  } catch (err) { toast(err.message, 'danger'); }
});

// ── Multi-column table sort ───────────────────────────────────────────────
function sortParam(sortState) {
  if (!sortState || !sortState.length) return undefined;
  return sortState.map(s => (s.dir === 'desc' ? '-' : '') + s.field).join(',');
}

function updateSortIndicators(table) {
  const sortState = State[table + 'Sort'] || [];
  document.querySelectorAll(`.sortable-th[data-table="${table}"]`).forEach(th => {
    const field = th.dataset.sortField;
    const idx = sortState.findIndex(s => s.field === field);
    const indicator = th.querySelector('.sort-indicator');
    if (idx === -1) {
      th.classList.remove('sort-active');
      indicator.innerHTML = '';
      return;
    }
    th.classList.add('sort-active');
    const entry = sortState[idx];
    const arrow = entry.dir === 'desc' ? '<i class="bi bi-caret-down-fill"></i>' : '<i class="bi bi-caret-up-fill"></i>';
    const priority = sortState.length > 1 ? `<span class="sort-priority">${idx + 1}</span>` : '';
    indicator.innerHTML = arrow + priority;
  });
}

function handleSortableThClick(th, shiftKey) {
  const table = th.dataset.table;
  const field = th.dataset.sortField;
  const key = table + 'Sort';
  let sortState = State[key] || [];

  if (shiftKey) {
    const idx = sortState.findIndex(s => s.field === field);
    if (idx === -1) {
      sortState = sortState.concat([{ field, dir: 'asc' }]);
    } else if (sortState[idx].dir === 'asc') {
      sortState = sortState.slice();
      sortState[idx] = { field, dir: 'desc' };
    } else {
      sortState = sortState.slice(0, idx).concat(sortState.slice(idx + 1));
    }
  } else {
    const isOnlyActiveColumn = sortState.length === 1 && sortState[0].field === field;
    if (isOnlyActiveColumn && sortState[0].dir === 'asc') {
      sortState = [{ field, dir: 'desc' }];
    } else if (isOnlyActiveColumn && sortState[0].dir === 'desc') {
      sortState = [];
    } else {
      sortState = [{ field, dir: 'asc' }];
    }
  }

  State[key] = sortState;
  State[table + 'Page'] = 0;
  const reload = PAGINATION_LOADERS[table];
  if (reload) reload();
}

document.querySelectorAll('.sortable-th').forEach(th => {
  th.addEventListener('click', e => handleSortableThClick(th, e.shiftKey));
});

// ── Hypernodes ─────────────────────────────────────────────────────────────
async function loadNodes() {
  // Sync State from the in-screen selector (it may have been set before State synced)
  const screenSel = document.getElementById('nodes-graph-select');
  if (screenSel.value) State.activeGraphId = screenSel.value;
  if (!State.activeGraphId) {
    document.getElementById('tbody-nodes').innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">Select a hypergraph above</td></tr>';
    return;
  }
  const tbody = document.getElementById('tbody-nodes');
  tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';

  const params = {
    skip: State.nodesPage * State.nodePageSize,
    limit: State.nodePageSize,
    status: document.getElementById('node-status-filter').value || undefined,
    node_type: document.getElementById('node-type-filter').value.trim() || undefined,
    search: document.getElementById('node-search').value.trim() || undefined,
    sort: sortParam(State.nodesSort),
  };
  updateSortIndicators('nodes');

  const showMedia = document.getElementById('node-show-media').checked;
  document.querySelector('#screen-nodes thead .td-media')?.classList.toggle('d-none', !showMedia);

  const spaceId = graphSpaceId(State.activeGraphId);
  try {
    const resp = spaceId
      ? await HGAI_API.listSpaceNodes(spaceId, State.activeGraphId, params)
      : await HGAI_API.listNodes(State.activeGraphId, params);
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">No hypernodes found</td></tr>';
    } else {
      resp.items.forEach(n => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="table-id-link" onclick="editNode('${n.id}')"><code class="text-truncate-150" title="${n.id}">${n.id}</code></td>
          <td class="td-media text-center ${showMedia ? '' : 'd-none'}">${showMedia ? mediaThumbCellHtml(n) : ''}</td>
          <td>${n.label||'—'}</td>
          <td><span class="badge bg-light text-dark">${n.type||'—'}</span></td>
          <td>${statusBadge(n.status)}</td>
          <td>${tagBadges(n.tags)}</td>
          <td class="small text-muted">${fmtDate(n.valid_from)}</td>
          <td class="small text-muted">${fmtDate(n.valid_to)}</td>
          <td class="text-end">
            <button class="btn btn-xs btn-outline-secondary me-1" onclick="viewNode('${n.id}')"><i class="bi bi-eye"></i></button>
            <button class="btn btn-xs btn-outline-success me-1" onclick="editNode('${n.id}')"><i class="bi bi-pencil"></i></button>
            <button class="btn btn-xs btn-outline-danger" onclick="deleteNode('${n.id}')"><i class="bi bi-trash"></i></button>
          </td>`;
        tbody.appendChild(tr);
      });
      if (showMedia) await loadTableThumbnails(tbody, _nodeThumbUrls);
    }
    renderPagination('nodes', resp.total, State.nodesPage, State.nodePageSize);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

const PAGINATION_LOADERS = { nodes: () => loadNodes(), edges: () => loadEdges(), media: () => loadMedia(), mediaPicker: () => loadMediaPicker() };

// ── Default-media thumbnails (Nodes/Edges list tables) ────────────────────────
let _nodeThumbUrls = [];
let _edgeThumbUrls = [];

// The default media's own metadata is already cached on the MediaRef (see
// handleMediaUpload/attachExistingMedia) inside the entity's own `media` list,
// so no extra round-trip is needed just to know its content type.
function defaultMediaRefFor(entity) {
  if (!entity.default_media_id) return null;
  return (entity.media || []).find(m => m.media_id === entity.default_media_id) || null;
}

function mediaThumbCellHtml(entity) {
  const ref = defaultMediaRefFor(entity);
  if (!ref) return '<span class="text-muted small">—</span>';
  if (ref.content_type && ref.content_type.startsWith('image/')) {
    return `<img class="table-thumb" data-thumb-media-id="${escapeHtml(ref.media_id)}" alt="${escapeHtml(ref.label || ref.filename || '')}">`;
  }
  const icon = ref.content_type && ref.content_type.startsWith('audio/') ? 'bi-music-note-beamed'
    : ref.content_type && ref.content_type.startsWith('video/') ? 'bi-camera-reels-fill'
    : 'bi-file-earmark-fill';
  return `<i class="bi ${icon} text-secondary fs-5" title="${escapeHtml(ref.label || ref.filename || ref.media_id)}"></i>`;
}

// Thumbnails are only actually fetched (as authenticated blobs, same as every
// other media view in this app) for rows whose default media is an image —
// audio/video/other default media render as a plain icon (no fetch needed,
// content_type is already cached) since there's no cheap static preview frame
// to show for those without real transcoding, which is out of scope here.
async function loadTableThumbnails(tbody, urlStore) {
  urlStore.forEach(u => URL.revokeObjectURL(u));
  urlStore.length = 0;
  const imgs = tbody.querySelectorAll('img[data-thumb-media-id]');
  await Promise.all([...imgs].map(async img => {
    const mediaId = img.dataset.thumbMediaId;
    try {
      const blob = await HGAI_API.downloadMedia(mediaId);
      const url = URL.createObjectURL(blob);
      urlStore.push(url);
      img.src = url;
    } catch {
      img.replaceWith(Object.assign(document.createElement('i'), { className: 'bi bi-image text-muted fs-5' }));
    }
  }));
}

function renderPagination(type, total, page, pageSize) {
  const totalPages = Math.ceil(total / pageSize);
  const infoEl = document.getElementById(`${type}-pagination-info`);
  const pgEl = document.getElementById(`${type}-pagination`);
  const reload = PAGINATION_LOADERS[type];

  infoEl.textContent = `Showing ${page * pageSize + 1}–${Math.min((page+1)*pageSize, total)} of ${total}`;
  pgEl.innerHTML = '';

  const prev = document.createElement('button');
  prev.className = 'btn btn-outline-secondary btn-sm'; prev.textContent = '‹ Prev';
  prev.disabled = page === 0;
  prev.onclick = () => { State[`${type}Page`]--; reload(); };
  pgEl.appendChild(prev);

  const next = document.createElement('button');
  next.className = 'btn btn-outline-secondary btn-sm'; next.textContent = 'Next ›';
  next.disabled = page >= totalPages - 1;
  next.onclick = () => { State[`${type}Page`]++; reload(); };
  pgEl.appendChild(next);
}

// ── Media attachment widget (shared by node & edge modals) ──────────────────
let nodeMediaItems = [];
let edgeMediaItems = [];
let nodeDefaultMediaId = '';
let edgeDefaultMediaId = '';

// containerId is always 'node-media-list' or 'edge-media-list' — this lets
// renderMediaList() stay a single shared function without every call site
// needing to know which entity's default-media state it's rendering into.
function defaultMediaState(containerId) {
  return containerId === 'edge-media-list'
    ? { get: () => edgeDefaultMediaId, set: v => { edgeDefaultMediaId = v; } }
    : { get: () => nodeDefaultMediaId, set: v => { nodeDefaultMediaId = v; } };
}

let mediaRefEditContext = null; // { items, index, containerId } for the currently-open ref-edit modal

function renderMediaList(containerId, items) {
  const el = document.getElementById(containerId);
  el.innerHTML = '';
  if (!items.length) {
    el.innerHTML = '<div class="media-item-empty">No media attached</div>';
    return;
  }
  const defaultState = defaultMediaState(containerId);
  items.forEach((ref, i) => {
    const div = document.createElement('div');
    const isDefault = !!ref.media_id && ref.media_id === defaultState.get();
    div.className = 'media-item' + (isDefault ? ' media-item-default' : '');
    const primaryText = ref.label || ref.filename || ref.media_id;
    const secondaryName = ref.name && ref.name !== primaryText ? ref.name : null;
    const sizeDuration = mediaSizeDurationText(ref.size_bytes, ref.duration_seconds);
    div.innerHTML = `
      <i class="bi bi-file-earmark-fill text-secondary"></i>
      <div class="media-item-text">
        <div class="media-item-name" title="${escapeHtml(ref.media_id)}">${escapeHtml(primaryText)}</div>
        ${secondaryName ? `<div class="media-item-subname" title="${escapeHtml(secondaryName)}">${escapeHtml(secondaryName)}</div>` : ''}
      </div>
      ${ref.content_type ? `<span class="badge bg-light text-dark">${escapeHtml(ref.content_type)}</span>` : ''}
      ${sizeDuration !== '—' ? `<span class="badge bg-light text-dark">${escapeHtml(sizeDuration)}</span>` : ''}
      ${ref.role ? `<span class="badge bg-light text-dark">${escapeHtml(ref.role)}</span>` : ''}
      ${ref.attributes && Object.keys(ref.attributes).length ? '<span class="badge bg-light text-dark" title="Has custom attributes"><i class="bi bi-braces"></i></span>' : ''}
      <button type="button" class="btn btn-xs ${isDefault ? 'btn-warning' : 'btn-outline-secondary'}" title="${isDefault ? 'Default representation — click to unset' : 'Set as default representation'}"><i class="bi ${isDefault ? 'bi-star-fill' : 'bi-star'}"></i></button>
      <button type="button" class="btn btn-xs btn-outline-secondary" title="Preview"><i class="bi bi-eye"></i></button>
      <button type="button" class="btn btn-xs btn-outline-secondary" title="Edit role &amp; attributes"><i class="bi bi-pencil"></i></button>
      <button type="button" class="btn btn-xs btn-outline-secondary" title="Download"><i class="bi bi-download"></i></button>
      <button type="button" class="btn btn-xs btn-outline-danger" title="Remove"><i class="bi bi-x"></i></button>`;
    const [defaultBtn, previewBtn, editBtn, downloadBtn, removeBtn] = div.querySelectorAll('button');
    defaultBtn.addEventListener('click', () => {
      defaultState.set(isDefault ? '' : ref.media_id);
      renderMediaList(containerId, items);
    });
    previewBtn.addEventListener('click', () => openMediaPreview({
      id: ref.media_id, filename: ref.filename, content_type: ref.content_type,
      name: ref.name, label: ref.label, description: ref.description,
      size_bytes: ref.size_bytes, duration_seconds: ref.duration_seconds,
    }));
    editBtn.addEventListener('click', () => openMediaRefEditModal(items, i, containerId));
    downloadBtn.addEventListener('click', () => downloadMediaFile(ref.media_id, ref.filename));
    removeBtn.addEventListener('click', () => {
      items.splice(i, 1);
      if (isDefault) defaultState.set('');
      renderMediaList(containerId, items);
    });
    el.appendChild(div);
  });
}

async function openMediaRefEditModal(items, index, containerId) {
  let ref = items[index];
  mediaRefEditContext = { items, index, containerId };
  document.getElementById('media-ref-edit-name').textContent = ref.label || ref.filename || ref.media_id;
  document.getElementById('media-ref-edit-role').value = ref.role || '';
  document.getElementById('media-ref-edit-attributes').value = JSON.stringify(ref.attributes || {}, null, 2);

  // media_id fields are read-only for mesh-remote media — the backend refuses
  // to update a record owned by another server, so don't offer the illusion of editing it.
  const isRemote = ref.media_id.includes('/');
  document.getElementById('media-ref-edit-remote-note').classList.toggle('d-none', !isRemote);

  // The ref's cached name/label/description may predate this caching (media
  // attached before this feature existed) or have drifted if the file's
  // metadata was edited elsewhere since — refresh from the authoritative
  // record before showing an edit form, so Save can't silently blank out
  // real values with what was just an incomplete cache.
  if (!isRemote) {
    const fresh = await fetchMediaMetadata(ref.media_id);
    if (fresh) {
      ref = { ...ref, ...mediaToPreviewInfo(fresh), media_id: ref.media_id };
      delete ref.id;
      items[index] = ref;
      renderMediaList(containerId, items);
    }
  }

  document.getElementById('media-ref-edit-media-name').value = ref.name || '';
  document.getElementById('media-ref-edit-media-label').value = ref.label || '';
  document.getElementById('media-ref-edit-media-description').value = ref.description || '';
  ['media-ref-edit-media-name', 'media-ref-edit-media-label', 'media-ref-edit-media-description'].forEach(id => {
    document.getElementById(id).disabled = isRemote;
  });

  new bootstrap.Modal(document.getElementById('modal-media-ref-edit')).show();
}

document.getElementById('btn-save-media-ref-edit').addEventListener('click', async () => {
  if (!mediaRefEditContext) return;
  const { items, index, containerId } = mediaRefEditContext;
  const ref = items[index];
  const role = document.getElementById('media-ref-edit-role').value.trim();
  const attributes = parseJSON(document.getElementById('media-ref-edit-attributes').value);

  // Name/label/description belong to the shared Media record, not this one
  // association, so saving them here patches the record itself (same call the
  // standalone Media Edit modal makes) — every other entity referencing this
  // file sees the change too, and this ref's own cache is refreshed from the
  // response so the attachment widget doesn't need a page reload to show it.
  let mediaUpdates = {};
  const isRemote = ref.media_id.includes('/');
  if (!isRemote) {
    const name = document.getElementById('media-ref-edit-media-name').value.trim();
    const label = document.getElementById('media-ref-edit-media-label').value.trim();
    const description = document.getElementById('media-ref-edit-media-description').value.trim();
    const spinner = document.getElementById('media-ref-edit-spinner');
    spinner.classList.remove('d-none');
    try {
      const media = await HGAI_API.updateMedia(ref.media_id, {
        name: name || null, label: label || null, description: description || null,
      });
      mediaUpdates = {
        content_type: media.content_type, filename: media.filename,
        name: media.name, label: media.label, description: media.description,
        size_bytes: media.size_bytes, duration_seconds: media.duration_seconds,
      };
    } catch (err) {
      toast(err.message, 'danger');
      spinner.classList.add('d-none');
      return;
    }
    spinner.classList.add('d-none');
  }

  items[index] = { ...items[index], ...mediaUpdates, role: role || null, attributes };
  renderMediaList(containerId, items);
  bootstrap.Modal.getInstance(document.getElementById('modal-media-ref-edit'))?.hide();
  toast('Media updated');
});

async function downloadMediaFile(mediaId, filename) {
  try {
    const blob = await HGAI_API.downloadMedia(mediaId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || State.mediaCache[mediaId]?.filename || mediaId;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (err) { toast(err.message, 'danger'); }
}

// ── Media preview (image / audio / video) — shared wherever media is referenced ──
const _mediaPreviewUrls = {}; // containerId -> object URL currently rendered into it

function isPreviewableMediaType(contentType) {
  return /^(image|audio|video)\//.test(contentType || '');
}

function clearMediaPreview(containerId) {
  if (_mediaPreviewUrls[containerId]) {
    URL.revokeObjectURL(_mediaPreviewUrls[containerId]);
    delete _mediaPreviewUrls[containerId];
  }
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = '';
}

async function renderMediaPreviewInto(containerId, mediaId, filename, contentType) {
  const el = document.getElementById(containerId);
  if (_mediaPreviewUrls[containerId]) {
    URL.revokeObjectURL(_mediaPreviewUrls[containerId]);
    delete _mediaPreviewUrls[containerId];
  }
  if (!isPreviewableMediaType(contentType)) {
    el.innerHTML = `<div class="text-muted py-3"><i class="bi bi-file-earmark display-6 d-block mb-2"></i>No preview available${contentType ? ` for "${escapeHtml(contentType)}"` : ''}</div>`;
    return;
  }
  el.innerHTML = '<div class="spinner-border spinner-border-sm"></div>';
  try {
    const blob = await HGAI_API.downloadMedia(mediaId);
    const objectUrl = URL.createObjectURL(blob);
    _mediaPreviewUrls[containerId] = objectUrl;
    const altText = escapeHtml(filename || mediaId);
    if (contentType.startsWith('image/')) {
      el.innerHTML = `<img src="${objectUrl}" alt="${altText}"/>`;
    } else if (contentType.startsWith('video/')) {
      el.innerHTML = `<video src="${objectUrl}" controls></video>`;
    } else if (contentType.startsWith('audio/')) {
      el.innerHTML = `<audio src="${objectUrl}" controls></audio>`;
    }
  } catch (err) {
    el.innerHTML = `<div class="text-danger small py-3">${escapeHtml(err.message)}</div>`;
  }
}

// Builds the openMediaPreview() info object from a full Media record (as opposed
// to a MediaRef, which already carries the same field names directly).
function mediaToPreviewInfo(m) {
  return {
    id: m.id, filename: m.filename, content_type: m.content_type,
    name: m.name, label: m.label, description: m.description,
    size_bytes: m.size_bytes, duration_seconds: m.duration_seconds,
  };
}

function renderMediaPreviewMetadata(info) {
  document.getElementById('media-preview-meta-name').textContent = info.name || '—';
  document.getElementById('media-preview-meta-label').textContent = info.label || '—';
  document.getElementById('media-preview-meta-size').textContent = fmtBytes(info.size_bytes);
  document.getElementById('media-preview-meta-duration').textContent = fmtDuration(info.duration_seconds) || '-';
  document.getElementById('media-preview-meta-description').textContent = info.description || '—';
}

// Refetches the authoritative Media record for `mediaId`, so the preview modal's
// metadata table is always correct even when the caller only had a MediaRef
// cached before name/label/description/size/duration were added to that cache
// (e.g. media attached to a hypernode/hyperedge in an earlier session) — or when
// the record's metadata was edited after it was attached. Mesh-qualified ids
// have no local record to refresh from, so those are left as-is.
async function fetchMediaMetadata(mediaId) {
  if (!mediaId || mediaId.includes('/')) return null;
  try {
    const resp = await HGAI_API.listMedia({ id: mediaId, limit: 1 });
    return (resp.items && resp.items[0]) || null;
  } catch {
    return null;
  }
}

// info: { id, filename, content_type, name, label, description, size_bytes, duration_seconds }
async function openMediaPreview(info) {
  const mediaId = info.id;
  document.getElementById('media-preview-title').textContent = info.label || info.filename || mediaId;
  document.getElementById('btn-media-preview-download').onclick = () => downloadMediaFile(mediaId, info.filename);
  renderMediaPreviewMetadata(info);
  new bootstrap.Modal(document.getElementById('modal-media-preview')).show();

  const [, fresh] = await Promise.all([
    renderMediaPreviewInto('media-preview-body', mediaId, info.filename, info.content_type),
    fetchMediaMetadata(mediaId),
  ]);
  if (fresh) {
    const freshInfo = mediaToPreviewInfo(fresh);
    document.getElementById('media-preview-title').textContent = freshInfo.label || freshInfo.filename || mediaId;
    document.getElementById('btn-media-preview-download').onclick = () => downloadMediaFile(mediaId, freshInfo.filename);
    renderMediaPreviewMetadata(freshInfo);
  }
}

document.getElementById('modal-media-preview').addEventListener('hidden.bs.modal', () => clearMediaPreview('media-preview-body'));
document.getElementById('modal-media-edit').addEventListener('hidden.bs.modal', () => clearMediaPreview('media-edit-preview'));

async function handleMediaUpload(fileInputId, roleInputId, spinnerId, items, containerId) {
  const fileInput = document.getElementById(fileInputId);
  const file = fileInput.files[0];
  if (!file) { toast('Choose a file first', 'warning'); return; }
  const role = document.getElementById(roleInputId).value.trim();
  const spinner = document.getElementById(spinnerId);
  spinner.classList.remove('d-none');
  try {
    const media = await HGAI_API.uploadMedia(file);
    items.push({
      media_id: media.id,
      role: role || null,
      content_type: media.content_type,
      filename: media.filename,
      name: media.name,
      label: media.label,
      description: media.description,
      size_bytes: media.size_bytes,
      duration_seconds: media.duration_seconds,
      attributes: {},
    });
    renderMediaList(containerId, items);
    fileInput.value = '';
    document.getElementById(roleInputId).value = '';
    toast(`"${media.filename || media.id}" uploaded and attached`);
  } catch (err) {
    toast(err.message, 'danger');
  } finally {
    spinner.classList.add('d-none');
  }
}

document.getElementById('btn-node-media-upload').addEventListener('click', () =>
  handleMediaUpload('node-media-file', 'node-media-role', 'node-media-upload-spinner', nodeMediaItems, 'node-media-list'));
document.getElementById('btn-edge-media-upload').addEventListener('click', () =>
  handleMediaUpload('edge-media-file', 'edge-media-role', 'edge-media-upload-spinner', edgeMediaItems, 'edge-media-list'));

// ── Media picker (attach an already-uploaded media file) ─────────────────────
let mediaPickerContext = null; // { items, containerId } for the currently-open picker modal

function openMediaPicker(items, containerId) {
  mediaPickerContext = { items, containerId };
  State.mediaPickerPage = 0;
  document.getElementById('media-picker-search').value = '';
  document.getElementById('media-picker-type-filter').value = '';
  document.getElementById('media-picker-role').value = '';
  new bootstrap.Modal(document.getElementById('modal-media-picker')).show();
  loadMediaPicker();
}

document.getElementById('btn-node-media-browse').addEventListener('click', () =>
  openMediaPicker(nodeMediaItems, 'node-media-list'));
document.getElementById('btn-edge-media-browse').addEventListener('click', () =>
  openMediaPicker(edgeMediaItems, 'edge-media-list'));

async function loadMediaPicker() {
  const tbody = document.getElementById('tbody-media-picker');
  tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';

  const params = {
    skip: State.mediaPickerPage * State.mediaPickerPageSize,
    limit: State.mediaPickerPageSize,
    search: document.getElementById('media-picker-search').value.trim() || undefined,
    content_type: document.getElementById('media-picker-type-filter').value.trim() || undefined,
    status: 'active',
  };

  try {
    const resp = await HGAI_API.listMedia(params);
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No media found</td></tr>';
    } else {
      resp.items.forEach(m => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><i class="bi bi-file-earmark-fill text-secondary me-1"></i><code class="text-truncate-150" title="${escapeHtml(m.filename || m.id)}">${escapeHtml(truncate(m.filename || m.id, 28))}</code></td>
          <td><span class="badge bg-light text-dark">${escapeHtml(m.content_type || '—')}</span></td>
          <td class="small text-muted">${fmtBytes(m.size_bytes)}</td>
          <td>${tagBadges(m.tags)}</td>
          <td class="text-end">
            <button type="button" class="btn btn-xs btn-outline-secondary me-1" title="Preview"><i class="bi bi-eye"></i></button>
            <button type="button" class="btn btn-xs btn-primary">Attach</button>
          </td>`;
        const [previewBtn, attachBtn] = tr.querySelectorAll('button');
        previewBtn.addEventListener('click', () => openMediaPreview(mediaToPreviewInfo(m)));
        attachBtn.addEventListener('click', () => attachExistingMedia(m));
        tbody.appendChild(tr);
      });
    }
    renderPagination('mediaPicker', resp.total, State.mediaPickerPage, State.mediaPickerPageSize);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-refresh-media-picker').addEventListener('click', () => loadMediaPicker());
['media-picker-search', 'media-picker-type-filter'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') { State.mediaPickerPage = 0; loadMediaPicker(); }
  });
});

function attachExistingMedia(m) {
  if (!mediaPickerContext) return;
  const { items, containerId } = mediaPickerContext;
  if (items.some(ref => ref.media_id === m.id)) {
    toast('Already attached', 'warning');
    return;
  }
  const role = document.getElementById('media-picker-role').value.trim();
  items.push({
    media_id: m.id,
    role: role || null,
    content_type: m.content_type,
    filename: m.filename,
    name: m.name,
    label: m.label,
    description: m.description,
    size_bytes: m.size_bytes,
    duration_seconds: m.duration_seconds,
    attributes: {},
  });
  renderMediaList(containerId, items);
  bootstrap.Modal.getInstance(document.getElementById('modal-media-picker'))?.hide();
  toast(`"${m.filename || m.id}" attached`);
}

// ── Media Screen (browse / search / manage) ──────────────────────────────────
function fmtBytes(n) {
  if (n == null) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

// Always renders hours:minutes:seconds (e.g. "0:00:32", "1:02:15") — never omits the hours place.
function fmtDuration(seconds) {
  if (seconds == null) return null;
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// Size always shown when known; duration appended when this is audio/video with a known length.
function mediaSizeDurationText(sizeBytes, durationSeconds) {
  const size = fmtBytes(sizeBytes);
  const duration = fmtDuration(durationSeconds);
  if (size === '—' && !duration) return '—';
  return duration ? (size === '—' ? duration : `${size} · ${duration}`) : size;
}

async function loadMedia() {
  const tbody = document.getElementById('tbody-media');
  tbody.innerHTML = '<tr><td colspan="11" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';

  const params = {
    skip: State.mediaPage * State.mediaPageSize,
    limit: State.mediaPageSize,
    search: document.getElementById('media-search').value.trim() || undefined,
    content_type: document.getElementById('media-type-filter').value.trim() || undefined,
    status: document.getElementById('media-status-filter').value || undefined,
    sort: sortParam(State.mediaSort),
  };
  updateSortIndicators('media');

  try {
    const resp = await HGAI_API.listMedia(params);
    tbody.innerHTML = '';
    State.mediaCache = {};
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-4">No media found</td></tr>';
    } else {
      resp.items.forEach(m => {
        State.mediaCache[m.id] = m;
        const tr = document.createElement('tr');
        const duration = fmtDuration(m.duration_seconds);
        tr.innerHTML = `
          <td class="table-id-link" onclick="editMedia('${m.id}')">
            <i class="bi bi-file-earmark-fill text-secondary me-1"></i>
            <code class="text-truncate-150" title="${escapeHtml(m.filename || m.id)}">${escapeHtml(truncate(m.filename || m.id, 28))}</code>
          </td>
          <td class="small text-muted">${escapeHtml(m.name || '—')}</td>
          <td>${escapeHtml(m.label || '—')}</td>
          <td><span class="badge bg-light text-dark">${escapeHtml(m.content_type || '—')}</span></td>
          <td class="small text-muted">${fmtBytes(m.size_bytes)}</td>
          <td class="small text-muted">${duration || '-'}</td>
          <td>${m.ref_count > 0 ? `<span class="badge bg-info text-dark">${m.ref_count}</span>` : '<span class="text-muted small">0</span>'}</td>
          <td class="small">${escapeHtml(m.uploaded_by || '—')}</td>
          <td>${tagBadges(m.tags)}</td>
          <td>${statusBadge(m.status)}</td>
          <td class="text-end">
            <button class="btn btn-xs btn-outline-secondary me-1" onclick="previewMediaRow('${m.id}')"><i class="bi bi-eye"></i></button>
            <button class="btn btn-xs btn-outline-secondary me-1" onclick="editMedia('${m.id}')"><i class="bi bi-pencil"></i></button>
            <button class="btn btn-xs btn-outline-secondary me-1" onclick="downloadMediaFile('${m.id}')"><i class="bi bi-download"></i></button>
            <button class="btn btn-xs btn-outline-danger" onclick="deleteMediaRow('${m.id}')"><i class="bi bi-trash"></i></button>
          </td>`;
        tbody.appendChild(tr);
      });
    }
    renderPagination('media', resp.total, State.mediaPage, State.mediaPageSize);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="11" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-refresh-media').addEventListener('click', () => loadMedia());
document.getElementById('media-status-filter').addEventListener('change', () => { State.mediaPage = 0; loadMedia(); });
['media-search', 'media-type-filter'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') { State.mediaPage = 0; loadMedia(); }
  });
});

// Standalone upload (not attached to any node/edge — browse-and-manage independently)
document.getElementById('btn-upload-media').addEventListener('click', () => {
  document.getElementById('upload-media-file').value = '';
  document.getElementById('upload-media-name').value = '';
  document.getElementById('upload-media-label').value = '';
  document.getElementById('upload-media-description').value = '';
  document.getElementById('upload-media-tags').value = '';
  document.getElementById('upload-media-attributes').value = '{}';
  new bootstrap.Modal(document.getElementById('modal-media-upload')).show();
});

document.getElementById('btn-confirm-upload-media').addEventListener('click', async () => {
  const fileInput = document.getElementById('upload-media-file');
  const file = fileInput.files[0];
  if (!file) { toast('Choose a file first', 'warning'); return; }
  const name = document.getElementById('upload-media-name').value.trim();
  const label = document.getElementById('upload-media-label').value.trim();
  const description = document.getElementById('upload-media-description').value.trim();
  const tags = parseTags(document.getElementById('upload-media-tags').value);
  const attributes = parseJSON(document.getElementById('upload-media-attributes').value);
  const spinner = document.getElementById('upload-media-spinner');
  spinner.classList.remove('d-none');
  try {
    const media = await HGAI_API.uploadMedia(file);
    if (name || label || description || tags.length || Object.keys(attributes).length) {
      await HGAI_API.updateMedia(media.id, {
        name: name || null, label: label || null, description: description || null,
        tags, attributes,
      });
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-media-upload'))?.hide();
    toast(`"${label || media.filename || media.id}" uploaded`);
    loadMedia();
  } catch (err) {
    toast(err.message, 'danger');
  } finally {
    spinner.classList.add('d-none');
  }
});

window.previewMediaRow = (id) => {
  const m = State.mediaCache[id];
  if (!m) return;
  openMediaPreview(mediaToPreviewInfo(m));
};

window.editMedia = (id) => {
  const m = State.mediaCache[id];
  if (!m) return;
  document.getElementById('media-edit-id').value = m.id;
  renderMediaPreviewInto('media-edit-preview', m.id, m.filename, m.content_type);
  document.getElementById('media-info-id').textContent = m.id;
  document.getElementById('media-info-content-type').textContent = m.content_type || '—';
  document.getElementById('media-info-size').textContent = fmtBytes(m.size_bytes);
  document.getElementById('media-info-checksum').textContent = m.checksum || '—';
  document.getElementById('media-info-uploaded-by').textContent = m.uploaded_by || '—';
  document.getElementById('media-info-ref-count').textContent = m.ref_count;
  document.getElementById('media-info-created').textContent = fmtDate(m.system_created);
  document.getElementById('media-edit-filename').value = m.filename || '';
  document.getElementById('media-edit-status').value = m.status || 'active';
  document.getElementById('media-edit-name').value = m.name || '';
  document.getElementById('media-edit-label').value = m.label || '';
  document.getElementById('media-edit-description').value = m.description || '';
  document.getElementById('media-edit-tags').value = (m.tags || []).join(', ');
  document.getElementById('media-edit-attributes').value = JSON.stringify(m.attributes || {}, null, 2);
  new bootstrap.Modal(document.getElementById('modal-media-edit')).show();
};

document.getElementById('btn-save-media-edit').addEventListener('click', async () => {
  const id = document.getElementById('media-edit-id').value;
  const data = {
    filename: document.getElementById('media-edit-filename').value.trim() || null,
    status: document.getElementById('media-edit-status').value,
    name: document.getElementById('media-edit-name').value.trim() || null,
    label: document.getElementById('media-edit-label').value.trim() || null,
    description: document.getElementById('media-edit-description').value.trim() || null,
    tags: parseTags(document.getElementById('media-edit-tags').value),
    attributes: parseJSON(document.getElementById('media-edit-attributes').value),
  };
  try {
    await HGAI_API.updateMedia(id, data);
    bootstrap.Modal.getInstance(document.getElementById('modal-media-edit'))?.hide();
    toast('Media updated');
    loadMedia();
  } catch (err) { toast(err.message, 'danger'); }
});

document.getElementById('btn-media-edit-download').addEventListener('click', () => {
  const id = document.getElementById('media-edit-id').value;
  downloadMediaFile(id);
});

function doDeleteMedia(id) {
  HGAI_API.deleteMedia(id).then(() => {
    toast('Media deleted');
    bootstrap.Modal.getInstance(document.getElementById('modal-media-edit'))?.hide();
    loadMedia();
  }).catch(err => toast(err.message, 'danger'));
}

document.getElementById('btn-media-edit-delete').addEventListener('click', () => {
  const id = document.getElementById('media-edit-id').value;
  confirmDelete(`Delete media "${id}"? This cannot be undone.`, () => doDeleteMedia(id));
});

window.deleteMediaRow = (id) => {
  confirmDelete(`Delete media "${id}"? This cannot be undone.`, () => doDeleteMedia(id));
};

document.getElementById('btn-create-node').addEventListener('click', () => openNodeModal());
document.getElementById('btn-refresh-nodes').addEventListener('click', () => loadNodes());
document.getElementById('node-show-media').addEventListener('change', () => loadNodes());
document.getElementById('node-status-filter').addEventListener('change', () => { State.nodesPage = 0; loadNodes(); });
['node-type-filter', 'node-search'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') { State.nodesPage = 0; loadNodes(); }
  });
});

async function openNodeModal(nodeId = null) {
  const modal = new bootstrap.Modal(document.getElementById('modal-node'));
  const isEdit = !!nodeId;
  document.getElementById('node-form-mode').value = isEdit ? 'edit' : 'create';
  document.getElementById('modal-node-title').textContent = isEdit ? `Edit: ${nodeId}` : 'New Hypernode';

  // Graph field: dropdown on create, read-only display on edit
  const graphSelectRow = document.getElementById('node-graph-select-row');
  const graphDisplayRow = document.getElementById('node-graph-display-row');
  if (isEdit) {
    graphSelectRow.classList.add('d-none');
    graphDisplayRow.classList.remove('d-none');
  } else {
    graphSelectRow.classList.remove('d-none');
    graphDisplayRow.classList.add('d-none');
    // Populate graph dropdown for create
    try {
      const items = await _fetchAndCacheGraphs();
      const sel = document.getElementById('node-graph-id');
      sel.innerHTML = '<option value="">— Select Hypergraph —</option>';
      items.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = g.space_id ? `${g.label} (${g.space_id}/${g.id})` : `${g.label} (${g.id})`;
        if (g.id === State.activeGraphId) opt.selected = true;
        sel.appendChild(opt);
      });
    } catch {}
  }

  if (isEdit && State.activeGraphId) {
    try {
      const spaceId = graphSpaceId(State.activeGraphId);
      const n = spaceId
        ? await HGAI_API.getSpaceNode(spaceId, State.activeGraphId, nodeId)
        : await HGAI_API.getNode(State.activeGraphId, nodeId);
      document.getElementById('node-graph-display').textContent = n.hypergraph_id || State.activeGraphId;
      document.getElementById('node-id').value = n.id; document.getElementById('node-id').readOnly = true;
      document.getElementById('node-label').value = n.label || '';
      document.getElementById('node-type').value = n.type || 'Entity';
      document.getElementById('node-description').value = n.description || '';
      document.getElementById('node-tags').value = (n.tags || []).join(', ');
      document.getElementById('node-status').value = n.status || 'active';
      document.getElementById('node-valid-from').value = n.valid_from ? n.valid_from.slice(0,16) : '';
      document.getElementById('node-valid-to').value = n.valid_to ? n.valid_to.slice(0,16) : '';
      document.getElementById('node-attributes').value = JSON.stringify(n.attributes || {}, null, 2);
      nodeMediaItems = (n.media || []).map(m => ({ ...m }));
      nodeDefaultMediaId = n.default_media_id || '';
      renderMediaList('node-media-list', nodeMediaItems);
    } catch {}
  } else if (!isEdit) {
    document.getElementById('form-node').reset();
    document.getElementById('node-id').readOnly = false;
    document.getElementById('node-attributes').value = '{}';
    document.getElementById('node-type').value = 'Entity';
    nodeMediaItems = [];
    nodeDefaultMediaId = '';
    renderMediaList('node-media-list', nodeMediaItems);
  }
  modal.show();
}

window.editNode = (id) => openNodeModal(id);
window.viewNode = async (id) => {
  const spaceId = graphSpaceId(State.activeGraphId);
  const n = spaceId
    ? await HGAI_API.getSpaceNode(spaceId, State.activeGraphId, id).catch(()=>null)
    : await HGAI_API.getNode(State.activeGraphId, id).catch(()=>null);
  showDetail(`Hypernode: ${id}`, n);
};
window.deleteNode = (id) => {
  confirmDelete(`Delete hypernode "${id}"?`, async () => {
    try {
      const spaceId = graphSpaceId(State.activeGraphId);
      if (spaceId) {
        await HGAI_API.deleteSpaceNode(spaceId, State.activeGraphId, id);
      } else {
        await HGAI_API.deleteNode(State.activeGraphId, id);
      }
      toast(`Hypernode "${id}" deleted`);
      loadNodes();
    } catch (err) { toast(err.message, 'danger'); }
  });
};

document.getElementById('btn-save-node').addEventListener('click', async () => {
  const mode = document.getElementById('node-form-mode').value;
  const targetGraphId = mode === 'create'
    ? document.getElementById('node-graph-id').value
    : State.activeGraphId;
  if (!targetGraphId) { toast('Select a hypergraph first', 'warning'); return; }
  const id = document.getElementById('node-id').value.trim();
  const vFrom = document.getElementById('node-valid-from').value;
  const vTo = document.getElementById('node-valid-to').value;

  const data = {
    id,
    label: document.getElementById('node-label').value.trim(),
    type: document.getElementById('node-type').value.trim() || 'Entity',
    description: document.getElementById('node-description').value.trim() || null,
    tags: parseTags(document.getElementById('node-tags').value),
    status: document.getElementById('node-status').value,
    valid_from: vFrom ? new Date(vFrom).toISOString() : null,
    valid_to: vTo ? new Date(vTo).toISOString() : null,
    attributes: parseJSON(document.getElementById('node-attributes').value),
    media: nodeMediaItems,
    default_media_id: nodeDefaultMediaId,
  };

  const targetSpaceId = graphSpaceId(targetGraphId);
  try {
    if (mode === 'create') {
      if (targetSpaceId) {
        await HGAI_API.createSpaceNode(targetSpaceId, targetGraphId, data);
      } else {
        await HGAI_API.createNode(targetGraphId, data);
      }
      // If we just created in a different graph, update the active graph so the table refreshes correctly
      if (targetGraphId !== State.activeGraphId) {
        State.activeGraphId = targetGraphId;
        document.getElementById('active-graph-select').value = targetGraphId;
        document.getElementById('nodes-graph-select').value = targetGraphId;
      }
      toast('Hypernode created');
    } else {
      if (targetSpaceId) {
        await HGAI_API.updateSpaceNode(targetSpaceId, targetGraphId, id, data);
      } else {
        await HGAI_API.updateNode(targetGraphId, id, data);
      }
      toast('Hypernode updated');
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-node'))?.hide();
    loadNodes();
  } catch (err) { toast(err.message, 'danger'); }
});

// ── Hyperedges ─────────────────────────────────────────────────────────────
async function loadEdges() {
  const screenSel = document.getElementById('edges-graph-select');
  if (screenSel.value) State.activeGraphId = screenSel.value;
  if (!State.activeGraphId) {
    document.getElementById('tbody-edges').innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">Select a hypergraph above</td></tr>';
    return;
  }
  const tbody = document.getElementById('tbody-edges');
  tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';

  const params = {
    skip: State.edgesPage * State.edgePageSize,
    limit: State.edgePageSize,
    relation: document.getElementById('edge-relation-filter').value.trim() || undefined,
    flavor: document.getElementById('edge-flavor-filter').value || undefined,
    node_id: document.getElementById('edge-node-filter').value.trim() || undefined,
    sort: sortParam(State.edgesSort),
  };
  updateSortIndicators('edges');

  const showMedia = document.getElementById('edge-show-media').checked;
  document.querySelector('#screen-edges thead .td-media')?.classList.toggle('d-none', !showMedia);

  const spaceId = graphSpaceId(State.activeGraphId);
  try {
    const resp = spaceId
      ? await HGAI_API.listSpaceEdges(spaceId, State.activeGraphId, params)
      : await HGAI_API.listEdges(State.activeGraphId, params);
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">No hyperedges found</td></tr>';
    } else {
      resp.items.forEach(e => {
        const membersSummary = (e.members || []).map(m => m.node_id).join(' · ') || '—';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="table-id-link" onclick="editEdge('${e.id||e.hyperkey}')"><code class="text-truncate-150" title="${escapeHtml(e.id||e.hyperkey)}">${escapeHtml(truncate(e.id||e.hyperkey, 24))}</code></td>
          <td class="td-media text-center ${showMedia ? '' : 'd-none'}">${showMedia ? mediaThumbCellHtml(e) : ''}</td>
          <td>${escapeHtml(e.label||'—')}</td>
          <td><strong>${escapeHtml(e.relation||'—')}</strong></td>
          <td><span class="badge badge-flavor">${escapeHtml(e.flavor||'—')}</span></td>
          <td><small class="text-muted" title="${membersSummary}">${truncate(membersSummary, 60)}</small></td>
          <td>${statusBadge(e.status)}</td>
          <td>${tagBadges(e.tags)}</td>
          <td class="text-end">
            <button class="btn btn-xs btn-outline-secondary me-1" onclick="viewEdge('${e.id||e.hyperkey}')"><i class="bi bi-eye"></i></button>
            <button class="btn btn-xs btn-outline-info me-1" onclick="editEdge('${e.id||e.hyperkey}')"><i class="bi bi-pencil"></i></button>
            <button class="btn btn-xs btn-outline-danger" onclick="deleteEdge('${e.id||e.hyperkey}')"><i class="bi bi-trash"></i></button>
          </td>`;
        tbody.appendChild(tr);
      });
      if (showMedia) await loadTableThumbnails(tbody, _edgeThumbUrls);
    }
    renderPagination('edges', resp.total, State.edgesPage, State.edgePageSize);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-create-edge').addEventListener('click', () => openEdgeModal());
document.getElementById('btn-refresh-edges').addEventListener('click', () => loadEdges());
document.getElementById('edge-show-media').addEventListener('change', () => loadEdges());
['edge-relation-filter', 'edge-node-filter'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') { State.edgesPage = 0; loadEdges(); }
  });
});
document.getElementById('edge-flavor-filter').addEventListener('change', () => { State.edgesPage = 0; loadEdges(); });

// Member builder
function addMemberRow(member = null) {
  const list = document.getElementById('edge-members-list');
  const idx = list.children.length;
  const div = document.createElement('div');
  div.className = 'member-row';
  div.innerHTML = `
    <input type="number" class="form-control form-control-sm member-seq" placeholder="seq" value="${member?.seq ?? idx}" min="0"/>
    <input type="text" class="form-control form-control-sm member-node-id" placeholder="node-id" value="${member?.node_id||''}"/>
    <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()"><i class="bi bi-x"></i></button>`;
  list.appendChild(div);
}

document.getElementById('btn-add-member').addEventListener('click', () => addMemberRow());

async function openEdgeModal(edgeId = null) {
  const modal = new bootstrap.Modal(document.getElementById('modal-edge'));
  const isEdit = !!edgeId;
  document.getElementById('edge-form-mode').value = isEdit ? 'edit' : 'create';
  document.getElementById('modal-edge-title').textContent = isEdit ? `Edit: ${edgeId}` : 'New Hyperedge';
  document.getElementById('edge-members-list').innerHTML = '';

  // Graph field: dropdown on create, read-only display on edit
  const graphSelectRow = document.getElementById('edge-graph-select-row');
  const graphDisplayRow = document.getElementById('edge-graph-display-row');
  if (isEdit) {
    graphSelectRow.classList.add('d-none');
    graphDisplayRow.classList.remove('d-none');
  } else {
    graphSelectRow.classList.remove('d-none');
    graphDisplayRow.classList.add('d-none');
    try {
      const items = await _fetchAndCacheGraphs();
      const sel = document.getElementById('edge-graph-id');
      sel.innerHTML = '<option value="">— Select Hypergraph —</option>';
      items.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = g.space_id ? `${g.label} (${g.space_id}/${g.id})` : `${g.label} (${g.id})`;
        if (g.id === State.activeGraphId) opt.selected = true;
        sel.appendChild(opt);
      });
    } catch {}
  }

  if (isEdit && State.activeGraphId) {
    try {
      const spaceId = graphSpaceId(State.activeGraphId);
      const e = spaceId
        ? await HGAI_API.getSpaceEdge(spaceId, State.activeGraphId, edgeId)
        : await HGAI_API.getEdge(State.activeGraphId, edgeId);
      document.getElementById('edge-graph-display').textContent = e.hypergraph_id || State.activeGraphId;
      document.getElementById('edge-id').value = e.id || '';
      document.getElementById('edge-id').readOnly = true;
      document.getElementById('edge-relation').value = e.relation || '';
      document.getElementById('edge-label').value = e.label || '';
      document.getElementById('edge-flavor').value = e.flavor || 'hub';
      document.getElementById('edge-status').value = e.status || 'active';
      document.getElementById('edge-tags').value = (e.tags || []).join(', ');
      document.getElementById('edge-valid-from').value = e.valid_from ? e.valid_from.slice(0,16) : '';
      document.getElementById('edge-valid-to').value = e.valid_to ? e.valid_to.slice(0,16) : '';
      document.getElementById('edge-attributes').value = JSON.stringify(e.attributes || {}, null, 2);
      (e.members || []).forEach(m => addMemberRow(m));
      edgeMediaItems = (e.media || []).map(m => ({ ...m }));
      edgeDefaultMediaId = e.default_media_id || '';
      renderMediaList('edge-media-list', edgeMediaItems);
    } catch {}
  } else if (!isEdit) {
    document.getElementById('form-edge').reset();
    document.getElementById('edge-id').readOnly = false;
    document.getElementById('edge-attributes').value = '{}';
    addMemberRow({ seq: 0 });
    addMemberRow({ seq: 1 });
    edgeMediaItems = [];
    edgeDefaultMediaId = '';
    renderMediaList('edge-media-list', edgeMediaItems);
  }
  modal.show();
}

window.editEdge = (id) => openEdgeModal(id);
window.viewEdge = async (id) => {
  const spaceId = graphSpaceId(State.activeGraphId);
  const e = spaceId
    ? await HGAI_API.getSpaceEdge(spaceId, State.activeGraphId, id).catch(()=>null)
    : await HGAI_API.getEdge(State.activeGraphId, id).catch(()=>null);
  showDetail(`Hyperedge: ${id}`, e);
};
window.deleteEdge = (id) => {
  confirmDelete(`Delete hyperedge "${id}"?`, async () => {
    try {
      const spaceId = graphSpaceId(State.activeGraphId);
      if (spaceId) {
        await HGAI_API.deleteSpaceEdge(spaceId, State.activeGraphId, id);
      } else {
        await HGAI_API.deleteEdge(State.activeGraphId, id);
      }
      toast(`Hyperedge deleted`);
      loadEdges();
    } catch (err) { toast(err.message, 'danger'); }
  });
};

document.getElementById('btn-save-edge').addEventListener('click', async () => {
  const mode = document.getElementById('edge-form-mode').value;
  const targetGraphId = mode === 'create'
    ? document.getElementById('edge-graph-id').value
    : State.activeGraphId;
  if (!targetGraphId) { toast('Select a hypergraph first', 'warning'); return; }
  const id = document.getElementById('edge-id').value.trim() || null;

  // Collect members
  const memberRows = document.getElementById('edge-members-list').querySelectorAll('.member-row');
  const members = Array.from(memberRows).map((row, i) => ({
    node_id: row.querySelector('.member-node-id').value.trim(),
    seq: parseInt(row.querySelector('.member-seq').value) || i,
  })).filter(m => m.node_id);

  const vFrom = document.getElementById('edge-valid-from').value;
  const vTo = document.getElementById('edge-valid-to').value;

  const data = {
    id,
    relation: document.getElementById('edge-relation').value.trim(),
    label: document.getElementById('edge-label').value.trim() || null,
    flavor: document.getElementById('edge-flavor').value,
    status: document.getElementById('edge-status').value,
    tags: parseTags(document.getElementById('edge-tags').value),
    valid_from: vFrom ? new Date(vFrom).toISOString() : null,
    valid_to: vTo ? new Date(vTo).toISOString() : null,
    attributes: parseJSON(document.getElementById('edge-attributes').value),
    members,
    media: edgeMediaItems,
    default_media_id: edgeDefaultMediaId,
  };

  const targetSpaceId = graphSpaceId(targetGraphId);
  try {
    if (mode === 'create') {
      if (targetSpaceId) {
        await HGAI_API.createSpaceEdge(targetSpaceId, targetGraphId, data);
      } else {
        await HGAI_API.createEdge(targetGraphId, data);
      }
      if (targetGraphId !== State.activeGraphId) {
        State.activeGraphId = targetGraphId;
        document.getElementById('active-graph-select').value = targetGraphId;
        document.getElementById('nodes-graph-select').value = targetGraphId;
        document.getElementById('edges-graph-select').value = targetGraphId;
      }
      toast('Hyperedge created');
    } else {
      if (targetSpaceId) {
        await HGAI_API.updateSpaceEdge(targetSpaceId, targetGraphId, id, data);
      } else {
        await HGAI_API.updateEdge(targetGraphId, id, data);
      }
      toast('Hyperedge updated');
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-edge'))?.hide();
    loadEdges();
  } catch (err) { toast(err.message, 'danger'); }
});

// ── Visualize (3D) ────────────────────────────────────────────────────────
// Structure follows docs/architecture/hypergraph-3d-viz.md: a hyperedge is its
// own node, linked via a virtual "hyperedge" edge to a virtual "members" node,
// which fans out — via edges labeled with the hyperedge's relation — to each
// member node. This keeps every hyperedge, of any arity, a first-class,
// uniformly clickable element instead of a special-cased plain line.
const VIZ_TYPE_PALETTE = ['#4f46e5','#059669','#0891b2','#d97706','#dc2626','#7c3aed','#db2777','#65a30d','#0d9488','#c026d3','#2563eb','#ea580c'];
// Edge-kind colors, matching docs/design/hypergraphai-hyperedge-virtual-3d-graph-via-representation.png:
// the hyperedge→members link is always "flavor/<flavor>" in magenta; every members→member
// link is always "rel:<relation>" in amber. Color encodes structural role, not the specific
// flavor/relation value — that's carried in the label text instead.
// The hyperedge->members link is colored by the hyperedge's flavor, so the
// topology pattern it implies (hub/symmetric/direct/...) reads at a glance.
const VIZ_FLAVOR_LINK_COLOR = {
  hub: '#f97316',                 // orange
  symmetric: '#22c55e',           // green
  direct: '#06b6d4',              // cyan
  transitive: '#8b5cf6',          // violet
  'inverse-transitive': '#f43f5e', // rose
};
const VIZ_LINK_RELATION_COLOR = '#f59e0b';
const VIZ_LINK_FIRST_MEMBER_COLOR = '#3b82f6';
const VIZ_DIM_NODE_COLOR = '#2a2a3d';
const VIZ_DIM_LINK_COLOR = '#20202f';
const VIZ_STRUCTURAL_COLOR = '#9ca3af';
const VIZ_FETCH_LIMIT = 500;
// Must match the .nodeRelSize() call in initViz3D() — kept as one constant so
// thumbnail sizing (vizSphereRadius) can never drift out of sync with the
// actual sphere size 3d-force-graph renders.
const VIZ_NODE_REL_SIZE = 3;
// Vertical tier (world Y) each node kind is pulled toward, echoing the reference
// diagram's top-down layout: hyperedge on top, its virtual members-hub in the
// middle, actual member hypernodes at the bottom.
const VIZ_LAYER_Y = { henode: 160, members: 0, hnode: -160 };

let vizRotateTimer = null;
let vizRotateAngle = 0;
let vizLabelsEnabled = true;
let vizMediaEnabled = false;
const vizLabelNodeEls = new Map();
const vizLabelLinkEls = new Map();
const vizThumbNodeEls = new Map();
let _vizThumbUrls = [];

function vizColorForType(type) {
  const key = type || 'Entity';
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  return VIZ_TYPE_PALETTE[hash % VIZ_TYPE_PALETTE.length];
}

function vizEsc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function populateVizGraphSelect() {
  const sel = document.getElementById('viz-graph-select');
  const picked = new Set(Array.from(sel.selectedOptions).map(o => o.value));
  try {
    const items = await _fetchAndCacheGraphs();
    sel.innerHTML = '';
    items.forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id;
      opt.textContent = g.space_id ? `${g.label} (${g.space_id}/${g.id})` : `${g.label} (${g.id})`;
      if (picked.size ? picked.has(g.id) : g.id === State.activeGraphId) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch {}
}

function loadVizScreen() {
  populateVizGraphSelect();
  if (!State.viz3d) initViz3D();
}

function vizShowDetail(raw) {
  document.getElementById('viz-detail-empty').classList.add('d-none');
  const content = document.getElementById('viz-detail-content');
  content.classList.remove('d-none');
  content.textContent = JSON.stringify(raw, null, 2);
}

function vizClearDetail() {
  document.getElementById('viz-detail-empty').classList.remove('d-none');
  document.getElementById('viz-detail-content').classList.add('d-none');
}

function vizResizeCanvas() {
  if (!State.viz3d) return;
  const el = document.getElementById('viz-cy-wrapper');
  if (!el || !el.clientWidth || !el.clientHeight) return;
  State.viz3d.width(el.clientWidth).height(el.clientHeight);
}

// Assigns a distinct curvature to every link so that multiple relationships
// fanning out from the same source node (e.g. a hyperedge's "members" node
// with many participants) render as visually separate arcs instead of
// overlapping straight lines.
function vizAssignCurvature(links) {
  const groups = new Map();
  links.forEach(l => {
    const src = typeof l.source === 'object' ? l.source.id : l.source;
    if (!groups.has(src)) groups.set(src, []);
    groups.get(src).push(l);
  });
  groups.forEach(group => {
    const n = group.length;
    group.forEach((l, i) => { l.curvature = n <= 1 ? 0 : (i - (n - 1) / 2) * 0.28; });
  });
}

// Projects a 3D world point to normalized (0..1) canvas space using the live
// camera's own view/projection matrices — plain arithmetic on THREE.Matrix4's
// `.elements` (column-major), so no THREE.js reference is needed on our side.
function vizProjectPoint(camera, x, y, z) {
  const ve = camera.matrixWorldInverse.elements;
  const vx = ve[0] * x + ve[4] * y + ve[8] * z + ve[12];
  const vy = ve[1] * x + ve[5] * y + ve[9] * z + ve[13];
  const vz = ve[2] * x + ve[6] * y + ve[10] * z + ve[14];
  const vw = ve[3] * x + ve[7] * y + ve[11] * z + ve[15];
  const pe = camera.projectionMatrix.elements;
  const cx = pe[0] * vx + pe[4] * vy + pe[8] * vz + pe[12] * vw;
  const cy = pe[1] * vx + pe[5] * vy + pe[9] * vz + pe[13] * vw;
  const cw = pe[3] * vx + pe[7] * vy + pe[11] * vz + pe[15] * vw;
  if (cw <= 0) return null;
  // For a standard (un-skewed) perspective projection matrix, clip-space w
  // equals the point's camera-space depth (-viewZ) — i.e. distance along the
  // view axis — so it's returned here too rather than recomputed separately
  // wherever perspective-correct on-screen sizing (not just position) is needed.
  return { x: cx / cw * 0.5 + 0.5, y: 1 - (cy / cw * 0.5 + 0.5), dist: cw };
}

// The world-space radius 3d-force-graph itself renders each node's sphere at
// (three-forcegraph's documented convention: radius = cbrt(val) * nodeRelSize) —
// replicated here (never read back from the library) so thumbnail sizing can
// match it exactly without needing a live reference into the render internals.
function vizSphereRadius(val) {
  return Math.cbrt(val || 1) * VIZ_NODE_REL_SIZE;
}

// Perspective-correct on-screen size (px) of a world-space diameter at a given
// camera-space distance, for a vertical field-of-view `fovDeg` rendered into a
// viewport `viewportHeightPx` tall — the standard "apparent size" formula:
// the visible world height at that distance is 2*dist*tan(fov/2), which maps
// to viewportHeightPx pixels.
function vizWorldSizeToPx(worldDiameter, dist, fovDeg, viewportHeightPx) {
  const visibleHeight = 2 * dist * Math.tan(fovDeg * Math.PI / 360);
  return (worldDiameter / visibleHeight) * viewportHeightPx;
}

// Every label/thumbnail/link-label lives as a flat 2D div in #viz-label-layer,
// stacked by plain DOM/paint order by default — with no relation at all to
// actual 3D depth, so an element for something far from the camera could
// paint over one for something close just by virtue of being added to the
// DOM later. Deriving each element's z-index from its camera distance every
// frame (closer = higher) keeps their stacking consistent with the scene's
// real depth ordering, across all three element kinds on one shared scale
// (so a close link label correctly outranks a far node label, etc.).
// #viz-label-layer is its own isolated stacking context (see CSS), so these
// values can never affect anything outside that layer.
function vizZIndexForDist(dist) {
  return Math.round(1000000 - dist * 10);
}

function vizClearLabelLayer() {
  document.getElementById('viz-label-layer').innerHTML = '';
  vizLabelNodeEls.clear();
  vizLabelLinkEls.clear();
  vizThumbNodeEls.clear();
  _vizThumbUrls.forEach(u => URL.revokeObjectURL(u));
  _vizThumbUrls = [];
}

// An hnode/henode's default media — same MediaRef-cache lookup as the
// Nodes/Edges table thumbnails, so no extra round-trip is needed to know its
// content type before deciding whether it's even showable as a static image.
function vizDefaultMediaRefFor(raw) {
  if (!raw || !raw.default_media_id) return null;
  return (raw.media || []).find(m => m.media_id === raw.default_media_id) || null;
}

function vizBuildLabelLayer(nodes, links) {
  vizClearLabelLayer();
  const layer = document.getElementById('viz-label-layer');
  const frag = document.createDocumentFragment();
  nodes.forEach(n => {
    // The virtual "members" node is purely structural (fans a hyperedge out
    // to its participants) — labeling it just adds visual clutter repeated
    // once per hyperedge, so it's excluded from the label layer entirely.
    // Its own tooltip (nodeLabel in initViz3D) still explains it on hover.
    if (n.kind !== 'members') {
      const el = document.createElement('div');
      el.className = 'viz-label viz-label-node';
      el.textContent = n.label;
      frag.appendChild(el);
      vizLabelNodeEls.set(n.id, { el, node: n });
    }

    if (n.kind === 'hnode' || n.kind === 'henode') {
      const ref = vizDefaultMediaRefFor(n.raw);
      if (ref && ref.content_type && ref.content_type.startsWith('image/')) {
        const img = document.createElement('img');
        img.className = 'viz-thumb';
        img.dataset.thumbMediaId = ref.media_id;
        frag.appendChild(img);
        vizThumbNodeEls.set(n.id, { el: img, node: n, aspect: 1 });
      }
    }
  });
  links.forEach(l => {
    if (!l.label) return;
    const el = document.createElement('div');
    el.className = 'viz-label viz-label-link';
    el.style.color = l.color;
    el.textContent = l.label;
    frag.appendChild(el);
    vizLabelLinkEls.set(l, { el, link: l });
  });
  layer.appendChild(frag);
  if (vizMediaEnabled) vizLoadThumbnails();
}

// Fetches each thumbnail as an authenticated blob (same pattern used
// everywhere else media is displayed in this app) and swaps it into the
// already-positioned <img> once it arrives; a failed fetch just removes that
// node's thumbnail from tracking rather than leaving a broken-image icon
// floating in the 3D scene.
async function vizLoadThumbnails() {
  _vizThumbUrls.forEach(u => URL.revokeObjectURL(u));
  _vizThumbUrls = [];
  await Promise.all([...vizThumbNodeEls.entries()].map(async ([id, entry]) => {
    const mediaId = entry.el.dataset.thumbMediaId;
    try {
      const blob = await HGAI_API.downloadMedia(mediaId);
      const url = URL.createObjectURL(blob);
      _vizThumbUrls.push(url);
      // Wait for the browser to decode the image so its real dimensions are
      // known before it's ever sized — vizLabelTick uses this to preserve the
      // image's own aspect ratio rather than forcing it into a fixed square.
      await new Promise((resolve, reject) => {
        entry.el.onload = resolve;
        entry.el.onerror = reject;
        entry.el.src = url;
      });
      if (entry.el.naturalWidth && entry.el.naturalHeight) {
        entry.aspect = entry.el.naturalWidth / entry.el.naturalHeight;
      }
    } catch {
      entry.el.remove();
      vizThumbNodeEls.delete(id);
    }
  }));
}

function vizLabelTick() {
  requestAnimationFrame(vizLabelTick);
  if (!State.viz3d) return;
  if (document.getElementById('screen-viz').classList.contains('d-none')) return;
  if (!vizLabelsEnabled && !vizMediaEnabled) return;
  const wrapper = document.getElementById('viz-cy-wrapper');
  const w = wrapper.clientWidth, h = wrapper.clientHeight;
  if (!w || !h) return;
  const camera = State.viz3d.camera();

  if (vizLabelsEnabled) {
    vizLabelNodeEls.forEach(({ el, node }) => {
      const p = vizProjectPoint(camera, node.x || 0, node.y || 0, node.z || 0);
      if (!p || p.x < -0.1 || p.x > 1.1 || p.y < -0.1 || p.y > 1.1) { el.style.display = 'none'; return; }
      el.style.display = '';
      el.style.left = (p.x * w) + 'px';
      el.style.top = (p.y * h) + 'px';
      el.style.zIndex = vizZIndexForDist(p.dist);
    });

    vizLabelLinkEls.forEach(({ el, link }) => {
      const s = typeof link.source === 'object' ? link.source : null;
      const t = typeof link.target === 'object' ? link.target : null;
      if (!s || !t) { el.style.display = 'none'; return; }
      const p = vizProjectPoint(camera, (s.x + t.x) / 2, (s.y + t.y) / 2, (s.z + t.z) / 2);
      if (!p || p.x < -0.1 || p.x > 1.1 || p.y < -0.1 || p.y > 1.1) { el.style.display = 'none'; return; }
      el.style.display = '';
      el.style.left = (p.x * w) + 'px';
      el.style.top = (p.y * h) + 'px';
      el.style.zIndex = vizZIndexForDist(p.dist);
    });
  }

  if (vizMediaEnabled) {
    vizThumbNodeEls.forEach(({ el, node, aspect }) => {
      const p = vizProjectPoint(camera, node.x || 0, node.y || 0, node.z || 0);
      if (!p || p.x < -0.1 || p.x > 1.1 || p.y < -0.1 || p.y > 1.1) { el.style.display = 'none'; return; }
      el.style.display = '';
      // Perspective-correct: the larger of the image's two dimensions is
      // sized to match the node's actual sphere at its current camera
      // distance (so zooming grows/shrinks it exactly as it does the sphere
      // it's standing in for), and the other dimension follows the image's
      // own natural aspect ratio — never stretched or cropped to a square.
      const diameter = 2 * vizSphereRadius(node.val);
      const targetSize = Math.max(6, Math.min(vizWorldSizeToPx(diameter, p.dist, camera.fov, h), 400));
      const ar = aspect || 1;
      const width = ar >= 1 ? targetSize : targetSize * ar;
      const height = ar >= 1 ? targetSize / ar : targetSize;
      el.style.width = width + 'px';
      el.style.height = height + 'px';
      el.style.left = (p.x * w) + 'px';
      // Nudged up by roughly its own half-height (not a fixed pixel offset)
      // so the label underneath it — sized independently — stays legible.
      el.style.top = (p.y * h - height * 0.55) + 'px';
      el.style.zIndex = vizZIndexForDist(p.dist);
    });
  }
}

// A d3-force-compatible custom force (the standard initialize(nodes)/force(alpha)
// contract) that gently pulls each node toward its kind's vertical tier, so the
// scene settles into the reference diagram's hyperedge/members/entity layering
// instead of one undifferentiated organic cloud.
function vizLayerForce() {
  let nodes = [];
  function force(alpha) {
    const k = alpha * 0.3;
    nodes.forEach(n => {
      const targetY = VIZ_LAYER_Y[n.kind] ?? 0;
      n.vy = (n.vy || 0) + (targetY - n.y) * k;
    });
  }
  force.initialize = ns => { nodes = ns; };
  return force;
}

function initViz3D() {
  const container = document.getElementById('viz-canvas');
  const g = ForceGraph3D()(container)
    .backgroundColor('#0f0f1a')
    .showNavInfo(false)
    .nodeRelSize(VIZ_NODE_REL_SIZE)
    .d3Force('layer', vizLayerForce())
    .nodeVal(n => n.val)
    .nodeColor(n => n._dim ? VIZ_DIM_NODE_COLOR : n.color)
    .nodeLabel(n => {
      if (n.kind === 'members') return `<div>members <span style="opacity:.6">(virtual)</span></div>`;
      if (n.kind === 'henode') {
        return `<div>${vizEsc(n.label)}<br/><span style="opacity:.6">${vizEsc(n.relation)} · flavor:${vizEsc(n.flavor)} · ${n.arity} member${n.arity === 1 ? '' : 's'}</span></div>`;
      }
      return `<div>${vizEsc(n.label)}<br/><span style="opacity:.6">${vizEsc(n.type)}</span></div>`;
    })
    .linkColor(l => l._dim ? VIZ_DIM_LINK_COLOR : l.color)
    .linkWidth(l => l.kind === 'hyperedge' ? 0.8 : 0.5)
    .linkCurvature(l => l.curvature || 0)
    .linkOpacity(0.75)
    .linkLabel(l => vizEsc(l.label))
    .linkDirectionalArrowLength(4)
    .linkDirectionalArrowRelPos(1)
    .linkDirectionalArrowColor(l => l._dim ? VIZ_DIM_LINK_COLOR : l.color)
    .onNodeClick(node => {
      const dist = 90;
      const ratio = 1 + dist / (Math.hypot(node.x || 0, node.y || 0, node.z || 0) || 1);
      g.cameraPosition({ x: node.x * ratio, y: node.y * ratio, z: node.z * ratio }, node, 700);
      if (node.kind === 'members') {
        vizShowDetail({
          virtual: true,
          note: "Structural node representing this hyperedge's member set — not a persisted entity.",
          hyperedge_id: node.parentRaw?.id || node.parentRaw?.hyperkey,
          relation: node.parentRaw?.relation,
          member_count: (node.parentRaw?.members || []).length,
        });
      } else {
        vizShowDetail(node.raw);
      }
    })
    .onLinkClick(link => {
      if (link.kind === 'hyperedge') {
        vizShowDetail({
          virtual: true,
          note: 'Structural link connecting the hyperedge node to its virtual members node.',
          hyperedge_id: link.parentRaw?.id || link.parentRaw?.hyperkey,
        });
      } else {
        vizShowDetail(link.raw);
      }
    })
    .onBackgroundClick(vizClearDetail);

  State.viz3d = g;
  vizResizeCanvas();
  window.addEventListener('resize', vizResizeCanvas);

  // Shift+left-click-drag pans the camera (left/right/up/down) instead of
  // orbiting it. TrackballControls (3d-force-graph's default controls) reads
  // `mouseButtons.LEFT` fresh at the start of each drag, so a capture-phase
  // mousedown listener that reassigns it just before the library's own
  // pointerdown handler runs is enough — no separate keydown/keyup state to
  // track, and it can't get stuck if a keyup is ever missed (e.g. losing
  // focus mid-drag), since it's re-derived from the live shiftKey flag on
  // every mousedown. Right-click already pans by default in this library, so
  // its existing mapping is reused rather than hardcoding THREE's MOUSE enum.
  const controls = g.controls();
  if (controls && controls.mouseButtons) {
    const rotateAction = controls.mouseButtons.LEFT;
    const panAction = controls.mouseButtons.RIGHT;
    container.addEventListener('mousedown', ev => {
      controls.mouseButtons.LEFT = ev.shiftKey ? panAction : rotateAction;
    }, true);
  }
}

async function fetchGraphElements(graphId) {
  const spaceId = graphSpaceId(graphId);
  const status = document.getElementById('viz-status-filter').value || undefined;
  const [nodesResp, edgesResp] = await Promise.all([
    spaceId ? HGAI_API.listSpaceNodes(spaceId, graphId, { limit: VIZ_FETCH_LIMIT, status })
            : HGAI_API.listNodes(graphId, { limit: VIZ_FETCH_LIMIT, status }),
    spaceId ? HGAI_API.listSpaceEdges(spaceId, graphId, { limit: VIZ_FETCH_LIMIT })
            : HGAI_API.listEdges(graphId, { limit: VIZ_FETCH_LIMIT }),
  ]);
  return {
    nodes: nodesResp.items || [], nodesTotal: nodesResp.total || 0,
    edges: edgesResp.items || [], edgesTotal: edgesResp.total || 0,
  };
}

async function renderViz() {
  const sel = document.getElementById('viz-graph-select');
  const graphIds = Array.from(sel.selectedOptions).map(o => o.value);
  if (!graphIds.length) { toast('Select at least one hypergraph', 'warning'); return; }
  if (!State.viz3d) initViz3D();

  document.getElementById('viz-empty-state').classList.add('d-none');
  vizResizeCanvas();

  const nodes = [];
  const links = [];
  const typeCount = {};
  const flavorSeen = new Set();
  let truncated = false;
  let hyperedgeCount = 0;

  try {
    for (const gid of graphIds) {
      const { nodes: rawNodes, edges, nodesTotal, edgesTotal } = await fetchGraphElements(gid);
      if (rawNodes.length < nodesTotal || edges.length < edgesTotal) truncated = true;

      const nodeIdSet = new Set();
      const hedgeIdSet = new Set();
      rawNodes.forEach(n => {
        nodeIdSet.add(n.id);
        const type = n.type || 'Entity';
        typeCount[type] = (typeCount[type] || 0) + 1;
        nodes.push({
          id: `${gid}::${n.id}`, kind: 'hnode', label: n.label || n.id, type,
          color: vizColorForType(type), val: 4, graphId: gid, raw: n,
        });
      });
      edges.forEach(e => {
        const k = e.id || e.hyperkey;
        if (k) hedgeIdSet.add(k);
      });

      // A member's node_id may point at either a hypernode or another
      // hyperedge — hyperedges are first-class and may themselves be members
      // of a hyperedge (see docs/architecture/hypergraph_ai_design_notes.md:
      // "HypergraphAI hyperedges are treated as hypernodes") — so resolve
      // against both id spaces, mapping to whichever viz node id scheme that
      // target actually uses, before treating a member as unresolvable.
      const vizMemberTargetId = nodeId => {
        if (nodeIdSet.has(nodeId)) return `${gid}::${nodeId}`;
        if (hedgeIdSet.has(nodeId)) return `${gid}::he::${nodeId}`;
        return null;
      };

      edges.forEach(e => {
        const members = (e.members || []).slice().sort((a, b) => (a.seq || 0) - (b.seq || 0));
        const flavor = e.flavor || 'hub';
        const validMembers = members
          .map(m => ({ ...m, vizTargetId: vizMemberTargetId(m.node_id) }))
          .filter(m => m.vizTargetId);
        hyperedgeCount++;
        flavorSeen.add(flavor);
        const heid = `${gid}::he::${e.id || e.hyperkey}`;
        const membersId = `${heid}::members`;

        // edge:<id> (node) — the hyperedge's own identity, matching the top box
        // in docs/design/hypergraphai-hyperedge-virtual-3d-graph-via-representation.png.
        // Always created, even with zero currently-resolvable members, so that
        // any OTHER hyperedge referencing this one as a member has a real node
        // to link to, and so a hyperedge — a first-class element — is never
        // silently hidden just because its own members didn't resolve.
        nodes.push({
          id: heid, kind: 'henode', label: e.label || e.id || e.hyperkey || '(hyperedge)',
          flavor, color: VIZ_STRUCTURAL_COLOR, val: Math.min(6 + validMembers.length, 16),
          arity: validMembers.length, relation: e.relation, graphId: gid, raw: e,
        });
        if (!validMembers.length) return;

        // "members" (virtual node)
        nodes.push({
          id: membersId, kind: 'members', label: 'members', color: VIZ_STRUCTURAL_COLOR,
          val: 1.6, graphId: gid, raw: null, parentRaw: e,
        });
        // "hyperedge" (virtual edge): hyperedge-node -> members-node, typed
        // by the hyperedge's flavor (e.g. "flavor:hub") per the reference diagram.
        links.push({
          source: heid, target: membersId, kind: 'hyperedge', label: `flavor:${flavor}`,
          color: VIZ_FLAVOR_LINK_COLOR[flavor] || VIZ_STRUCTURAL_COLOR, raw: null, parentRaw: e,
        });
        // relation-labeled edges: members-node -> each member (a hypernode's
        // hnode, or another hyperedge's henode). The first member (lowest seq)
        // gets a distinct blue so it stands out from the rest.
        validMembers.forEach((m, i) => {
          links.push({
            source: membersId, target: m.vizTargetId, kind: 'relation',
            label: e.relation || '', seq: m.seq,
            color: i === 0 ? VIZ_LINK_FIRST_MEMBER_COLOR : VIZ_LINK_RELATION_COLOR, raw: e,
          });
        });
      });
    }

    vizAssignCurvature(links);
    State.viz3d.graphData({ nodes, links });
    vizBuildLabelLayer(nodes, links);
    buildVizLegend(typeCount, flavorSeen);
    document.getElementById('viz-stats').textContent =
      `${nodes.filter(n => n.kind === 'hnode').length} hypernodes · ${hyperedgeCount} hyperedges`;
    if (truncated) toast(`Some graphs exceeded the display limit (${VIZ_FETCH_LIMIT}) — showing a partial view`, 'warning');
    if (!nodes.length) {
      const empty = document.getElementById('viz-empty-state');
      empty.classList.remove('d-none');
      empty.querySelector('p').textContent = 'No hypernodes found for the selected hypergraph(s).';
    } else {
      setTimeout(() => State.viz3d?.zoomToFit(600, 60), 500);
    }
  } catch (err) {
    toast(err.message, 'danger');
  }
}

function vizClear() {
  if (State.viz3d) State.viz3d.graphData({ nodes: [], links: [] });
  vizClearLabelLayer();
  document.getElementById('viz-legend').innerHTML = '';
  document.getElementById('viz-stats').textContent = '';
  document.getElementById('viz-search').value = '';
  vizClearDetail();
  const empty = document.getElementById('viz-empty-state');
  empty.querySelector('p').innerHTML = 'Select one or more hypergraphs and click <strong>Render</strong> to visualize in 3D.';
  empty.classList.remove('d-none');
}

function buildVizLegend(typeCount, flavorSeen) {
  const el = document.getElementById('viz-legend');
  el.innerHTML = '';
  Object.keys(typeCount).sort().forEach(type => {
    const item = document.createElement('div');
    item.className = 'viz-legend-item';
    item.innerHTML = `<span class="viz-legend-swatch" style="background:${vizColorForType(type)}"></span>${type} (${typeCount[type]})`;
    item.addEventListener('click', () => toggleVizType(type, item));
    el.appendChild(item);
  });
  Array.from(flavorSeen).sort().forEach(flavor => {
    const item = document.createElement('div');
    item.className = 'viz-legend-item';
    const color = VIZ_FLAVOR_LINK_COLOR[flavor] || VIZ_STRUCTURAL_COLOR;
    item.innerHTML = `<span class="viz-legend-swatch bag" style="background:${color}"></span>flavor:${flavor}`;
    el.appendChild(item);
  });
  if (flavorSeen.size) {
    [
      ['rel:*  edge', VIZ_LINK_RELATION_COLOR],
      ['rel:*  edge (first member)', VIZ_LINK_FIRST_MEMBER_COLOR],
    ].forEach(([label, color]) => {
      const item = document.createElement('div');
      item.className = 'viz-legend-item';
      item.innerHTML = `<span class="viz-legend-swatch bag" style="background:${color}"></span>${label}`;
      el.appendChild(item);
    });
  }
}

function vizRecomputeDim() {
  if (!State.viz3d) return;
  const data = State.viz3d.graphData();
  data.nodes.forEach(n => { n._dim = !!(n._typeHidden || n._searchDim); });
  data.links.forEach(l => {
    const s = typeof l.source === 'object' ? l.source : data.nodes.find(n => n.id === l.source);
    const t = typeof l.target === 'object' ? l.target : data.nodes.find(n => n.id === l.target);
    l._dim = !!(s && s._dim) || !!(t && t._dim);
  });
  const g = State.viz3d;
  g.nodeColor(g.nodeColor()).linkColor(g.linkColor()).linkDirectionalArrowColor(g.linkDirectionalArrowColor());
}

function toggleVizType(type, item) {
  if (!State.viz3d) return;
  const hidden = item.classList.toggle('dimmed');
  State.viz3d.graphData().nodes.forEach(n => { if (n.type === type) n._typeHidden = hidden; });
  vizRecomputeDim();
}

function vizStartAutoRotate() {
  if (vizRotateTimer) return;
  vizRotateTimer = setInterval(() => {
    if (!State.viz3d || document.getElementById('screen-viz').classList.contains('d-none')) return;
    const pos = State.viz3d.cameraPosition();
    const r = Math.hypot(pos.x, pos.z) || 400;
    vizRotateAngle += 0.003;
    State.viz3d.cameraPosition({ x: r * Math.sin(vizRotateAngle), y: pos.y, z: r * Math.cos(vizRotateAngle) });
  }, 30);
}

function vizStopAutoRotate() {
  if (vizRotateTimer) { clearInterval(vizRotateTimer); vizRotateTimer = null; }
}

document.getElementById('btn-viz-render').addEventListener('click', renderViz);
document.getElementById('btn-viz-fit').addEventListener('click', () => State.viz3d?.zoomToFit(600, 60));
document.getElementById('btn-viz-clear').addEventListener('click', vizClear);
document.getElementById('viz-auto-rotate').addEventListener('change', function() {
  this.checked ? vizStartAutoRotate() : vizStopAutoRotate();
});
document.getElementById('viz-show-labels').addEventListener('change', function() {
  vizLabelsEnabled = this.checked;
  if (!vizLabelsEnabled) {
    vizLabelNodeEls.forEach(({ el }) => { el.style.display = 'none'; });
    vizLabelLinkEls.forEach(({ el }) => { el.style.display = 'none'; });
  }
});
document.getElementById('viz-show-media').addEventListener('change', function() {
  vizMediaEnabled = this.checked;
  if (vizMediaEnabled) {
    vizLoadThumbnails();
  } else {
    vizThumbNodeEls.forEach(({ el }) => { el.style.display = 'none'; });
  }
});
document.getElementById('viz-search').addEventListener('input', function() {
  if (!State.viz3d) return;
  const q = this.value.trim().toLowerCase();
  State.viz3d.graphData().nodes.forEach(n => { n._searchDim = q ? !(n.label || '').toLowerCase().includes(q) : false; });
  vizRecomputeDim();
});

vizLabelTick();

// ── JSON syntax highlighter ────────────────────────────────────────────────
function syntaxHighlightJson(obj) {
  const json = JSON.stringify(obj, null, 2);
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
    match => {
      let cls = 'json-number';
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? 'json-key' : 'json-string';
      } else if (/true|false/.test(match)) {
        cls = 'json-bool';
      } else if (/null/.test(match)) {
        cls = 'json-null';
      }
      return `<span class="${cls}">${match.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</span>`;
    }
  );
}

// ── Query (HQL) ────────────────────────────────────────────────────────────
const HQL_EXAMPLES = [
  {
    title: 'List all nodes in a graph',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hypernode\n  return:\n    - id\n    - label\n    - type\n    - attributes`
  },
  {
    title: 'Find hyperedges by relation',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hyperedge\n    relation: has-member\n  return:\n    - id\n    - relation\n    - members\n    - attributes\n  as: memberships`
  },
  {
    title: 'Point-in-time query (1940)',
    hql: `hql:\n  from: hello-world\n  at: "1940-06-01T00:00:00Z"\n  match:\n    type: hyperedge\n    relation: has-member\n  return:\n    - members\n    - attributes\n    - valid_from\n    - valid_to`
  },
  {
    title: 'Filter by tags',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hyperedge\n  where:\n    tags:\n      - original\n  return:\n    - id\n    - relation\n    - members\n    - tags`
  },
  {
    title: 'Find siblings (symmetric edges)',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hyperedge\n    relation: sibling\n    flavor: symmetric\n  return:\n    - members\n    - attributes`
  },
  {
    title: 'Aggregate: count by relation',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hyperedge\n  return:\n    - relation\n  aggregate:\n    count: true\n    group_by: relation`
  },
  {
    title: 'Multi-graph composition',
    hql: `hql:\n  from:\n    - graph-1\n    - graph-2\n  match:\n    type: hypernode\n    node_type: Person\n  return:\n    - id\n    - label\n    - attributes`
  },
  {
    title: 'Find edges containing a specific node',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hyperedge\n    nodes:\n      - moe-howard\n  return:\n    - id\n    - relation\n    - members`
  },
  {
    title: 'PIT — group members via rel:member hyperedges',
    hql: `hql:\n  from:\n    - hg-alpha\n  at: "2026-01-01T00:00:00"\n  match:\n    type: hyperedge\n    relation: "rel:member"\n  where:\n    members.node_id: "group:three-stooges"\n  return:\n    - id\n    - relation\n    - members`
  },
  {
    title: 'Positional member filter — first member is a specific node (seq)',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hyperedge\n    relation: "rel:member"\n  where:\n    members:\n      seq: 0\n      node_id: "group:three-stooges"\n  return:\n    - id\n    - relation\n    - members\n    - attributes\n  as: first_member_is_stooges`
  },
  {
    title: 'Find nodes by attribute value',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hypernode\n  where:\n    attributes.last_name: Howard\n  return:\n    - "*"`
  },
  {
    title: 'Find nodes by attribute regex',
    hql: `hql:\n  from: hello-world\n  match:\n    type: hypernode\n  where:\n    attributes.last_name:\n      $regex: "How.*"\n      $options: "i"\n  return:\n    - "*"`
  },
  {
    title: 'Mesh — all nodes from one graph on one server',
    hql: `hql:\n  from: bauhaus-strix.bauhaus.stooges-graph\n  match:\n    type: hypernode\n  return:\n    - id\n    - label\n    - type`
  },
  {
    title: 'Mesh — one graph across all servers',
    hql: `hql:\n  from: bauhaus-strix.*.stooges-graph\n  match:\n    type: hypernode\n  return:\n    - id\n    - label\n    - "_mesh_server_id"`
  },
  {
    title: 'Mesh — all graphs on all servers',
    hql: `hql:\n  from: bauhaus-strix.*.*\n  match:\n    type: hypernode\n  where:\n    attributes.last_name: Howard\n  return:\n    - id\n    - label\n    - attributes\n    - "_mesh_server_id"`
  },
  {
    title: 'Mesh — mix local and mesh graphs',
    hql: `hql:\n  from:\n    - hello-world\n    - bauhaus-strix.bauhaus.stooges-graph\n  match:\n    type: hypernode\n  return:\n    - id\n    - label\n    - "_mesh_server_id"`
  },
  {
    title: 'Space — query all nodes in a space graph',
    hql: `hql:\n  from: alpha/alpha-hg\n  match:\n    type: hypernode\n  return:\n    - id\n    - label\n    - type\n    - attributes`
  },
  {
    title: 'Space — query edges by relation in a space graph',
    hql: `hql:\n  from: alpha/alpha-hg\n  match:\n    type: hyperedge\n    relation: has-member\n  return:\n    - id\n    - relation\n    - members\n    - attributes`
  },
  {
    title: 'Space — multi-graph across two spaces',
    hql: `hql:\n  from:\n    - alpha/alpha-hg\n    - beta/beta-hg\n  match:\n    type: hypernode\n    node_type: Person\n  return:\n    - id\n    - label\n    - attributes`
  },
  {
    title: 'Space — mix space graph and global graph',
    hql: `hql:\n  from:\n    - hello-world\n    - alpha/alpha-hg\n  match:\n    type: hypernode\n  return:\n    - id\n    - label\n    - type`
  },
  {
    title: 'Space — mesh dot-notation (space-scoped remote graph)',
    hql: `hql:\n  from: bauhaus-strix.bauhaus.alpha.alpha-hg\n  match:\n    type: hypernode\n  return:\n    - id\n    - label\n    - "_mesh_server_id"`
  },
];

function initQueryEditor() {
  if (State.editorCM) return;
  const ta = document.getElementById('query-editor');
  State.editorCM = CodeMirror.fromTextArea(ta, {
    mode: 'yaml',
    theme: 'dracula',
    lineNumbers: true,
    lineWrapping: true,
    indentUnit: 2,
    tabSize: 2,
    extraKeys: {
      'Ctrl-Enter': () => runQuery(),
      'Cmd-Enter': () => runQuery(),
    },
  });
  // Set default query
  State.editorCM.setValue(HQL_EXAMPLES[0].hql);

  // Build examples list
  const exList = document.getElementById('hql-examples-list');
  HQL_EXAMPLES.forEach(ex => {
    const card = document.createElement('div');
    card.className = 'hql-example-card';
    card.innerHTML = `<div class="example-title">${ex.title}</div><pre>${ex.hql}</pre>`;
    card.addEventListener('click', () => {
      State.editorCM.setValue(ex.hql);
      bootstrap.Offcanvas.getInstance(document.getElementById('offcanvas-examples'))?.hide();
    });
    exList.appendChild(card);
  });
}

async function runQuery() {
  const hql = State.editorCM?.getValue() || '';
  const useCache = document.getElementById('query-use-cache').checked;
  const resultArea = document.getElementById('query-result-area');
  const countEl = document.getElementById('query-result-count');
  resultArea.innerHTML = '<span class="text-muted"><div class="spinner-border spinner-border-sm me-2"></div>Executing...</span>';
  try {
    const result = await HGAI_API.runQuery(hql, useCache);
    countEl.textContent = `${result.count || 0} results`;
    countEl.className = 'badge bg-success';
    resultArea.innerHTML = syntaxHighlightJson(result);
  } catch (err) {
    countEl.textContent = 'error';
    countEl.className = 'badge bg-danger';
    resultArea.innerHTML = `<span class="text-danger">${err.message}</span>`;
  }
}

document.getElementById('btn-query-run').addEventListener('click', runQuery);

document.getElementById('btn-query-validate').addEventListener('click', async () => {
  const hql = State.editorCM?.getValue() || '';
  try {
    const result = await HGAI_API.validateQuery(hql);
    if (result.valid) {
      toast('HQL is valid', 'success');
    } else {
      toast('Validation errors: ' + result.errors.join('; '), 'danger');
    }
  } catch (err) { toast(err.message, 'danger'); }
});

document.getElementById('btn-query-examples').addEventListener('click', () => {
  new bootstrap.Offcanvas(document.getElementById('offcanvas-examples')).show();
});

document.getElementById('btn-query-copy').addEventListener('click', () => {
  const content = document.getElementById('query-result-area').innerText;
  navigator.clipboard.writeText(content).then(() => toast('Copied to clipboard'));
});

// ── Query (SHQL) ───────────────────────────────────────────────────────────
const SHQL_EXAMPLES = [
  {
    title: 'Find all nodes of a type',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: ?person\n      node_type: Person\n  select:\n    - ?person`
  },
  {
    title: 'Find nodes with attribute filter',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: ?p\n      node_type: Person\n    - filter:\n        CONTAINS:\n          - ?p.label\n          - "Shemp"\n  select:\n    - ?p.id\n    - ?p.label`
  },
  {
    title: 'Find edges by relation type',
    shql: `shql:\n  from: hello-world\n  where:\n    - edge: ?e\n      relation: has-member\n  select:\n    - ?e.id\n    - ?e.relation\n    - ?e.members`
  },
  {
    title: 'Join nodes through a hyperedge',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: ?person\n      node_type: Person\n    - edge: ?membership\n      relation: has-member\n      members:\n        - node_id: ?person\n  select:\n    - ?person.label\n    - ?membership.id\n    - ?membership.relation`
  },
  {
    title: 'Optional pattern (left outer join)',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: ?p\n      node_type: Person\n    - optional:\n        - edge: ?e\n          relation: sibling\n          members:\n            - node_id: ?p\n  select:\n    - ?p.label\n    - ?e.id`
  },
  {
    title: 'Union of two patterns',
    shql: `shql:\n  from: hello-world\n  where:\n    - union:\n        - - node: ?item\n            node_type: Person\n        - - node: ?item\n            node_type: Character\n  select:\n    - ?item.id\n    - ?item.label\n    - ?item.type`
  },
  {
    title: 'Multi-graph with ORDER BY and LIMIT',
    shql: `shql:\n  from:\n    - graph-1\n    - graph-2\n  where:\n    - node: ?n\n      node_type: Person\n  select:\n    - ?n.id\n    - ?n.label\n  order_by: ?n.label\n  limit: 10`
  },
  {
    title: 'Numeric attribute filter',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: ?n\n    - filter:\n        ">=":\n          - ?n.attributes.score\n          - 90\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n.attributes.score`
  },
  {
    title: 'PIT — group members via rel:member hyperedges',
    shql: `shql:\n  from:\n    - hg-alpha\n  at: "2026-01-01T00:00:00"\n  where:\n    - edge: "?membership"\n      relation: "rel:member"\n      members:\n        - bind: "?group"\n          id: "group:three-stooges"\n        - bind: "?member"\n    - node: "?member"\n      bind: "?member_node"\n  select:\n    - "?member_node.id"\n    - "?member_node.label"\n    - "?member_node.type"\n    - "?member_node.attributes"`
  },
  {
    title: 'Positional member filter — bind the first member (seq)',
    shql: `shql:\n  from: hello-world\n  where:\n    - edge: ?e\n      relation: "rel:member"\n      members:\n        - bind: ?first_member_id\n          seq: 0\n  select:\n    - ?e.id\n    - ?e.relation\n    - ?first_member_id`
  },
  {
    title: 'Find nodes by attribute value',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: "?n"\n      attributes:\n        last_name: Howard\n  select:\n    - "?n"`
  },
  {
    title: 'Find nodes by attribute regex (DB-side)',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: "?n"\n      attributes:\n        last_name:\n          $regex: "How.*"\n          $options: "i"\n  select:\n    - "?n"`
  },
  {
    title: 'Find nodes by attribute regex (filter)',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: "?n"\n    - filter:\n        MATCHES:\n          - ?n.attributes.last_name\n          - "How.*"\n  select:\n    - "?n.id"\n    - "?n.label"\n    - "?n.attributes.last_name"`
  },
  {
    title: 'Mesh — all nodes from one graph on one server',
    shql: `shql:\n  from: bauhaus-strix.bauhaus.stooges-graph\n  where:\n    - node: ?n\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n.type`
  },
  {
    title: 'Mesh — one graph across all servers',
    shql: `shql:\n  from: bauhaus-strix.*.stooges-graph\n  where:\n    - node: ?n\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n._mesh_server_id`
  },
  {
    title: 'Mesh — all graphs on all servers',
    shql: `shql:\n  from: bauhaus-strix.*.*\n  where:\n    - node: ?n\n      node_type: Person\n    - filter:\n        "==":\n          - ?n.attributes.last_name\n          - Howard\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n._mesh_server_id`
  },
  {
    title: 'Mesh — mix local and mesh graphs',
    shql: `shql:\n  from:\n    - hello-world\n    - bauhaus-strix.bauhaus.stooges-graph\n  where:\n    - node: ?n\n      node_type: Person\n  select:\n    - ?n.id\n    - ?n.label`
  },
  {
    title: 'Space — find all nodes in a space graph',
    shql: `shql:\n  from: alpha/alpha-hg\n  where:\n    - node: ?n\n      node_type: Person\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n.attributes`
  },
  {
    title: 'Space — join nodes through edge in a space graph',
    shql: `shql:\n  from: alpha/alpha-hg\n  where:\n    - node: ?person\n      node_type: Person\n    - edge: ?membership\n      relation: has-member\n      members:\n        - node_id: ?person\n  select:\n    - ?person.label\n    - ?membership.id\n    - ?membership.relation`
  },
  {
    title: 'Space — multi-graph across two spaces',
    shql: `shql:\n  from:\n    - alpha/alpha-hg\n    - beta/beta-hg\n  where:\n    - node: ?n\n      node_type: Person\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n.attributes`
  },
  {
    title: 'Space — mix space graph and global graph',
    shql: `shql:\n  from:\n    - hello-world\n    - alpha/alpha-hg\n  where:\n    - node: ?n\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n.type`
  },
  {
    title: 'Space — mesh dot-notation (space-scoped remote graph)',
    shql: `shql:\n  from: bauhaus-strix.bauhaus.alpha.alpha-hg\n  where:\n    - node: ?n\n      node_type: Person\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n._mesh_server_id`
  },
];

let _shqlEditorCM = null;

function initShqlEditor() {
  if (_shqlEditorCM) return;
  const ta = document.getElementById('shql-editor');
  _shqlEditorCM = CodeMirror.fromTextArea(ta, {
    mode: 'yaml',
    theme: 'dracula',
    lineNumbers: true,
    lineWrapping: true,
    indentUnit: 2,
    tabSize: 2,
    extraKeys: {
      'Ctrl-Enter': () => runShqlQuery(),
      'Cmd-Enter': () => runShqlQuery(),
    },
  });
  _shqlEditorCM.setValue(SHQL_EXAMPLES[0].shql);

  const exList = document.getElementById('shql-examples-list');
  SHQL_EXAMPLES.forEach(ex => {
    const card = document.createElement('div');
    card.className = 'hql-example-card';
    card.innerHTML = `<div class="example-title">${ex.title}</div><pre>${ex.shql}</pre>`;
    card.addEventListener('click', () => {
      _shqlEditorCM.setValue(ex.shql);
      bootstrap.Offcanvas.getInstance(document.getElementById('offcanvas-shql-examples'))?.hide();
    });
    exList.appendChild(card);
  });
}

async function runShqlQuery() {
  const shql = _shqlEditorCM?.getValue() || '';
  const useCache = document.getElementById('shql-use-cache').checked;
  const resultArea = document.getElementById('shql-result-area');
  const countEl = document.getElementById('shql-result-count');
  resultArea.innerHTML = '<span class="text-muted"><div class="spinner-border spinner-border-sm me-2"></div>Executing...</span>';
  try {
    const result = await HGAI_API.runShqlQuery(shql, useCache);
    countEl.textContent = `${result.count || 0} results`;
    countEl.className = 'badge bg-success';
    resultArea.innerHTML = syntaxHighlightJson(result);
  } catch (err) {
    countEl.textContent = 'error';
    countEl.className = 'badge bg-danger';
    resultArea.innerHTML = `<span class="text-danger">${err.message}</span>`;
  }
}

document.getElementById('btn-shql-run').addEventListener('click', runShqlQuery);

document.getElementById('btn-shql-validate').addEventListener('click', async () => {
  const shql = _shqlEditorCM?.getValue() || '';
  try {
    const result = await HGAI_API.validateShqlQuery(shql);
    if (result.valid) {
      toast('SHQL is valid', 'success');
    } else {
      toast('Validation errors: ' + result.errors.join('; '), 'danger');
    }
  } catch (err) { toast(err.message, 'danger'); }
});

document.getElementById('btn-shql-examples').addEventListener('click', () => {
  new bootstrap.Offcanvas(document.getElementById('offcanvas-shql-examples')).show();
});

document.getElementById('btn-shql-copy').addEventListener('click', () => {
  const content = document.getElementById('shql-result-area').innerText;
  navigator.clipboard.writeText(content).then(() => toast('Copied to clipboard'));
});

// ── Accounts ───────────────────────────────────────────────────────────────
async function loadAccounts() {
  const tbody = document.getElementById('tbody-accounts');
  tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  try {
    const resp = await HGAI_API.listAccounts({ limit: 200 });
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No accounts found</td></tr>';
      return;
    }
    resp.items.forEach(a => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${a.username}</strong></td>
        <td>${a.email||'—'}</td>
        <td>${roleBadges(a.roles)}</td>
        <td>${statusBadge(a.status)}</td>
        <td class="small text-muted">${fmtDate(a.last_login)}</td>
        <td>${tagBadges(a.tags)}</td>
        <td class="text-end">
          <button class="btn btn-xs btn-outline-primary me-1" onclick="editAccount('${a.username}')"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-xs btn-outline-danger" onclick="deleteAccount('${a.username}')"><i class="bi bi-trash"></i></button>
        </td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-create-account').addEventListener('click', () => openAccountModal());

async function openAccountModal(username = null) {
  const modal = new bootstrap.Modal(document.getElementById('modal-account'));
  const isEdit = !!username;
  document.getElementById('account-form-mode').value = isEdit ? 'edit' : 'create';
  document.getElementById('modal-account-title').textContent = isEdit ? `Edit: ${username}` : 'New Account';
  document.getElementById('pw-required').style.display = isEdit ? 'none' : '';
  // Show Space Memberships tab only in edit mode
  document.getElementById('account-spaces-tab-item').style.display = isEdit ? '' : 'none';
  // Always start on Details tab
  const detailsTabEl = document.querySelector('#account-modal-tabs .nav-link:first-child');
  bootstrap.Tab.getOrCreateInstance(detailsTabEl).show();
  document.getElementById('account-assign-space-form').classList.add('d-none');

  if (isEdit) {
    try {
      const a = await HGAI_API.getAccount(username);
      document.getElementById('account-username').value = a.username;
      document.getElementById('account-username').readOnly = true;
      document.getElementById('account-email').value = a.email || '';
      document.getElementById('account-status').value = a.status || 'active';
      document.getElementById('account-tags').value = (a.tags || []).join(', ');
      document.getElementById('account-description').value = a.description || '';
      document.getElementById('account-password').value = '';
      ['admin','user','agent','readonly'].forEach(r => {
        document.getElementById(`role-${r}`).checked = (a.roles || []).includes(r);
      });
    } catch {}
    loadAccountSpaces(username);
  } else {
    document.getElementById('form-account').reset();
    document.getElementById('account-username').readOnly = false;
    document.getElementById('role-user').checked = true;
  }
  modal.show();
}

async function loadAccountSpaces(username) {
  const tbody = document.getElementById('tbody-account-spaces');
  tbody.innerHTML = '<tr><td colspan="4" class="text-center py-3"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  try {
    const resp = await HGAI_API.listAccountSpaces(username, { limit: 200 });
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No space memberships</td></tr>';
      return;
    }
    resp.items.forEach(s => {
      const member = (s.members || []).find(m => m.username === username);
      const role = member?.role || '—';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${s.id}</code></td>
        <td>${s.label || '—'}</td>
        <td>
          <select class="form-select form-select-sm" style="width:110px"
            onchange="updateAccountSpaceRole('${username}', '${s.id}', this.value)">
            <option ${role==='viewer'?'selected':''} value="viewer">viewer</option>
            <option ${role==='member'?'selected':''} value="member">member</option>
            <option ${role==='admin'?'selected':''} value="admin">admin</option>
            <option ${role==='owner'?'selected':''} value="owner">owner</option>
          </select>
        </td>
        <td class="text-end">
          <button class="btn btn-xs btn-outline-danger" onclick="removeAccountSpace('${username}', '${s.id}')">
            <i class="bi bi-x-circle"></i>
          </button>
        </td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-danger text-center py-2">${err.message}</td></tr>`;
  }
}

window.updateAccountSpaceRole = async (username, spaceId, role) => {
  try {
    await HGAI_API.assignAccountToSpace(username, spaceId, { role });
    toast(`Role updated to "${role}"`);
  } catch (err) {
    toast(err.message, 'danger');
    loadAccountSpaces(username);
  }
};

window.removeAccountSpace = (username, spaceId) => {
  confirmDelete(`Remove "${username}" from space "${spaceId}"?`, async () => {
    try {
      await HGAI_API.removeAccountFromSpace(username, spaceId);
      toast(`Removed from space "${spaceId}"`);
      loadAccountSpaces(username);
    } catch (err) { toast(err.message, 'danger'); }
  });
};

document.getElementById('btn-account-assign-space').addEventListener('click', async () => {
  const form = document.getElementById('account-assign-space-form');
  form.classList.remove('d-none');
  // Populate space select
  const sel = document.getElementById('account-space-select');
  sel.innerHTML = '<option value="">— Select Space —</option>';
  try {
    const resp = await HGAI_API.listSpaces({ limit: 200 });
    (resp.items || []).forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id; opt.textContent = `${s.label} (${s.id})`;
      sel.appendChild(opt);
    });
  } catch {}
});

document.getElementById('btn-account-space-cancel').addEventListener('click', () => {
  document.getElementById('account-assign-space-form').classList.add('d-none');
});

document.getElementById('btn-account-space-confirm').addEventListener('click', async () => {
  const username = document.getElementById('account-username').value;
  const spaceId = document.getElementById('account-space-select').value;
  const role = document.getElementById('account-space-role').value;
  if (!spaceId) { toast('Select a space first', 'warning'); return; }
  try {
    await HGAI_API.assignAccountToSpace(username, spaceId, { role });
    toast(`Assigned "${username}" to space "${spaceId}" as ${role}`);
    document.getElementById('account-assign-space-form').classList.add('d-none');
    loadAccountSpaces(username);
  } catch (err) { toast(err.message, 'danger'); }
});

window.editAccount = (username) => openAccountModal(username);
window.deleteAccount = (username) => {
  confirmDelete(`Delete account "${username}"?`, async () => {
    try {
      await HGAI_API.deleteAccount(username);
      toast(`Account "${username}" deleted`);
      loadAccounts();
    } catch (err) { toast(err.message, 'danger'); }
  });
};

document.getElementById('btn-save-account').addEventListener('click', async () => {
  const mode = document.getElementById('account-form-mode').value;
  const username = document.getElementById('account-username').value.trim();
  const roles = ['admin','user','agent','readonly'].filter(r => document.getElementById(`role-${r}`).checked);
  const pw = document.getElementById('account-password').value;

  const data = {
    username,
    email: document.getElementById('account-email').value.trim() || null,
    roles,
    status: document.getElementById('account-status').value,
    tags: parseTags(document.getElementById('account-tags').value),
    description: document.getElementById('account-description').value.trim() || null,
    attributes: {},
    permissions: { graphs: ['*'], operations: roles.includes('admin') ? ['read','write','delete','admin','query','export','import'] : ['read','query'] },
  };
  if (pw) data.password = pw;
  if (mode === 'create' && !pw) { toast('Password is required for new accounts', 'warning'); return; }

  try {
    if (mode === 'create') {
      await HGAI_API.createAccount(data);
      toast('Account created');
    } else {
      await HGAI_API.updateAccount(username, data);
      toast('Account updated');
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-account'))?.hide();
    loadAccounts();
  } catch (err) { toast(err.message, 'danger'); }
});

// ── Meshes ─────────────────────────────────────────────────────────────────
let _activeMeshId = null;

async function loadMeshes() {
  const tbody = document.getElementById('tbody-meshes');
  tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  // Hide detail panel when refreshing the list
  document.getElementById('mesh-detail-panel').classList.add('d-none');
  _activeMeshId = null;
  try {
    const resp = await HGAI_API.listMeshes({ limit: 200 });
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No meshes configured</td></tr>';
      return;
    }
    resp.items.forEach(m => {
      const tr = document.createElement('tr');
      tr.className = 'cursor-pointer';
      tr.innerHTML = `
        <td><code>${m.id}</code></td>
        <td>${m.label||'—'}</td>
        <td class="text-muted small">${truncate(m.description||'', 40)}</td>
        <td><span class="badge bg-secondary">${(m.servers||[]).length}</span></td>
        <td>${statusBadge(m.status)}</td>
        <td class="text-end">
          <button class="btn btn-xs btn-outline-info me-1" title="Ping" onclick="event.stopPropagation();openMeshPing('${m.id}')"><i class="bi bi-wifi"></i></button>
          <button class="btn btn-xs btn-outline-success me-1" title="Sync" onclick="event.stopPropagation();runMeshSync('${m.id}')"><i class="bi bi-arrow-repeat"></i></button>
          <button class="btn btn-xs btn-outline-primary me-1" title="Federated Query" onclick="event.stopPropagation();openMeshQuery('${m.id}')"><i class="bi bi-terminal"></i></button>
          <button class="btn btn-xs btn-outline-secondary me-1" title="Edit" onclick="event.stopPropagation();editMesh('${m.id}')"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-xs btn-outline-danger" title="Delete" onclick="event.stopPropagation();deleteMesh('${m.id}')"><i class="bi bi-trash"></i></button>
        </td>`;
      tr.addEventListener('click', () => openMeshDetail(m.id));
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

async function openMeshDetail(id) {
  _activeMeshId = id;
  const panel = document.getElementById('mesh-detail-panel');
  const tbody = document.getElementById('tbody-mesh-servers');
  document.getElementById('mesh-detail-id').textContent = id;
  panel.classList.remove('d-none');
  tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  try {
    const m = await HGAI_API.getMesh(id);
    tbody.innerHTML = '';
    (m.servers || []).forEach(srv => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${srv.server_id||'—'}</code></td>
        <td>${srv.server_name||'—'}</td>
        <td><a href="${srv.url}" target="_blank" class="small text-muted">${srv.url||'—'}</a></td>
        <td>${statusBadge(srv.status)}</td>
        <td><span class="badge bg-light text-dark" id="ping-${srv.server_id}">—</span></td>`;
      tbody.appendChild(tr);
    });
    if (!m.servers || !m.servers.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No servers configured</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-mesh-detail-close').addEventListener('click', () => {
  document.getElementById('mesh-detail-panel').classList.add('d-none');
  _activeMeshId = null;
});

document.getElementById('btn-mesh-ping-panel').addEventListener('click', () => {
  if (_activeMeshId) openMeshPing(_activeMeshId);
});

document.getElementById('btn-mesh-sync-panel').addEventListener('click', () => {
  if (_activeMeshId) runMeshSync(_activeMeshId);
});

document.getElementById('btn-mesh-query-panel').addEventListener('click', () => {
  if (_activeMeshId) openMeshQuery(_activeMeshId);
});

window.openMeshPing = async (id) => {
  document.getElementById('modal-ping-mesh-id').textContent = id;
  const tbody = document.getElementById('tbody-ping-results');
  tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3"><div class="spinner-border spinner-border-sm"></div> Pinging...</td></tr>';
  new bootstrap.Modal(document.getElementById('modal-mesh-ping')).show();
  try {
    const result = await HGAI_API.pingMesh(id);
    tbody.innerHTML = '';
    (result.results || []).forEach(r => {
      const ok = r.status === 'ok';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${r.server_id||'—'}</code></td>
        <td><a href="${r.url||'#'}" target="_blank" class="small text-muted">${r.url||'—'}</a></td>
        <td><span class="badge ${ok ? 'badge-status-active' : 'bg-danger'}">${r.status||'?'}</span></td>
        <td>${r.latency_ms != null ? r.latency_ms.toFixed(0) + ' ms' : '—'}</td>
        <td class="text-danger small">${r.error||''}</td>`;
      tbody.appendChild(tr);
      // Update inline ping badge in server detail panel
      const badge = document.getElementById(`ping-${r.server_id}`);
      if (badge) {
        badge.textContent = ok ? `${(r.latency_ms||0).toFixed(0)}ms` : r.status;
        badge.className = `badge ${ok ? 'badge-status-active' : 'bg-danger'}`;
      }
    });
    if (!result.results || !result.results.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No servers in mesh</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">${err.message}</td></tr>`;
  }
};

window.runMeshSync = async (id) => {
  try {
    toast(`Syncing mesh "${id}"…`, 'info');
    const result = await HGAI_API.syncMesh(id);
    const updated = result.updated_servers || result.servers_updated || 0;
    toast(`Mesh "${id}" synced — ${updated} server(s) updated`);
    if (_activeMeshId === id) openMeshDetail(id);
  } catch (err) { toast(err.message, 'danger'); }
};

window.openMeshQuery = (id) => {
  document.getElementById('mesh-query-id').textContent = id;
  document.getElementById('mesh-query-result-count').textContent = '—';
  document.getElementById('mesh-query-result-count').className = 'badge bg-secondary';
  document.getElementById('mesh-query-result-area').textContent = '(results appear here)';
  new bootstrap.Offcanvas(document.getElementById('offcanvas-mesh-query')).show();
};

document.getElementById('btn-mesh-query-run').addEventListener('click', async () => {
  const id = document.getElementById('mesh-query-id').textContent;
  const lang = document.getElementById('mesh-query-lang').value;
  const useCache = document.getElementById('mesh-query-use-cache').checked;
  const queryText = document.getElementById('mesh-query-editor').value.trim();
  const resultArea = document.getElementById('mesh-query-result-area');
  const countEl = document.getElementById('mesh-query-result-count');

  if (!queryText) { toast('Enter a query first', 'warning'); return; }

  resultArea.textContent = 'Executing…';
  countEl.textContent = '…';
  countEl.className = 'badge bg-secondary';

  // Auto-wrap with language key if missing
  let body;
  const stripped = queryText.trimStart();
  if (stripped.startsWith(`${lang}:`)) {
    body = { [lang]: queryText, use_cache: useCache };
  } else {
    // Wrap it
    const wrapped = `${lang}:\n` + queryText.split('\n').map(l => '  ' + l).join('\n');
    body = { [lang]: wrapped, use_cache: useCache };
  }

  try {
    const result = await HGAI_API.queryMesh(id, body);
    countEl.textContent = `${result.count || 0} results`;
    countEl.className = 'badge bg-success';
    resultArea.innerHTML = syntaxHighlightJson(result);
  } catch (err) {
    countEl.textContent = 'error';
    countEl.className = 'badge bg-danger';
    resultArea.textContent = err.message;
  }
});

document.getElementById('btn-mesh-query-copy').addEventListener('click', () => {
  const content = document.getElementById('mesh-query-result-area').innerText;
  navigator.clipboard.writeText(content).then(() => toast('Copied to clipboard'));
});

// Mesh create/edit modal
document.getElementById('btn-create-mesh').addEventListener('click', () => openMeshModal());

window.editMesh = (id) => openMeshModal(id);

function _renderMeshServerRow(srv = {}) {
  const div = document.createElement('div');
  div.className = 'member-row align-items-start';
  div.innerHTML = `
    <input type="text" class="form-control form-control-sm srv-id" placeholder="id" style="width:110px;flex-shrink:0" value="${srv.server_id||''}"/>
    <input type="text" class="form-control form-control-sm srv-name" placeholder="name" style="width:120px;flex-shrink:0" value="${srv.server_name||''}"/>
    <input type="text" class="form-control form-control-sm srv-url" placeholder="http://host:8357" style="width:180px;flex-shrink:0" value="${srv.url||''}"/>
    <input type="text" class="form-control form-control-sm srv-token font-monospace" placeholder="api_token (optional)" style="flex:1;min-width:0" value="${srv.api_token||''}"/>
    <select class="form-select form-select-sm srv-status" style="width:95px;flex-shrink:0">
      <option ${srv.status==='active'?'selected':''}>active</option>
      <option ${srv.status==='inactive'?'selected':''}>inactive</option>
    </select>
    <button type="button" class="btn btn-xs btn-outline-danger flex-shrink-0" onclick="this.closest('.member-row').remove()">
      <i class="bi bi-x-lg"></i>
    </button>`;
  return div;
}

async function openMeshModal(meshId = null) {
  const modal = new bootstrap.Modal(document.getElementById('modal-mesh'));
  document.getElementById('mesh-form-mode').value = meshId ? 'edit' : 'create';
  document.getElementById('modal-mesh-title').textContent = meshId ? `Edit Mesh: ${meshId}` : 'New Mesh';

  const serversList = document.getElementById('mesh-servers-list');
  serversList.innerHTML = '';

  if (meshId) {
    try {
      const m = await HGAI_API.getMesh(meshId);
      document.getElementById('mesh-id').value = m.id;
      document.getElementById('mesh-id').readOnly = true;
      document.getElementById('mesh-label').value = m.label || '';
      document.getElementById('mesh-description').value = m.description || '';
      document.getElementById('mesh-status').value = m.status || 'active';
      (m.servers || []).forEach(srv => serversList.appendChild(_renderMeshServerRow(srv)));
    } catch {}
  } else {
    document.getElementById('mesh-id').value = '';
    document.getElementById('mesh-id').readOnly = false;
    document.getElementById('mesh-label').value = '';
    document.getElementById('mesh-description').value = '';
    document.getElementById('mesh-status').value = 'active';
    serversList.appendChild(_renderMeshServerRow());
  }
  modal.show();
}

document.getElementById('btn-add-mesh-server').addEventListener('click', () => {
  document.getElementById('mesh-servers-list').appendChild(_renderMeshServerRow());
});

document.getElementById('btn-save-mesh').addEventListener('click', async () => {
  const mode = document.getElementById('mesh-form-mode').value;
  const id = document.getElementById('mesh-id').value.trim();
  if (!id) { toast('Mesh ID is required', 'warning'); return; }

  const servers = Array.from(document.querySelectorAll('#mesh-servers-list .member-row')).map(row => ({
    server_id: row.querySelector('.srv-id').value.trim(),
    server_name: row.querySelector('.srv-name').value.trim(),
    url: row.querySelector('.srv-url').value.trim(),
    api_token: row.querySelector('.srv-token').value.trim() || null,
    status: row.querySelector('.srv-status').value,
  })).filter(s => s.server_id || s.url);

  const data = {
    id,
    label: document.getElementById('mesh-label').value.trim() || id,
    description: document.getElementById('mesh-description').value.trim() || null,
    status: document.getElementById('mesh-status').value,
    servers,
  };

  try {
    if (mode === 'create') {
      await HGAI_API.createMesh(data);
      toast(`Mesh "${id}" created`);
    } else {
      await HGAI_API.updateMesh(id, data);
      toast(`Mesh "${id}" updated`);
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-mesh'))?.hide();
    loadMeshes();
  } catch (err) { toast(err.message, 'danger'); }
});

window.deleteMesh = (id) => {
  confirmDelete(`Delete mesh "${id}"?`, async () => {
    try { await HGAI_API.deleteMesh(id); toast(`Mesh "${id}" deleted`); loadMeshes(); }
    catch (err) { toast(err.message, 'danger'); }
  });
};

// ── Spaces ─────────────────────────────────────────────────────────────────
async function loadSpaces() {
  const tbody = document.getElementById('tbody-spaces');
  tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  document.getElementById('space-detail-panel').classList.add('d-none');
  State.activeSpaceDetailId = null;
  try {
    const resp = await HGAI_API.listSpaces({ limit: 200 });
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No spaces found</td></tr>';
      return;
    }
    resp.items.forEach(s => {
      const tr = document.createElement('tr');
      tr.className = 'cursor-pointer';
      tr.innerHTML = `
        <td><code>${s.id}</code></td>
        <td>${s.label||'—'}</td>
        <td class="text-muted small">${truncate(s.description||'', 50)}</td>
        <td><span class="badge bg-secondary">${(s.members||[]).length}</span></td>
        <td>${statusBadge(s.status)}</td>
        <td>${tagBadges(s.tags)}</td>
        <td class="text-end">
          <button class="btn btn-xs btn-outline-primary me-1" title="Edit" onclick="event.stopPropagation();editSpace('${s.id}')"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-xs btn-outline-danger" title="Delete" onclick="event.stopPropagation();deleteSpace('${s.id}')"><i class="bi bi-trash"></i></button>
        </td>`;
      tr.addEventListener('click', () => openSpaceDetail(s.id));
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

async function openSpaceDetail(spaceId) {
  State.activeSpaceDetailId = spaceId;
  document.getElementById('space-detail-id').textContent = spaceId;
  document.getElementById('space-member-space-id').value = spaceId;
  const panel = document.getElementById('space-detail-panel');
  panel.classList.remove('d-none');
  await _loadSpaceMembers(spaceId);
}

async function _loadSpaceMembers(spaceId) {
  const tbody = document.getElementById('tbody-space-members');
  tbody.innerHTML = '<tr><td colspan="3" class="text-center py-3"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  try {
    const members = await HGAI_API.listSpaceMembers(spaceId);
    tbody.innerHTML = '';
    if (!members || !members.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-3">No members</td></tr>';
      return;
    }
    members.forEach(m => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${m.username}</strong></td>
        <td>
          <select class="form-select form-select-sm" style="width:110px"
            onchange="updateSpaceMemberRole('${spaceId}', '${m.username}', this.value)">
            <option ${m.role==='viewer'?'selected':''} value="viewer">viewer</option>
            <option ${m.role==='member'?'selected':''} value="member">member</option>
            <option ${m.role==='admin'?'selected':''} value="admin">admin</option>
            <option ${m.role==='owner'?'selected':''} value="owner">owner</option>
          </select>
        </td>
        <td class="text-end">
          <button class="btn btn-xs btn-outline-danger" onclick="removeSpaceMember('${spaceId}', '${m.username}')">
            <i class="bi bi-person-x"></i>
          </button>
        </td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="3" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-space-detail-close').addEventListener('click', () => {
  document.getElementById('space-detail-panel').classList.add('d-none');
  State.activeSpaceDetailId = null;
});

document.getElementById('btn-create-space').addEventListener('click', () => openSpaceModal());

window.editSpace = (id) => openSpaceModal(id);

async function openSpaceModal(spaceId = null) {
  const modal = new bootstrap.Modal(document.getElementById('modal-space'));
  document.getElementById('space-form-mode').value = spaceId ? 'edit' : 'create';
  document.getElementById('modal-space-title').textContent = spaceId ? `Edit Space: ${spaceId}` : 'New Space';

  if (spaceId) {
    try {
      const s = await HGAI_API.getSpace(spaceId);
      document.getElementById('space-id').value = s.id;
      document.getElementById('space-id').readOnly = true;
      document.getElementById('space-label').value = s.label || '';
      document.getElementById('space-status').value = s.status || 'active';
      document.getElementById('space-tags').value = (s.tags || []).join(', ');
      document.getElementById('space-description').value = s.description || '';
    } catch {}
  } else {
    document.getElementById('space-id').value = '';
    document.getElementById('space-id').readOnly = false;
    document.getElementById('space-label').value = '';
    document.getElementById('space-status').value = 'active';
    document.getElementById('space-tags').value = '';
    document.getElementById('space-description').value = '';
  }
  modal.show();
}

document.getElementById('btn-save-space').addEventListener('click', async () => {
  const mode = document.getElementById('space-form-mode').value;
  const id = document.getElementById('space-id').value.trim();
  if (!id) { toast('Space ID is required', 'warning'); return; }
  const data = {
    id,
    label: document.getElementById('space-label').value.trim() || id,
    status: document.getElementById('space-status').value,
    tags: parseTags(document.getElementById('space-tags').value),
    description: document.getElementById('space-description').value.trim() || null,
  };
  try {
    if (mode === 'create') {
      await HGAI_API.createSpace(data);
      toast(`Space "${id}" created`);
    } else {
      await HGAI_API.updateSpace(id, data);
      toast(`Space "${id}" updated`);
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-space'))?.hide();
    loadSpaces();
  } catch (err) { toast(err.message, 'danger'); }
});

window.deleteSpace = (id) => {
  confirmDelete(`Delete space "${id}"? Graphs within the space will be unaffected.`, async () => {
    try {
      await HGAI_API.deleteSpace(id);
      toast(`Space "${id}" deleted`);
      loadSpaces();
    } catch (err) { toast(err.message, 'danger'); }
  });
};

document.getElementById('btn-add-space-member').addEventListener('click', () => {
  const spaceId = State.activeSpaceDetailId;
  if (!spaceId) return;
  document.getElementById('space-member-mode').value = 'add';
  document.getElementById('modal-space-member-title').textContent = `Add Member to ${spaceId}`;
  document.getElementById('space-member-space-id').value = spaceId;
  document.getElementById('space-member-username').value = '';
  document.getElementById('space-member-username').readOnly = false;
  document.getElementById('space-member-role').value = 'member';
  new bootstrap.Modal(document.getElementById('modal-space-member')).show();
});

document.getElementById('btn-save-space-member').addEventListener('click', async () => {
  const spaceId = document.getElementById('space-member-space-id').value;
  const username = document.getElementById('space-member-username').value.trim();
  const role = document.getElementById('space-member-role').value;
  if (!username) { toast('Username is required', 'warning'); return; }
  try {
    await HGAI_API.addSpaceMember(spaceId, username, { role });
    toast(`Added "${username}" to space "${spaceId}"`);
    bootstrap.Modal.getInstance(document.getElementById('modal-space-member'))?.hide();
    if (State.activeSpaceDetailId === spaceId) await _loadSpaceMembers(spaceId);
  } catch (err) { toast(err.message, 'danger'); }
});

window.updateSpaceMemberRole = async (spaceId, username, role) => {
  try {
    await HGAI_API.updateSpaceMemberRole(spaceId, username, { role });
    toast(`Updated role for "${username}"`);
  } catch (err) {
    toast(err.message, 'danger');
    if (State.activeSpaceDetailId === spaceId) await _loadSpaceMembers(spaceId);
  }
};

window.removeSpaceMember = (spaceId, username) => {
  confirmDelete(`Remove "${username}" from space "${spaceId}"?`, async () => {
    try {
      await HGAI_API.removeSpaceMember(spaceId, username);
      toast(`Removed "${username}" from space`);
      await _loadSpaceMembers(spaceId);
    } catch (err) { toast(err.message, 'danger'); }
  });
};

// ── System ─────────────────────────────────────────────────────────────────
async function loadSystem() {
  try {
    const info = await HGAI_API.getServerInfo();
    const table = document.getElementById('sys-server-info');
    table.innerHTML = Object.entries({
      'Server ID': info.server_id,
      'Server Name': info.server_name,
      'Version': info.version,
      'Capabilities': (info.capabilities || []).join(', '),
    }).map(([k,v]) => `<tr><th class="fw-normal text-muted" style="width:40%">${k}</th><td>${v||'—'}</td></tr>`).join('');
  } catch {}
}

document.getElementById('btn-flush-cache').addEventListener('click', async () => {
  try {
    const result = await HGAI_API.flushCache();
    toast(`Cache flushed (${result.invalidated} entries removed)`);
  } catch (err) { toast(err.message, 'danger'); }
});

// ── Bootstrap ──────────────────────────────────────────────────────────────
initApp();
