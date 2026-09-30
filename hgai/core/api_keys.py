"""Tenant-scoped API keys: creation, and resolving a presented key to an account."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from hgai.db.storage import get_storage
from hgai.models.account import AccountInDB, AccountPermissions
from hgai.models.api_key import KEY_PREFIX, KEY_USERNAME_PREFIX, ApiKeyCreate, ApiKeyInDB
from hgai.models.common import now_utc

# Recording last use on every request would write on every request.
_LAST_USED_INTERVAL = timedelta(minutes=5)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def key_username(key_id: str) -> str:
    """The pseudo-username a key acts as (audit trails, space membership)."""
    return f"{KEY_USERNAME_PREFIX}{key_id}"


def key_id_from_username(username: str) -> Optional[str]:
    return username[len(KEY_USERNAME_PREFIX):] if username.startswith(KEY_USERNAME_PREFIX) else None


async def create_api_key(data: ApiKeyCreate, tenant_id: str, created_by: str) -> Tuple[ApiKeyInDB, str]:
    """Create a key for `tenant_id`. Returns (stored key, the secret, which is never stored)."""
    raw = KEY_PREFIX + secrets.token_urlsafe(32)
    now = now_utc()
    doc = {
        "id": uuid.uuid4().hex[:12],
        "label": data.label,
        "tenant_id": tenant_id,
        "key_prefix": raw[: len(KEY_PREFIX) + 6],
        "key_hash": hash_key(raw),
        "operations": data.operations,
        "expires_at": data.expires_at,
        "last_used": None,
        "status": "active",
        "tags": data.tags,
        "attributes": data.attributes,
        "system_created": now,
        "system_updated": now,
        "created_by": created_by,
        "version": 1,
    }
    return await get_storage().api_keys.create(doc), raw


async def tenant_of_key_username(username: str) -> Optional[Tuple[bool, str]]:
    """(found, tenant_id) for a key's pseudo-username, or None if it is not one."""
    key_id = key_id_from_username(username)
    if key_id is None:
        return None
    key = await get_storage().api_keys.get(key_id)
    return (key is not None), (key.tenant_id if key else None)


async def resolve_api_key(raw: str) -> Optional[AccountInDB]:
    """The account a stored key acts as, or None if it is unknown, revoked, expired or unusable.

    A tenant-scoped key is only honoured while tenancy is enforced: with the boundary off
    nothing would confine it to its tenant.
    """
    from hgai.core.auth import multitenancy_on

    if not raw.startswith(KEY_PREFIX) or not multitenancy_on():
        return None
    key = await get_storage().api_keys.get_by_hash(hash_key(raw))
    if key is None or key.status != "active":
        return None
    now = datetime.now(timezone.utc)
    if key.expires_at is not None:
        expires = key.expires_at if key.expires_at.tzinfo else key.expires_at.replace(tzinfo=timezone.utc)
        if expires <= now:
            return None
    last = key.last_used
    if last is None or (now - (last if last.tzinfo else last.replace(tzinfo=timezone.utc))) > _LAST_USED_INTERVAL:
        await get_storage().api_keys.touch(key.id, now)
    return AccountInDB(
        username=key_username(key.id),
        description=f"API key: {key.label}",
        roles=["agent"],
        tenant_id=key.tenant_id,
        permissions=AccountPermissions(graphs=["*"], operations=list(key.operations)),
        password_hash="",
        tags=["api-key"],
        status="active",
    )
