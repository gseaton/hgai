Assess the quality and completeness of unit test coverage across the codebase. This is a qualitative audit, not a line-coverage count. Follow these steps exactly:

---

## Step 1 — Get the timestamp

Run two Bash commands in parallel:
- `date +%Y%m%d%H%M%S` — for the filename
- `date --iso-8601=seconds` — for the report header

## Step 2 — Discover source and test files

Use Bash to list all `.py` files in the project, excluding `.venv/`, `site-packages/`, `__pycache__/`, `.project/`, and the `tests/` tree itself. This is the **source surface**.

Then list all `.py` files under `tests/`, excluding `__init__.py` files and `tests/runner.py` (infrastructure, not tests). This is the **test surface**.

## Step 3 — Build the coverage map

For each source file, determine:
- Its corresponding test file path (mirror the directory structure under `tests/`).
- Whether that test file exists.
- Whether the test file is non-empty (has actual test cases defined).

Read every source file and every existing test file in full.

## Step 4 — Enumerate and classify every public callable

For each source module (skip `main.py`, `run_all.py`, and any `__init__.py` that is empty):

1. List every public function (not prefixed with `_`) defined in the module.
2. For each function, determine:
   - **Tested?** Does the corresponding test file exercise this function?
   - **Coverage tier** — assign exactly one of the four tiers below.
   - **Gaps** — what scenarios are untested that would meaningfully catch bugs?

### Coverage Tier Definitions

| Tier | Label | Assign when… |
|------|-------|--------------|
| **Significant** | `[SIG]` | Tests exercise error paths, boundary values, branching logic, schema/type validation, or any scenario where a bug could silently return a wrong result. These tests are the most valuable — they catch real defects. |
| **Necessary** | `[NEC]` | Tests cover the standard happy path and expected return shape, but miss error paths or interesting edge cases. The function has meaningful logic and warrants this baseline. |
| **Trivial** | `[TRV]` | The function is so simple (a one-liner, a direct pass-through, a single arithmetic operation) that a test provides little protection — failure would indicate a Python or interpreter bug, not an app bug. Testing is optional. |
| **Unnecessary** | `[UNN]` | Existing tests verify third-party / stdlib / framework behaviour, not app logic. Or tests are so tightly coupled to implementation details that they break on every internal refactor without catching real regressions. These tests add maintenance burden without safety. |

When a function is **untested**, note its potential tier if it were tested (e.g. "Untested — warrants `[NEC]`").

### Additional classification notes

- A function may have *some* tests at one tier while also having *gaps* at a higher tier. For example, a function tested only for the happy path (`[NEC]`) may have significant untested error paths (`[SIG]` gap).
- Private helpers (`_name`) that are exclusively exercised through tested public functions can be listed as "covered indirectly" — do not require their own test cases.
- Functions requiring a live external service (database, network) cannot be unit-tested in isolation; note them as "integration-only" and assess what *can* be unit-tested (pure logic, factory functions, validators).

## Step 5 — Identify gaps

For each public function, identify specific untested scenarios. Prioritise:

1. **Error paths**: Does the function raise? Are those raises tested?
2. **Optional parameters**: Are keyword arguments with defaults ever exercised in tests?
3. **Boundary inputs**: Empty strings, zero, None, empty collections, maximum/minimum values.
4. **Return value shape**: Is the structure of returned dicts verified, or just that something is returned?

## Step 6 — Ensure the output directory exists

Run: `mkdir -p .project/tests/assessments`

## Step 7 — Write the assessment file

Write the report to `.project/tests/assessments/<YYYYMMDDHHMMSS>_test_assessment.md` using this exact structure:

```markdown
# Test Coverage Assessment
Generated: <ISO datetime>

## Executive Summary
- Source modules assessed: N
- Public functions surveyed: N
- Functions with coverage: N (X%)
- Functions without coverage: N (Y%)
- Overall quality rating: STRONG | ADEQUATE | WEAK | CRITICAL

> **Rating guide:** STRONG = all significant and necessary functions are well-tested.
> ADEQUATE = most necessary coverage is present; some significant gaps exist.
> WEAK = major gaps in necessary coverage; significant paths untested.
> CRITICAL = large portions of the codebase have no tests at all.

---

## Coverage Tier Key
| Tier | Meaning |
|------|---------|
| `[SIG]` | Significant — tests catch real, non-obvious defects |
| `[NEC]` | Necessary — standard happy/error path coverage present |
| `[TRV]` | Trivial — function too simple to meaningfully break |
| `[UNN]` | Unnecessary — tests verify framework/stdlib, not app logic |

---

## Module Assessments

### `<source/module.py>`
**Test file:** `tests/<module.py>` ✅ exists | ❌ missing

| Function | Tier | Tested? | Notes |
|----------|------|---------|-------|
| `func_name` | `[SIG]` | ✅ Yes | Brief one-line description |
| `func_name` | `[NEC]` | ⚠️ Partial | What's covered and what's missing |
| `func_name` | `[TRV]` | ✅ Yes | Trivial; tests optional |
| `func_name` | `[NEC]` | ❌ No | Untested — warrants [NEC] |

#### Gaps in `<source/module.py>`
- `func_name`: <specific missing scenario and why it matters>
- `func_name`: <specific missing scenario and why it matters>

> _No gaps._ ← use this if the module is fully and appropriately covered

[Repeat `### Module` block for every non-empty source module]

---

## Untested Surface

Functions and modules with no test coverage at all, ranked by risk (highest first):

| Risk | Module | Function | Reason coverage matters |
|------|--------|----------|------------------------|
| HIGH | `path/module.py` | `func_name` | One sentence on what could silently break |
| MED  | `path/module.py` | `func_name` | … |
| LOW  | `path/module.py` | `func_name` | … |

> _No untested surface._ ← use this if everything is covered

---

## Recommendations

### High Priority — add or expand significant coverage
- **`module.py :: func_name`**: <what to add and why it catches real bugs>

### Medium Priority — fill necessary coverage gaps
- **`module.py :: func_name`**: <what basic case is missing>

### Low Priority / Defer — trivial or marginal value
- **`module.py :: func_name`**: <why this can wait>

### Consider Removing — unnecessary tests
- **`tests/module.py :: test case description`**: <why this test adds maintenance cost without safety>

> _No recommendations._ ← use this section only if it truly applies
```

Rules for writing the assessment:
- Be specific: name the exact missing scenario, not just "add more tests".
- Be honest: if a test suite is genuinely good, say so — do not manufacture gaps.
- Do not count lines or statements; judge based on logical scenarios and risk.
- If a whole module is untestable without a live service, note it clearly and assess only what is unit-testable within it.
- Use `⚠️ Partial` in the Tested column when some but not all meaningful paths are covered.

## Step 8 — Report to the user

Output the path to the written file and a two-sentence plain-English verdict: the overall rating and the single most important action to take next.
