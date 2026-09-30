"""Authentication and RBAC for HypergraphAI."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from hgai.config import get_settings
from hgai.db.storage import get_storage
from hgai.core.tenant_engine import effective_tenant_id
from hgai.models.account import AccountInDB, AccountPermissions, SystemRole, TokenData

from hgai.models.space import SpaceRole

# Space role ordering: a higher rank includes everything a lower one may do.
SPACE_ROLE_RANK = {
    SpaceRole.viewer: 0,
    SpaceRole.member: 1,
    SpaceRole.admin: 2,
    SpaceRole.owner: 3,
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# auto_error=False so we can fall through to API key check when the header is missing or invalid
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def _api_key_account() -> AccountInDB:
    """Return a synthetic admin AccountInDB for API key authenticated requests."""
    return AccountInDB(
        username="api-key",
        email=None,
        description="Machine-to-machine API key account",
        roles=["admin"],
        permissions=AccountPermissions(
            graphs=["*"],
            operations=["read", "write", "delete", "admin", "query", "export", "import"],
        ),
        password_hash="",
        tags=["system", "api-key"],
        status="active",
    )


def _resolve_api_key(token: str) -> bool:
    """Return True if token matches a configured API key."""
    if not token:
        return False
    settings = get_settings()
    keys = [k for k in (settings.primary_api_key, settings.secondary_api_key) if k]
    return token in keys


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(username: str, roles: List[str]) -> tuple[str, int]:
    settings = get_settings()
    expire_minutes = settings.token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": username,
        "roles": roles,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, expire_minutes * 60


async def get_account_by_username(username: str) -> Optional[AccountInDB]:
    raw = await get_storage().accounts.get_by_username(username)
    if not raw:
        return None
    return AccountInDB(**raw)


async def authenticate_account(username: str, password: str) -> Optional[AccountInDB]:
    account = await get_account_by_username(username)
    if not account:
        return None
    if not verify_password(password, account.password_hash):
        return None
    if account.status != "active":
        return None
    if not await _tenant_active(account):
        return None
    return account


async def authenticate_token(token: Optional[str]) -> Optional[AccountInDB]:
    """Resolve a bearer credential (API key or JWT) to an active account.

    Returns None for a missing/invalid/expired token, an unknown account, or an
    account that is not active. Shared by the REST dependency and the MCP
    endpoint so both authenticate identically.
    """
    if not token:
        return None

    # API key fast-path (no DB lookup required)
    if _resolve_api_key(token):
        return _api_key_account()

    # A stored, tenant-scoped API key
    from hgai.core.api_keys import resolve_api_key
    key_account = await resolve_api_key(token)
    if key_account is not None:
        return key_account if await _tenant_active(key_account) else None

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
        roles: List[str] = payload.get("roles", [])
        token_data = TokenData(username=username, roles=roles)
    except JWTError:
        return None

    account = await get_account_by_username(token_data.username)
    if account is None or account.status != "active":
        return None
    if not await _tenant_active(account):
        return None
    return account


async def get_current_account(
    request: Request, token: Optional[str] = Depends(oauth2_scheme)
) -> AccountInDB:
    account = await authenticate_token(token)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Stashed on the ASGI scope (not just this Request instance) so telemetry's
    # outer middleware — which runs before FastAPI's own dependency injection —
    # can read the authenticated account after the fact, without re-running
    # authentication. See hgai_module_telemetry/middleware.py.
    request.state.account = account
    _enforce_auditor_limits(request, account)
    return account


# ─── Tenancy ──────────────────────────────────────────────────────────────────
# See docs/architecture/hypergraph-ai-multi-tenancy-*.md §5. The tenant boundary is
# evaluated BEFORE roles, space membership and permissions.graphs wildcards, and
# only when HGAI_MULTITENANCY_ENABLED is on, so a deployment that leaves it off
# behaves exactly as before.


class PermissionDeniedError(Exception):
    """The caller is authenticated but not permitted to do this."""


class TenantBoundaryError(PermissionDeniedError):
    """The resource belongs to another tenant. REST maps this to 404, not 403,
    so a caller cannot probe which ids exist in other tenants."""


def multitenancy_on() -> bool:
    return get_settings().multitenancy_enabled


def is_system_admin(account: AccountInDB) -> bool:
    """System-wide root: all tenants, spaces and graphs. The legacy global `admin` role reads as this."""
    return account.system_role == SystemRole.system_admin


# What a system auditor may do to graphs: look, query and export.
AUDITOR_OPERATIONS = frozenset({"read", "query", "export"})

# A system auditor is read-only. The one central guard below refuses every request that
# is not a read, except these read-only computations that happen to be POSTs, and refuses
# the routes that hold users' own data.
_AUDITOR_POST_OK = ("/shql/query", "/shql/validate", "/shql/history", "/telemetry/ingest",
                    "/export", "/infer/transitive", "/infer/expand")
_AUDITOR_BLOCKED = ("/api/v1/notes", "/api/v1/media", "/api/v1/parameterized-queries", "/api/v1/agent")


def is_system_auditor(account: AccountInDB) -> bool:
    return account.system_role == SystemRole.system_auditor


def sees_all_tenants(account: AccountInDB) -> bool:
    """System admins and system auditors are not bound to any tenant."""
    return is_system_admin(account) or is_system_auditor(account)


def _enforce_auditor_limits(request: Request, account: AccountInDB) -> None:
    if not is_system_auditor(account):
        return
    path, method = request.url.path, request.method.upper()
    if any(path == p or path.startswith(p + "/") for p in _AUDITOR_BLOCKED):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="System auditors cannot access users' own notes, media, saved queries or chats")
    if method not in ("GET", "HEAD", "OPTIONS") and not (
        method == "POST" and any(path.endswith(ok) for ok in _AUDITOR_POST_OK)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System auditors are read-only")


def is_tenant_admin(account: AccountInDB) -> bool:
    return "tenant_admin" in account.roles


def _tenant_admin_in_force(account: AccountInDB) -> bool:
    """A tenant admin has full rights inside its own tenant, only while tenancy is enforced."""
    return multitenancy_on() and is_tenant_admin(account) and not is_system_admin(account)


async def _tenant_active(account: AccountInDB) -> bool:
    """False when tenancy is enforced and the account's tenant is missing or suspended."""
    if not multitenancy_on() or sees_all_tenants(account):
        return True
    tenant = await get_storage().tenants.get(effective_tenant_id(account))
    return tenant is not None and tenant.status == "active"


