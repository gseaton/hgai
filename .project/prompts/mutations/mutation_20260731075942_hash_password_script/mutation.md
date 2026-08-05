# Mutation Log

## Created
- **scripts/hash_password.py** — Standalone CLI script that hashes a password with bcrypt (via passlib's `CryptContext`) and prints the resulting hash plus a verification check. Accepts the password as an argv arg or prompts via `getpass` if omitted.
