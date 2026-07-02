Scan all Python source files in this project for code smells and produce a structured report with candidate fixes. Follow these steps exactly:

## Step 1 — Discover Python files

Use the Glob tool to find all `**/*.py` files in the project, excluding virtual environments (`venv/`, `.venv/`, `env/`, `site-packages/`).

## Step 2 — Analyse each file

Read each Python file and check for the following code smell categories:

### Style & Readability
- Functions or methods longer than ~40 lines (too long, hard to reason about)
- Deep nesting (more than 3 levels of indentation)
- Magic numbers/strings (unexplained literals that should be named constants)
- Overly abbreviated or cryptic variable/function names
- Dead code (unreachable statements, commented-out blocks that should be removed)

### Design & Structure
- God classes/functions (doing too many unrelated things)
- Feature envy (a function that uses another module's data more than its own)
- Data clumps (groups of variables that always appear together and should be a dataclass/namedtuple)
- Long parameter lists (more than ~5 parameters — consider a config object)
- Duplicate code blocks (copy-pasted logic that should be extracted)

### Error Handling
- Bare `except:` or `except Exception:` clauses that swallow errors silently
- Missing error handling around I/O, network calls, or external processes
- Using exceptions for normal control flow

### Performance
- Repeated attribute lookups inside loops (e.g. `obj.attr` called on every iteration)
- List concatenation inside a loop (`result += [item]` instead of `append`)
- Unnecessary list comprehensions where a generator expression would do

### Pythonic Patterns
- Using `range(len(x))` instead of `enumerate(x)`
- Manual iteration where `zip()`, `map()`, or comprehensions are clearer
- Mutable default arguments in function signatures
- Not using context managers (`with`) for resources

## Step 3 — Write the report

Determine the current timestamp in `YYYYMMDDHHMMSS` format using a Bash command: `date +%Y%m%d%H%M%S`

Write the report to `.project/code/smells/smells_<timestamp>.md` using the Write tool with this structure:

```
# Code Smell Report
Generated: <ISO datetime>

## Summary
- Files scanned: N
- Total smells found: N
- Files with smells: N

## Findings

### <relative/path/to/file.py>

#### <Smell Category> — <Short smell name> (line N or lines N–M)
**Smell:** <one-sentence description of the problem>
**Why it matters:** <one-sentence rationale>
**Candidate fix:**
\`\`\`python
# before
<problematic snippet>

# after
<improved snippet>
\`\`\`

[repeat for each smell in this file]

[repeat ### block for each file that has smells]

## Files with No Smells
- <list of clean files>
```

Only include findings that are genuine issues. Do not manufacture smells. If a file is clean, list it in "Files with No Smells". Keep candidate fix snippets short and focused — show only the relevant lines, not the whole function.

After writing the file, output the path to the report and a one-paragraph plain-English summary of the most important findings.