async def _graph_tenant(graph_id: str, space_id: Optional[str], unowned: bool):
    """(found, tenant_id) for a graph. A space graph's tenant is its space's."""
    from hgai.core.space_engine import get_space_for_graph

    resolved = space_id or (None if unowned else await get_space_for_graph(graph_id))
    if resolved:
        space = await get_storage().spaces.get(resolved)
        return (space is not None), (space.tenant_id if space else None)
    graph = await get_storage().hypergraphs.get(graph_id, space_id=None)
    return (graph is not None), (graph.tenant_id if graph else None)


async def _tenant_allows_graph(
    account: AccountInDB, graph_id: str, space_id: Optional[str], unowned: bool
) -> bool:
    """The tenant boundary for one graph. A graph that does not exist has nothing to isolate."""
    if not multitenancy_on() or sees_all_tenants(account):
        return True
    found, tenant = await _graph_tenant(graph_id, space_id, unowned)
    return (not found) or tenant == effective_tenant_id(account)


def tenant_scope(account: AccountInDB) -> Optional[str]:
    """The tenant to filter this caller's lists by, or None for no filter (tenancy
    off, or a system admin or auditor, who see every tenant)."""
    if not multitenancy_on() or sees_all_tenants(account):
        return None
    return effective_tenant_id(account)


async def graph_access_for(account: AccountInDB):
    """The storage-level filter for listing graphs as `account`, or None when nothing needs
    filtering (system admin; a tenant admin, whose tenant filter is applied separately).
    Mirrors can_access_graph: space membership for space graphs, permissions.graphs for
    unowned ones."""
    if sees_all_tenants(account) or _tenant_admin_in_force(account):
        return None
    from hgai_module_storage.filters import GraphAccess
    perms = account.permissions
    spaces = await get_storage().spaces.list_active_space_ids_for_user(account.username)
    return GraphAccess(
        space_ids=list(spaces),
        unowned_ids=None if "*" in perms.graphs else list(perms.graphs),
    )


def space_visibility(account: AccountInDB):
    """(username, tenant_id) filters for listing spaces as `account`.

    System admin: everything. Otherwise only the caller's tenant (when enforced),
    and within it the spaces the caller belongs to, except a tenant admin, who
    sees all of its tenant's spaces.
    """
    if sees_all_tenants(account):
        return None, None
    if not multitenancy_on():
        return account.username, None
    return (None if is_tenant_admin(account) else account.username), effective_tenant_id(account)


async def check_composition_tenancy(account: AccountInDB, member_ids) -> None:
    """Raise TenantBoundaryError if a logical graph would compose another tenant's graph.

    Query time already requires access to every composed member; this stops the
    reference being created at all, so a tenant cannot probe for or wire up graphs
    it cannot see. Unknown members are ignored (a composition may name graphs that
    do not exist yet).
    """
    if not multitenancy_on() or sees_all_tenants(account):
        return
    for member_id in member_ids or []:
        member = await get_storage().hypergraphs.find_composition_member(member_id)
        if member is not None:
            check_record_tenant(account, member.tenant_id, f"Composed hypergraph '{member_id}'")


