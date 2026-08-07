# Mutation Summary

## Intent
`pip install -r requirements.txt` was failing with a `maturin`/`pep517` build error while building the `pydantic-core` wheel. The user wanted the failure diagnosed and fixed.

## Context
- The project venv (`.venv`) runs Python 3.14.4, and it is the only Python interpreter installed on this machine (no 3.11/3.12/3.13 available, so switching interpreters was not a viable fix).
- `requirements.txt` pinned `pydantic==2.10.3`, which resolves to `pydantic-core==2.27.x`.
- `pydantic-core` 2.27.x predates PyPI's `cp314` (Python 3.14) prebuilt wheels, so pip fell back to building it from source via `maturin`, which requires a Rust toolchain.
- No Rust toolchain (`rustc`/`cargo`) is installed on this machine, so the source build failed — this is the direct cause of the `maturin pep517 build-wheel` error.
- `pyproject.toml`'s dependency bounds (`pydantic>=2.10.0`, `pydantic-settings>=2.6.0`) already permitted newer versions; only the hard pins in `requirements.txt` were blocking an upgrade.

## What Changed and Why
- Verified via `pip index versions` and `pip install --dry-run` that `pydantic-core==2.46.4` (pulled in by `pydantic==2.13.4`) ships a prebuilt `manylinux` wheel for `cp314`, avoiding the Rust build entirely.
- Updated `requirements.txt` to pin `pydantic==2.13.4` and `pydantic-settings==2.15.0` (the versions that resolve to that compatible `pydantic-core` release).
- Ran `pip install -r requirements.txt` in the project venv to confirm the full dependency set now installs cleanly from prebuilt wheels, and confirmed `hgai.main` imports successfully afterward.

## Key Decisions
- Considered two fixes: (1) bump the `pydantic`/`pydantic-settings` pins to versions with prebuilt Python 3.14 wheels, or (2) install a Rust toolchain so `maturin` could build `pydantic-core` from source on the old pinned version. The user chose option 1 (recommended) since it removes the Rust toolchain dependency entirely and fixes the underlying version-skew issue for anyone else running Python 3.14, rather than papering over it with an extra system dependency.
