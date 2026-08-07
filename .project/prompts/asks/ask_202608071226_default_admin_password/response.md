# Response Summary

## Question / Intent
The user wanted to know the default password for the bootstrapped `admin` account.

## Answer / Recommendation
The default admin password is `pwd357`, defined in `hgai/config.py` (`admin_password: str = Field(default="pwd357")`). It is used by `bootstrap_admin()` in `hgai/main.py` on first server run to create the admin account if one doesn't exist. It can be overridden via the `HGAI_ADMIN_PASSWORD` environment variable (the `Settings` class uses env prefix `HGAI_`).

## Key Points
- Flagged as a hardcoded default credential risk: any deployment that doesn't set `HGAI_ADMIN_PASSWORD` in `.env` gets `admin`/`pwd357` out of the box.
- Same pattern exists for `secret_key` (JWT signing key), which also defaults to an insecure placeholder value (`"insecure-default-change-me"`).

## Context
Found in `hgai/config.py`, the `Settings` (pydantic-settings `BaseSettings`) class that backs `hgai/main.py`'s admin bootstrap logic.