def check_record_tenant(account: AccountInDB, record_tenant_id: Optional[str], what: str = "Resource") -> None:
    """Raise TenantBoundaryError unless the caller may reach a record stamped with
    `record_tenant_id` (None means system level: system admins only)."""
    if not multitenancy_on() or is_system_admin(account):
        return
    if record_tenant_id != effective_tenant_id(account):
        raise TenantBoundaryError(f"{what} not found")


def can_administer_tenant(account: AccountInDB, tenant_id: str) -> bool:
    """System admins administer every tenant; a tenant admin only its own."""
    if is_system_admin(account):
        return True
    return is_tenant_admin(account) and effective_tenant_id(account) == tenant_id


# ─── Role gates ───────────────────────────────────────────────────────────────

async def require_system_admin(account: AccountInDB = Depends(get_current_account)) -> AccountInDB:
    if not is_system_admin(account):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return account


# Legacy name: the global admin role is now the system admin.
require_admin = require_system_admin


async def require_tenant_admin(account: AccountInDB = Depends(get_current_account)) -> AccountInDB:
    """System admin, or (while tenancy is enforced) a tenant admin. Routes that take
    a target tenant must additionally check `can_administer_tenant`."""
    if not (is_system_admin(account) or _tenant_admin_in_force(account)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin role required"
        )
    return account


async def require_tenant_reader(account: AccountInDB = Depends(get_current_account)) -> AccountInDB:
    """Who may read tenant-level administration (accounts, tenants): a system admin, a system
    auditor, or (while tenancy is enforced) a tenant admin for its own tenant."""
    if not (sees_all_tenants(account) or _tenant_admin_in_force(account)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin or system role required"
        )
    return account


async def _access_inner(
    account: AccountInDB, graph_id: str, space_id: Optional[str], unowned: bool
) -> bool:
    """Space membership, else permissions.graphs. The tenant boundary is applied by the callers."""
    if _tenant_admin_in_force(account):
        return True

    from hgai.core.space_engine import get_space_for_graph, get_member_role
    resolved_space_id = space_id or (None if unowned else await get_space_for_graph(graph_id))

    if resolved_space_id:
        # Space-scoped graph: membership is the only gate
        role = await get_member_role(resolved_space_id, account.username)
        return role is not None

    # Unowned graph: fall through to permissions.graphs
    perms = account.permissions
    return "*" in perms.graphs or graph_id in perms.graphs


async def _perform_inner(
    account: AccountInDB, operation: str, graph_id: Optional[str], space_id: Optional[str], unowned: bool
) -> bool:
    if _tenant_admin_in_force(account):
        return True
    if operation in account.permissions.operations:
        return True
    # Space role path
    if graph_id:
        from hgai.core.space_engine import get_space_for_graph, get_member_role
        from hgai.models.space import SPACE_ROLE_OPERATIONS
        resolved_space_id = space_id or (None if unowned else await get_space_for_graph(graph_id))
        if resolved_space_id:
            role = await get_member_role(resolved_space_id, account.username)
            if role and operation in SPACE_ROLE_OPERATIONS.get(role, set()):
                return True
    return False


async def can_access_graph(
    account: AccountInDB, graph_id: str, space_id: Optional[str] = None,
    unowned: bool = False,
) -> bool:
    """Check if account can access a specific graph.

    Order: system admin, tenant boundary, tenant admin, then for space-scoped
    graphs space membership is the sole gate (permissions.graphs wildcards do NOT
    grant access to another tenant's or another space's graphs), and for unowned
    (non-space) graphs permissions.graphs is used.

    space_id should be passed when known to avoid an extra DB lookup.
    unowned=True asserts the graph is a non-space graph, skipping the
    id-only space lookup — which would otherwise be ambiguous if a space also
    holds a graph with the same id.
    """
    if sees_all_tenants(account):
        return True
    if not await _tenant_allows_graph(account, graph_id, space_id, unowned):
        return False
    return await _access_inner(account, graph_id, space_id, unowned)


async def can_perform(
    account: AccountInDB,
    operation: str,
    graph_id: Optional[str] = None,
    space_id: Optional[str] = None,
    unowned: bool = False,
) -> bool:
    """Check if account can perform an operation.

    When graph_id is given, also checks the tenant boundary and the caller's
    space role for that graph in case they lack the operation in their direct
    account permissions. space_id should be passed when known to avoid
    ambiguous lookups.
    """
    if is_system_admin(account):
        return True
    if is_system_auditor(account):
        return operation in AUDITOR_OPERATIONS
    if graph_id and not await _tenant_allows_graph(account, graph_id, space_id, unowned):
        return False
    return await _perform_inner(account, operation, graph_id, space_id, unowned)


