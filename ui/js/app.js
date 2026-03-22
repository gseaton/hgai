/**
 * HypergraphAI Web UI - Main Application
 */

// ── State ──────────────────────────────────────────────────────────────────
const State = {
  currentScreen: 'dashboard',
  activeGraphId: null,
  nodesPage: 0,
  edgesPage: 0,
  nodePageSize: 50,
  edgePageSize: 50,
  confirmCallback: null,
  editorCM: null,
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
    edges: 'Hyperedges', query: 'HQL Query', shql: 'SHQL Query', accounts: 'Accounts',
    meshes: 'Meshes', system: 'System',
  };
  document.getElementById('topbar-screen-title').textContent = titles[name] || name;
  State.currentScreen = name;

  // Load screen data
  const loaders = {
    dashboard: loadDashboard,
    graphs: loadGraphs,
    nodes: () => { State.nodesPage = 0; populateNodesGraphSelect(); loadNodes(); },
    edges: () => { State.edgesPage = 0; populateEdgesGraphSelect(); loadEdges(); },
    query: initQueryEditor,
    shql: initShqlEditor,
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

async function populateGraphSelector() {
  const sel = document.getElementById('active-graph-select');
  try {
    const resp = await HGAI_API.listGraphs({ status: 'active', limit: 200 });
    sel.innerHTML = '<option value="">— Select Graph —</option>';
    (resp.items || []).forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id; opt.textContent = `${g.label} (${g.id})`;
      if (g.id === State.activeGraphId) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch {}
}

async function populateNodesGraphSelect(selectedId) {
  const sel = document.getElementById('nodes-graph-select');
  const pick = selectedId !== undefined ? selectedId : (sel.value || State.activeGraphId);
  try {
    const resp = await HGAI_API.listGraphs({ status: 'active', limit: 200 });
    sel.innerHTML = '<option value="">— Select Hypergraph —</option>';
    (resp.items || []).forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id; opt.textContent = `${g.label} (${g.id})`;
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
    const resp = await HGAI_API.listGraphs({ status: 'active', limit: 200 });
    sel.innerHTML = '<option value="">— Select Hypergraph —</option>';
    (resp.items || []).forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id; opt.textContent = `${g.label} (${g.id})`;
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
  tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  try {
    const resp = await HGAI_API.listGraphs({ status: '', limit: 200 });
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No hypergraphs found</td></tr>';
      return;
    }
    resp.items.forEach(g => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${g.id}</code></td>
        <td>${g.label}</td>
        <td><span class="badge bg-light text-dark">${g.type}</span></td>
        <td>${g.node_count||0}</td>
        <td>${g.edge_count||0}</td>
        <td>${statusBadge(g.status)}</td>
        <td>${tagBadges(g.tags)}</td>
        <td class="text-end">
          <button class="btn btn-xs btn-outline-secondary me-1" onclick="viewGraph('${g.id}')"><i class="bi bi-eye"></i></button>
          <button class="btn btn-xs btn-outline-primary me-1" onclick="editGraph('${g.id}')"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-xs btn-outline-danger" onclick="deleteGraph('${g.id}')"><i class="bi bi-trash"></i></button>
        </td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-create-graph').addEventListener('click', () => openGraphModal());

async function openGraphModal(graphId = null) {
  const modal = new bootstrap.Modal(document.getElementById('modal-graph'));
  document.getElementById('graph-form-mode').value = graphId ? 'edit' : 'create';
  document.getElementById('modal-graph-title').textContent = graphId ? 'Edit Hypergraph' : 'New Hypergraph';

  if (graphId) {
    try {
      const g = await HGAI_API.getGraph(graphId);
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
  }
  modal.show();
}

window.editGraph = (id) => openGraphModal(id);
window.viewGraph = async (id) => {
  const g = await HGAI_API.getGraph(id).catch(()=>null);
  const stats = await HGAI_API.getGraphStats(id).catch(()=>null);
  showDetail(`Hypergraph: ${id}`, { ...g, stats });
};
window.deleteGraph = (id) => {
  confirmDelete(`Delete hypergraph "${id}" and ALL its nodes and edges?`, async () => {
    try {
      await HGAI_API.deleteGraph(id);
      toast(`Hypergraph "${id}" deleted`);
      loadGraphs();
      populateGraphSelector();
    } catch (err) { toast(err.message, 'danger'); }
  });
};

document.getElementById('btn-save-graph').addEventListener('click', async () => {
  const mode = document.getElementById('graph-form-mode').value;
  const id = document.getElementById('graph-id').value.trim();
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
      await HGAI_API.createGraph(data);
      toast('Hypergraph created');
    } else {
      await HGAI_API.updateGraph(id, data);
      toast('Hypergraph updated');
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-graph'))?.hide();
    loadGraphs();
    populateGraphSelector();
  } catch (err) { toast(err.message, 'danger'); }
});

// ── Hypernodes ─────────────────────────────────────────────────────────────
async function loadNodes() {
  // Sync State from the in-screen selector (it may have been set before State synced)
  const screenSel = document.getElementById('nodes-graph-select');
  if (screenSel.value) State.activeGraphId = screenSel.value;
  if (!State.activeGraphId) {
    document.getElementById('tbody-nodes').innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Select a hypergraph above</td></tr>';
    return;
  }
  const tbody = document.getElementById('tbody-nodes');
  tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';

  const params = {
    skip: State.nodesPage * State.nodePageSize,
    limit: State.nodePageSize,
    status: document.getElementById('node-status-filter').value || undefined,
    node_type: document.getElementById('node-type-filter').value.trim() || undefined,
    search: document.getElementById('node-search').value.trim() || undefined,
  };

  try {
    const resp = await HGAI_API.listNodes(State.activeGraphId, params);
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No hypernodes found</td></tr>';
    } else {
      resp.items.forEach(n => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><code class="text-truncate-150" title="${n.id}">${n.id}</code></td>
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
    }
    renderPagination('nodes', resp.total, State.nodesPage, State.nodePageSize);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

function renderPagination(type, total, page, pageSize) {
  const totalPages = Math.ceil(total / pageSize);
  const infoEl = document.getElementById(`${type}-pagination-info`);
  const pgEl = document.getElementById(`${type}-pagination`);

  infoEl.textContent = `Showing ${page * pageSize + 1}–${Math.min((page+1)*pageSize, total)} of ${total}`;
  pgEl.innerHTML = '';

  const prev = document.createElement('button');
  prev.className = 'btn btn-outline-secondary btn-sm'; prev.textContent = '‹ Prev';
  prev.disabled = page === 0;
  prev.onclick = () => { State[`${type}Page`]--; type === 'nodes' ? loadNodes() : loadEdges(); };
  pgEl.appendChild(prev);

  const next = document.createElement('button');
  next.className = 'btn btn-outline-secondary btn-sm'; next.textContent = 'Next ›';
  next.disabled = page >= totalPages - 1;
  next.onclick = () => { State[`${type}Page`]++; type === 'nodes' ? loadNodes() : loadEdges(); };
  pgEl.appendChild(next);
}

document.getElementById('btn-create-node').addEventListener('click', () => openNodeModal());
document.getElementById('btn-refresh-nodes').addEventListener('click', () => loadNodes());
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
      const resp = await HGAI_API.listGraphs({ status: 'active', limit: 200 });
      const sel = document.getElementById('node-graph-id');
      sel.innerHTML = '<option value="">— Select Hypergraph —</option>';
      (resp.items || []).forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id; opt.textContent = `${g.label} (${g.id})`;
        if (g.id === State.activeGraphId) opt.selected = true;
        sel.appendChild(opt);
      });
    } catch {}
  }

  if (isEdit && State.activeGraphId) {
    try {
      const n = await HGAI_API.getNode(State.activeGraphId, nodeId);
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
      document.getElementById('node-skos-broader').value = (n.skos_broader || []).join(', ');
      document.getElementById('node-skos-narrower').value = (n.skos_narrower || []).join(', ');
    } catch {}
  } else if (!isEdit) {
    document.getElementById('form-node').reset();
    document.getElementById('node-id').readOnly = false;
    document.getElementById('node-attributes').value = '{}';
    document.getElementById('node-type').value = 'Entity';
  }
  modal.show();
}

window.editNode = (id) => openNodeModal(id);
window.viewNode = async (id) => {
  const n = await HGAI_API.getNode(State.activeGraphId, id).catch(()=>null);
  showDetail(`Hypernode: ${id}`, n);
};
window.deleteNode = (id) => {
  confirmDelete(`Delete hypernode "${id}"?`, async () => {
    try {
      await HGAI_API.deleteNode(State.activeGraphId, id);
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
    skos_broader: parseTags(document.getElementById('node-skos-broader').value),
    skos_narrower: parseTags(document.getElementById('node-skos-narrower').value),
  };

  try {
    if (mode === 'create') {
      await HGAI_API.createNode(targetGraphId, data);
      // If we just created in a different graph, update the active graph so the table refreshes correctly
      if (targetGraphId !== State.activeGraphId) {
        State.activeGraphId = targetGraphId;
        document.getElementById('active-graph-select').value = targetGraphId;
        document.getElementById('nodes-graph-select').value = targetGraphId;
      }
      toast('Hypernode created');
    } else {
      await HGAI_API.updateNode(targetGraphId, id, data);
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
    document.getElementById('tbody-edges').innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">Select a hypergraph above</td></tr>';
    return;
  }
  const tbody = document.getElementById('tbody-edges');
  tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';

  const params = {
    skip: State.edgesPage * State.edgePageSize,
    limit: State.edgePageSize,
    relation: document.getElementById('edge-relation-filter').value.trim() || undefined,
    flavor: document.getElementById('edge-flavor-filter').value || undefined,
    node_id: document.getElementById('edge-node-filter').value.trim() || undefined,
  };

  try {
    const resp = await HGAI_API.listEdges(State.activeGraphId, params);
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No hyperedges found</td></tr>';
    } else {
      resp.items.forEach(e => {
        const membersSummary = (e.members || []).map(m => m.node_id).join(' · ') || '—';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><code class="text-truncate-150" title="${e.id||e.hyperkey}">${truncate(e.id||e.hyperkey, 24)}</code></td>
          <td><strong>${e.relation||'—'}</strong></td>
          <td><span class="badge badge-flavor">${e.flavor||'—'}</span></td>
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
    }
    renderPagination('edges', resp.total, State.edgesPage, State.edgePageSize);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

document.getElementById('btn-create-edge').addEventListener('click', () => openEdgeModal());
document.getElementById('btn-refresh-edges').addEventListener('click', () => loadEdges());
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
      const resp = await HGAI_API.listGraphs({ status: 'active', limit: 200 });
      const sel = document.getElementById('edge-graph-id');
      sel.innerHTML = '<option value="">— Select Hypergraph —</option>';
      (resp.items || []).forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id; opt.textContent = `${g.label} (${g.id})`;
        if (g.id === State.activeGraphId) opt.selected = true;
        sel.appendChild(opt);
      });
    } catch {}
  }

  if (isEdit && State.activeGraphId) {
    try {
      const e = await HGAI_API.getEdge(State.activeGraphId, edgeId);
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
    } catch {}
  } else if (!isEdit) {
    document.getElementById('form-edge').reset();
    document.getElementById('edge-id').readOnly = false;
    document.getElementById('edge-attributes').value = '{}';
    addMemberRow({ seq: 0 });
    addMemberRow({ seq: 1 });
  }
  modal.show();
}

window.editEdge = (id) => openEdgeModal(id);
window.viewEdge = async (id) => {
  const e = await HGAI_API.getEdge(State.activeGraphId, id).catch(()=>null);
  showDetail(`Hyperedge: ${id}`, e);
};
window.deleteEdge = (id) => {
  confirmDelete(`Delete hyperedge "${id}"?`, async () => {
    try {
      await HGAI_API.deleteEdge(State.activeGraphId, id);
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
  };

  try {
    if (mode === 'create') {
      await HGAI_API.createEdge(targetGraphId, data);
      if (targetGraphId !== State.activeGraphId) {
        State.activeGraphId = targetGraphId;
        document.getElementById('active-graph-select').value = targetGraphId;
        document.getElementById('nodes-graph-select').value = targetGraphId;
        document.getElementById('edges-graph-select').value = targetGraphId;
      }
      toast('Hyperedge created');
    } else {
      await HGAI_API.updateEdge(targetGraphId, id, data);
      toast('Hyperedge updated');
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-edge'))?.hide();
    loadEdges();
  } catch (err) { toast(err.message, 'danger'); }
});

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
    shql: `shql:\n  from: hello-world\n  where:\n    - union:\n        - - node: ?item\n            node_type: Person\n        - - node: ?item\n            node_type: Character\n  select:\n    - ?item.id\n    - ?item.label\n    - ?item.node_type`
  },
  {
    title: 'Multi-graph with ORDER BY and LIMIT',
    shql: `shql:\n  from:\n    - graph-1\n    - graph-2\n  where:\n    - node: ?n\n      node_type: Person\n  select:\n    - ?n.id\n    - ?n.label\n  order_by: ?n.label\n  limit: 10`
  },
  {
    title: 'Numeric attribute filter',
    shql: `shql:\n  from: hello-world\n  where:\n    - node: ?n\n    - filter:\n        ">=":\n          - ?n.attributes.score\n          - 90\n  select:\n    - ?n.id\n    - ?n.label\n    - ?n.attributes.score`
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
  document.getElementById('account-form-mode').value = username ? 'edit' : 'create';
  document.getElementById('modal-account-title').textContent = username ? `Edit: ${username}` : 'New Account';
  document.getElementById('pw-required').style.display = username ? 'none' : '';

  if (username) {
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
  } else {
    document.getElementById('form-account').reset();
    document.getElementById('account-username').readOnly = false;
    document.getElementById('role-user').checked = true;
  }
  modal.show();
}

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
async function loadMeshes() {
  const tbody = document.getElementById('tbody-meshes');
  tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td></tr>';
  try {
    const resp = await HGAI_API.listMeshes({ limit: 200 });
    tbody.innerHTML = '';
    if (!resp.items || !resp.items.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No meshes configured</td></tr>';
      return;
    }
    resp.items.forEach(m => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${m.id}</code></td>
        <td>${m.label||'—'}</td>
        <td>${(m.servers||[]).length} server(s)</td>
        <td>${statusBadge(m.status)}</td>
        <td class="text-end">
          <button class="btn btn-xs btn-outline-secondary me-1" onclick="viewMesh('${m.id}')"><i class="bi bi-eye"></i></button>
          <button class="btn btn-xs btn-outline-danger" onclick="deleteMesh('${m.id}')"><i class="bi bi-trash"></i></button>
        </td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">${err.message}</td></tr>`;
  }
}

window.viewMesh = async (id) => {
  const m = await HGAI_API.getMesh(id).catch(()=>null);
  showDetail(`Mesh: ${id}`, m);
};
window.deleteMesh = (id) => {
  confirmDelete(`Delete mesh "${id}"?`, async () => {
    try { await HGAI_API.deleteMesh(id); toast(`Mesh "${id}" deleted`); loadMeshes(); }
    catch (err) { toast(err.message, 'danger'); }
  });
};

document.getElementById('btn-create-mesh').addEventListener('click', () => {
  toast('Mesh creation coming soon — use the API or hgai shell', 'info');
});

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
