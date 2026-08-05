# Response Summary

## Question / Intent
The user wanted to know what hashing algorithm is used to produce the `password_hash` value stored on MongoDB `accounts` records.

## Answer / Recommendation
Bcrypt, via passlib. `hgai/core/auth.py` defines `pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")` and wraps it with `hash_password(password)` / `verify_password(plain, hashed)`. Account creation (`hgai/api/routers/accounts.py`, `bootstrap_admin` in `hgai/core/auth.py`) calls `hash_password()` and stores the result in the `password_hash` field; login (`authenticate_account`) calls `verify_password()` against the stored hash. `hgai/models/account.py:73` documents the field as "bcrypt password hash".

## Key Points
- `password_hash` is always stripped from API responses before returning account docs (`accounts.py` pops the field in multiple handlers).
- API-key authenticated requests use a synthetic in-memory account with `password_hash=""` — never persisted, not a real bcrypt hash.
- `deprecated="auto"` in the CryptContext means passlib would auto-upgrade hashes if the scheme list ever changes, but only bcrypt is currently configured.

## Context
Read-only codebase lookup across `hgai/core/auth.py`, `hgai/models/account.py`, and `hgai/api/routers/accounts.py`; no files were modified.