async def check_graph_permission(
    account: AccountInDB,
    graph_id: str,
    operation: str = "read",
    space_id: Optional[str] = None,
    unowned: bool = False,
) -> None:
    """Raise PermissionDeniedError unless `account` may perform `operation` on the graph.

    The single enforcement point behind the REST `require_graph_access`
    dependency, the MCP tools and SHQL execution, so all three agree. A graph in
    another tenant raises TenantBoundaryError.
    """
    if is_system_admin(account):
        return
    if is_system_auditor(account):
        if operation not in AUDITOR_OPERATIONS:
            raise PermissionDeniedError(f"Operation '{operation}' not permitted: system auditors are read-only")
        return
    if not await _tenant_allows_graph(account, graph_id, space_id, unowned):
        raise TenantBoundaryError(f"Hypergraph '{graph_id}' not found")
    if not await _access_inner(account, graph_id, space_id, unowned):
        raise PermissionDeniedError(f"Access to graph '{graph_id}' not permitted")
    if not await _perform_inner(account, operation, graph_id, space_id, unowned):
        raise PermissionDeniedError(f"Operation '{operation}' not permitted")


def require_admin_role(account: AccountInDB, what: str = "this operation") -> None:
    """Raise PermissionDeniedError unless `account` is a system admin."""
    if not is_system_admin(account):
        raise PermissionDeniedError(f"Admin role required for {what}")


async def check_space_role(account: AccountInDB, space_id: str, minimum: str = "viewer") -> None:
    """Raise PermissionDeniedError unless `account` holds `minimum` (or a higher) role in the space.

    System admins pass; so does a tenant admin inside its own tenant. A space in
    another tenant raises TenantBoundaryError. `minimum` is a SpaceRole value:
    viewer < member < admin < owner.
    """
    if is_system_admin(account):
        return
    if is_system_auditor(account):
        if minimum != "viewer":
            raise PermissionDeniedError("System auditors are read-only")
        return
    if multitenancy_on():
        space = await get_storage().spaces.get(space_id)
        if space is not None:
            if space.tenant_id != effective_tenant_id(account):
                raise TenantBoundaryError(f"Space '{space_id}' not found")
            if is_tenant_admin(account):
                return
    from hgai.core.space_engine import get_member_role
    from hgai.models.space import SpaceRole

    role = await get_member_role(space_id, account.username)
    if role is None:
        raise PermissionDeniedError(f"Not a member of space '{space_id}'")
    if SPACE_ROLE_RANK.get(SpaceRole(role), -1) < SPACE_ROLE_RANK[SpaceRole(minimum)]:
        raise PermissionDeniedError(f"Space role '{minimum}' or higher required")


async def filter_accessible_graphs(account: AccountInDB, graphs: list) -> list:
    """Keep only the graphs `account` may access — same rule as can_access_graph.

    Other tenants' graphs are dropped first. Space membership is resolved once
    per distinct space rather than per graph.
    """
    if sees_all_tenants(account):
        return list(graphs)
    if multitenancy_on():
        mine = effective_tenant_id(account)
        graphs = [g for g in graphs if g.tenant_id == mine]
        if is_tenant_admin(account):
            return list(graphs)
    from hgai.core.space_engine import get_member_role

    perms = account.permissions
    member_of: dict = {}
    allowed = []
    for g in graphs:
        if g.space_id:
            if g.space_id not in member_of:
                member_of[g.space_id] = (await get_member_role(g.space_id, account.username)) is not None
            if member_of[g.space_id]:
                allowed.append(g)
        elif "*" in perms.graphs or g.id in perms.graphs:
            allowed.append(g)
    return allowed


async def bootstrap_admin(username: str, password: str, email: str) -> bool:
    """Create admin account if it does not exist. Returns True if created."""
    if await get_storage().accounts.exists(username):
        return False

    from hgai.models.common import now_utc
    from hgai.models.account import AccountPermissions, Role

    now = now_utc()
    doc = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "roles": ["admin"],
        "permissions": {
            "graphs": ["*"],
            "operations": ["read", "write", "delete", "admin", "query", "export", "import"]
        },
        "tags": ["system", "admin"],
        "status": "active",
        "system_created": now,
        "system_updated": now,
        "created_by": "system",
        "version": 1,
        "last_login": None,
        "description": "System administrator account",
        "attributes": {}
    }
    await get_storage().accounts.create(doc)
    return True
