Generate and update project documentation: a root-level README, module-level docstrings, and function docstrings. Follow these steps exactly:

---

## Step 1 — Survey the codebase

Run these in parallel:

1. Find all Python source files (exclude `.venv/`, `site-packages/`, `__pycache__/`).
2. Find any existing documentation files: `README*`, `*.md` at the project root, any `docs/` directory.
3. Read `notes/dev/entity_structures.md` if it exists — it contains the intended domain model and is required context for accurate documentation.

Read every non-empty, non-test Python source file in full:
- `main.py`
- `scratch/math.py`
- `run_all.py`
- `models/structure.py`
- `stores/mongo/__init__.py`
- `stores/mongo/entities/annotation.py`

Also read the test infrastructure file `tests/runner.py`.

---

## Step 2 — Audit documentation gaps

For each source file, identify:

**Module docstrings** — is the first statement a `"""..."""` string describing the module's purpose, contents, and usage? If not, it is missing.

**Function docstrings** — does every non-trivial public function have a docstring? "Non-trivial" means it has branching logic, parameters, a meaningful return value, or can raise. Simple one-liners (e.g. `return x * 2`) do not require docstrings, though a module docstring noting their purpose is sufficient.

**Empty `__init__.py` files** — do not add docstrings to empty package marker files.

Build a list of every gap before writing anything.

---

## Step 3 — Write `README.md`

Write a `README.md` at the project root. Use the source files and `notes/dev/entity_structures.md` as the source of truth. Structure it exactly as follows:

```markdown
# annotativ

> One-sentence description of what annotativ is and does.

## Overview
Two to four sentences on the project's purpose, the problem it solves, and the core design philosophy (dict-first, no-classes, JSON Schema validation, MongoDB-backed).

## Architecture

### Layer diagram
A plain-text diagram showing how the layers relate:

    notes/dev/        ← domain model reference
    models/           ← JSON Schema definitions + validation
    stores/mongo/     ← MongoDB client, CRUD primitives
    stores/mongo/entities/  ← entity-specific operations (make, save, get, …)
    tests/            ← dict-based test framework + suites

### Design principles
Bullet list of the key decisions documented in `stores/mongo/__init__.py` and the no-classes rule: no ORM, no Pydantic, plain dicts everywhere, TypedDict for annotations only.

## Domain Model

### Entities
A markdown table or structured list of every entity type from `notes/dev/entity_structures.md`, with its key fields and relationships. Show which entities currently have JSON schemas defined in `models/structure.py` and which are planned but not yet implemented.

### Entity validation
Explain that every entity is defined as a JSON Schema dict in `models/structure.py`, validated with `validate_structure()`, and registered in `ENTITY_REGISTRY` for lookup by name.

## Getting Started

### Prerequisites
- Python 3.11+
- MongoDB (local or remote)
- Install dependencies: `pip install -r requirements.txt` (or note if none exists yet)

### Configuration
Describe the `.env` file: list the key environment variables (`MONGO_URI` or individual `MONGO_HOST` / `MONGO_PORT` / `MONGO_USERNAME` etc.) and what they control. Use the variable names from `stores/mongo/__init__.py`.

### Running the application
How to start / use the project (noting that `main.py` is currently a placeholder).

## Usage

### Creating and saving an annotation
A complete, runnable Python code example that calls `make_annotation`, then `save`.

### Querying annotations
A code example using `get_by_document` and/or `get_by_annotator`.

### Validating an entity dict
A code example calling `validate_structure` both with an explicit schema and via `entity_type=`.

## Testing

### Running the test suite
```
python run_all.py
```

### Running a single suite
```
python -m tests.scratch.math
python -m tests.models.structure
python -m tests.stores.mongo.entities.annotation
```

### Test framework
One paragraph explaining the dict-based framework in `tests/runner.py`: test cases as plain dicts with `arguments`, `expected_result`, and optional `expected_exception` / `kwargs` keys.

## Project Structure
A file tree (as a fenced code block) of the meaningful project files, with a one-line annotation for each.
```

Rules for writing `README.md`:
- Do not invent features, behaviors, or configuration options not present in the source.
- Where the `entity_structures.md` describes entities not yet implemented in code, label them clearly as "planned" rather than omitting them or presenting them as implemented.
- Keep code examples short — three to eight lines is ideal.
- No emojis.

---

## Step 4 — Add missing module docstrings

For each source file that lacks a module docstring, prepend one using the Edit tool. Follow this format:

```python
"""
<module/path.py>

<One sentence on what this module provides.>

<Two to four sentences describing the contents: what it defines, its design
approach, and its relationship to other modules it depends on or is used by.>

Usage
-----
    <minimal import + one-line usage example>
"""
```

Apply to every non-empty source file missing a module docstring. Do **not** add module docstrings to `__init__.py` files that are empty package markers.

---

## Step 5 — Add missing function docstrings

For each non-trivial function without a docstring, add one inline using the Edit tool. Use Google-style format, consistent with the existing docstrings in `models/structure.py` and `stores/mongo/entities/annotation.py`:

```python
def func(arg1: type, arg2: type) -> return_type:
    """One-sentence summary of what this function does.

    Args:
        arg1: Description.
        arg2: Description.

    Returns:
        Description of the return value.

    Raises:
        ErrorType: When this condition occurs.
    """
```

Omit sections that do not apply (e.g. no `Raises:` if the function never raises, no `Returns:` for `-> None`).

For **`tests/runner.py`**, document `execute_test`, `execute_tests`, and `print_results`. Keep docstrings brief — one summary line plus Args/Returns is sufficient for test infrastructure.

For **`scratch/math.py`**, a module docstring explaining it is a scratch utilities module is sufficient; individual one-liner function docstrings are optional but welcome if they add clarity.

Do **not** add docstrings to:
- Empty `__init__.py` files
- Functions that already have adequate docstrings
- Private helpers where the name is self-explanatory and the function is trivial (e.g. `_new_id`, `_utcnow`)

---

## Step 6 — Report to the user

After all writes and edits are complete, output:

1. A bullet list of every file created or modified, with a one-line note on what was added.
2. A one-sentence overall summary of the state of project documentation now that this command has run.