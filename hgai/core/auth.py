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


async def get_current_account(token: Optional[str] = Depends(oauth2_scheme)) -> AccountInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    # API key fast-path (no DB lookup required)
    if _resolve_api_key(token):
        return _api_key_account()

    # JWT validation
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        roles: List[str] = payload.get("roles", [])
        token_data = TokenData(username=username, roles=roles)
    except JWTError:
        raise credentials_exception

    account = await get_account_by_username(token_data.username)
    if account is None or account.status != "active":
        raise credentials_exception
    return account


async def require_admin(account: AccountInDB = Depends(get_current_account)) -> AccountInDB:
    if "admin" not in account.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return account


async def can_access_graph(
    account: AccountInDB, graph_id: str, space_id: Optional[str] = None
) -> bool:
    """Check if account can access a specific graph.

    For space-scoped graphs, space membership is the sole gate —
    permissions.graphs wildcards do NOT grant access to another tenant's space.
    For unowned (non-space) graphs, permissions.graphs is used as before.

    space_id should be passed when known to avoid an extra DB lookup.
    """
    if "admin" in account.roles:
        return True

    from hgai.core.space_engine import get_space_for_graph, get_member_role
    resolved_space_id = space_id or await get_space_for_graph(graph_id)

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
        resolved_space_id = space_id or await get_space_for_graph(graph_id)
        if resolved_space_id:
            role = await get_member_role(resolved_space_id, account.username)
            if role and operation in SPACE_ROLE_OPERATIONS.get(role, set()):
                return True
    return False


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
