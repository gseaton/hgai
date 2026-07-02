Run the full project test suite and save a timestamped summary to `.project/tests/`. Follow these steps exactly:

## Step 1 — Get the timestamp

Run two Bash commands in parallel:
- `date +%Y%m%d%H%M%S` — for the filename
- `date --iso-8601=seconds` — for the report header

## Step 2 — Ensure the output directory exists

Run: `mkdir -p .project/tests`

## Step 3 — Run the tests

Run the test suite from the project root:

```
.venv/bin/python run_all.py 2>&1
```

Capture the full output including the exit code. To capture the exit code run:

```
.venv/bin/python run_all.py 2>&1; echo "EXIT:$?"
```

## Step 4 — Parse the output

From the captured output, extract:

1. **Overall result** — PASS if exit code is 0, FAIL otherwise.
2. **Total counts** — the `TOTAL: N/M passed` line at the end.
3. **Per-suite results** — for each `=== <suite-label>` block, the `Results: N/M passed` line and the list of `[PASS]` / `[FAIL]` lines with their test case descriptions.
4. **Failure details** — for any `[FAIL]` line, also capture the indented lines beneath it (Exception, Expected, Actual).

## Step 5 — Write the summary file

Write the report to `.project/tests/runs/<YYYYMMDDHHMMSS>_test_summary.md` using this exact structure:

```markdown
# Test Summary
Generated: <ISO datetime>
Result: **PASS** | **FAIL**

## Totals
- Total tests: M
- Passed: N
- Failed: M - N

## Suites

### <suite-label>
- Result: PASS | FAIL
- Passed: N / M

| Status | Test Case |
|--------|-----------|
| ✅ PASS | <test case description> |
| ❌ FAIL | <test case description> |

[repeat for each suite]

## Failures

> _No failures._

OR, if there are failures:

### <suite-label> — <test case description>
- **Expected:** `<expected value or exception>`
- **Actual:** `<actual value or error message>`

[repeat for each failure]
```

Rules:
- If there are no failures, write `> _No failures._` under `## Failures`.
- If the test runner itself failed to launch (import error, syntax error, etc.), set Result to **FAIL**, set all counts to 0, and include the raw error output under a `## Runner Error` heading instead of the Suites and Failures sections.
- Use `✅` for PASS and `❌` for FAIL in the table.
- Keep the suite label exactly as printed by the runner (e.g. `scratch/math.py`).

## Step 6 — Report to the user

Output the path to the written file and a one-sentence plain-English verdict (e.g. "All 45 tests passed." or "3 of 45 tests failed — see `.project/tests/<timestamp>_test_summary.md` for details.").
