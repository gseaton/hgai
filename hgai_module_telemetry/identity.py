"""Identifier hashing for telemetry events.

Account, graph and space ids are HMAC-hashed by default (plan §3, §5) so
events can be grouped per-identifier *within one deployment* without being
reversible or comparable across two different customers' deployments.

The HMAC key is `settings.secret_key` — already a per-deployment secret
(it signs JWTs, see hgai/config.py) rather than a freshly-generated value
stored alongside the admin bootstrap record. Phase 1 reuses it rather than
adding a new persisted-settings mechanism purely for this: it has the same
security property the plan asks for (a stable, per-deployment, non-public
value), and every deployment already has one.
"""

import hashlib
import hmac

from hgai.config import Settings


def hash_id(value: str, settings: Settings) -> str:
    """HMAC-SHA256(value, settings.secret_key), hex-encoded."""
    return hmac.new(
        settings.secret_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
    ).hexdigest()
