"""Symmetric encryption for vendor API keys at rest.

Keyed by the same HGAI_SECRET_KEY already required for JWT signing (see
hgai.config.Settings.secret_key) — no separate secret to provision or
rotate independently. This is encryption-at-rest against DB compromise; it
is not a substitute for restricting who can reach the admin-only vendor
endpoints in the first place (see hgai.core.auth.require_admin).
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from hgai.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    key_bytes = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_api_key(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_api_key(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError(
            "Stored API key could not be decrypted — HGAI_SECRET_KEY may have changed since it was saved"
        )


def last4(plaintext: str) -> str:
    return plaintext[-4:] if len(plaintext) >= 4 else plaintext
