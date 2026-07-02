---
description: Enforce dict-first data modeling — no needless Pydantic models, dataclasses, or custom classes as data containers. Apply whenever writing, reviewing, or modifying Python code.
---

# No-Classes Rule: Dicts as the Primary Data Structure

This project uses plain Python `dict` as its primary flexible data structure. Do not introduce classes or class-based data containers unless absolutely necessary.

## What is FORBIDDEN

- **Pydantic models** — `BaseModel`, `BaseSettings`, `RootModel`, `@dataclass` from pydantic, `Field(...)`, validators, etc.
- **Dataclasses** — `@dataclasses.dataclass`, `@dataclass` from the standard library
- **NamedTuples as data containers** — `typing.NamedTuple`, `collections.namedtuple` used to model domain data
- **Custom classes used as data bags** — any `class Foo:` whose primary purpose is to hold data fields (with or without `__init__`, `__repr__`, etc.)
- **attrs / marshmallow / SQLModel / msgspec structs** — or any other class-based schema/validation library

## What is ALLOWED

- **Plain dicts** — `{}`, `dict()`, `TypedDict` (for type hints only, never instantiated as objects)
- **Type aliases** — `type UserRecord = dict[str, Any]` or `UserRecord = dict[str, Any]`
- **`typing.TypedDict`** — used purely for static type annotations; never instantiated directly or passed to `isinstance()`
- **`list`, `tuple`, `set`** — as collections of dicts or primitives
- **Utility/service classes** — classes that encapsulate *behaviour* (HTTP clients, file writers, algorithm implementations) with no data-holding fields are acceptable; they must not be used as record/DTO types
- **Enums** — `enum.Enum` subclasses for named constants are acceptable
- **Custom exceptions** — subclasses of `Exception` (or its built-in subclasses such as `ValueError`, `RuntimeError`) are acceptable when they signal a specific error condition. They carry *behaviour* (error signalling), not data fields. Keep them minimal — no instance attributes beyond what the base class provides:
  ```python
  # Good — signals a domain-specific failure, holds no data fields
  class StructureError(ValueError):
      """Raised when an entity dict does not match its schema."""
  ```

## How to model data with dicts

### Defining a schema (documentation only — use TypedDict)
```python
# Good
from typing import TypedDict, Any

class UserRecord(TypedDict):          # type hint only
    id: str
    name: str
    email: str
    metadata: dict[str, Any]

def make_user(id: str, name: str, email: str) -> UserRecord:
    return {"id": id, "name": name, "email": email, "metadata": {}}
```

### Validation — use plain functions, not class methods
```python
# Good
def validate_user(record: dict) -> None:
    if not record.get("id"):
        raise ValueError("user record missing 'id'")
    if not isinstance(record.get("email"), str):
        raise TypeError("email must be a string")
```

### Transformation / serialisation
```python
# Good
def to_api_response(user: dict) -> dict:
    return {"userId": user["id"], "displayName": user["name"]}
```

### Merging / updating records
```python
# Good — use dict unpacking or .update()
updated = {**existing_record, "name": new_name}
```

## When reviewing or generating code

- If you encounter a class whose sole purpose is to hold data fields, **replace it with a `dict` + factory function + optional `TypedDict` annotation**.
- If you encounter a Pydantic model, **convert it**: map fields to `TypedDict` keys, move validation logic into standalone functions, and replace `.model_dump()` / `.dict()` calls with the dict itself.
- If a function accepts a class instance, **refactor it to accept a plain dict**.
- Do not add `@dataclass`, `BaseModel`, or similar imports even as a "temporary" measure.
- If you believe a class is genuinely needed for behavioural reasons (not data holding), note the justification in a comment.