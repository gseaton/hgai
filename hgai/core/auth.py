"""Authentication and RBAC for HypergraphAI."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from hgai.config import get_settings
from hgai.db.storage import get_storage
from hgai.models.account import AccountInDB, AccountPermissions, TokenData

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
    return account


async def get_current_account(token: Optional[str] = Depends(oauth2_scheme)) -> AccountInDB:
    account = await authenticate_token(token)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return account


async def require_admin(account: AccountInDB = Depends(get_current_account)) -> AccountInDB:
    if "admin" not in account.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return account


async def can_access_graph(
    account: AccountInDB, graph_id: str, space_id: Optional[str] = None,
    unowned: bool = False,
) -> bool:
    """Check if account can access a specific graph.

    For space-scoped graphs, space membership is the sole gate —
    permissions.graphs wildcards do NOT grant access to another tenant's space.
    For unowned (non-space) graphs, permissions.graphs is used as before.

    space_id should be passed when known to avoid an extra DB lookup.
    unowned=True asserts the graph is a non-space graph, skipping the
    id-only space lookup — which would otherwise be ambiguous if a space also
    holds a graph with the same id.
    """
    if "admin" in account.roles:
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


async def can_perform(
    account: AccountInDB,
    operation: str,
    graph_id: Optional[str] = None,
    space_id: Optional[str] = None,
    unowned: bool = False,
) -> bool:
    """Check if account can perform an operation.

    When graph_id is given, also checks the caller's space role for that graph
    in case they lack the operation in their direct account permissions.
    space_id should be passed when known to avoid ambiguous lookups.
    """
    if "admin" in account.roles:
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


class PermissionDeniedError(Exception):
    """The caller is authenticated but not permitted to do this."""


async def check_graph_permission(
    account: AccountInDB,
    graph_id: str,
    operation: str = "read",
    space_id: Optional[str] = None,
    unowned: bool = False,
) -> None:
    """Raise PermissionDeniedError unless `account` may perform `operation` on the graph.

    The single enforcement point behind the REST `require_graph_access`
    dependency, the MCP tools and SHQL execution, so all three agree.
    """
    if not await can_access_graph(account, graph_id, space_id=space_id, unowned=unowned):
        raise PermissionDeniedError(f"Access to graph '{graph_id}' not permitted")
    if not await can_perform(account, operation, graph_id=graph_id, space_id=space_id, unowned=unowned):
        raise PermissionDeniedError(f"Operation '{operation}' not permitted")


def require_admin_role(account: AccountInDB, what: str = "this operation") -> None:
    """Raise PermissionDeniedError unless `account` has the admin role."""
    if "admin" not in account.roles:
        raise PermissionDeniedError(f"Admin role required for {what}")


async def check_space_role(account: AccountInDB, space_id: str, minimum: str = "viewer") -> None:
    """Raise PermissionDeniedError unless `account` holds `minimum` (or a higher) role in the space.

    Admins pass. `minimum` is a SpaceRole value: viewer < member < admin < owner.
    """
    if "admin" in account.roles:
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

    Space membership is resolved once per distinct space rather than per graph.
    """
    if "admin" in account.roles:
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
