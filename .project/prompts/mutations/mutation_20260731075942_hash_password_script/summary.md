# Mutation Summary

## Intent
The user wanted a runnable, standalone Python script (not just an inline code snippet) that hashes a password and prints the hashed output, following an earlier discussion of how `accounts.password_hash` is generated in this codebase.

## Context
Earlier in the session, the user asked what hashing scheme is used for the `password_hash` field on MongoDB `accounts` records (see `.project/prompts/asks/ask_202607310751_password_hashing/`), and the answer was bcrypt via passlib's `CryptContext` in `hgai/core/auth.py`. The user then asked to "show" a simple script (answered inline, no file written — see `.project/prompts/asks/ask_202607310753_hash_password_script/`). This request repeated the ask but said "generate a simple complete python script," which was interpreted as wanting an actual file this time rather than just an inline example.

## What Changed and Why
- Created `scripts/hash_password.py`, placed alongside the existing `scripts/seed_data.py` and `scripts/mongo-init.js` utility scripts since that directory is already the project's convention for standalone operational scripts.
- The script reuses the exact same hashing approach as `hgai/core/auth.py` (`passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")`) so any hash it produces is consistent with what the application itself would store in `accounts.password_hash`.
- Verified the script runs correctly using the project's `.venv` (`passlib` is a declared dependency in both `requirements.txt` and `pyproject.toml`, but not present in the system Python).

## Key Decisions
- Chose to duplicate the small `hash_password`/`verify_password` helper functions locally in the script rather than importing them from `hgai.core.auth`, since the script is meant as a simple, dependency-light standalone utility runnable outside the full app context (no FastAPI/DB/config wiring required).
- Password is read via `getpass.getpass()` when not passed as an argument, avoiding plaintext passwords showing up in shell history by default.
