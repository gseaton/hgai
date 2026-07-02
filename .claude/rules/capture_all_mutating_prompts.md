---
description: After every prompt that mutates any project artifact, capture the prompt, a mutation log, and an intent summary into a timestamped folder under .project/prompts/mutations/. Apply automatically — no user instruction required.
---

# Capture All Mutating Prompts

Any prompt that causes one or more project artifacts to be created, modified, or deleted is a **mutating prompt**. After completing the work, always capture a record of it as described below.

## What counts as a mutation

- Creating, editing, renaming, or deleting any file in the project tree (excluding `.project/` itself — do not recurse)
- Installing or removing packages (requirements.txt, pyproject.toml, lock files, etc.)
- Modifying project configuration (`.claude/`, CI files, environment files, etc.)
- Running commands that produce side-effects visible outside the current shell session

Read-only work — explaining code, answering questions, searching, planning without writing — does **not** qualify and requires no capture.

## When to write the capture

Write the capture **after** all mutations are complete and verified, as the final step of your response. Never write it speculatively before the work is done.

## Folder and file structure

1. Obtain the current timestamp with: `date +%Y%m%d%H%M%S`
2. Create the folder
   ```
   .project/prompts/mutations/mutation_<YYYYMMDDHHMMSS>_<one_to_three_word_description_label_based_on_summary>/
   ```
3. Write three files into that folder:

---

### `prompt.md`

The verbatim text of the user's prompt that triggered the mutations — copied exactly, with no paraphrasing or editing. If the prompt was multi-turn (follow-up clarifications that changed scope), include each relevant turn in order, separated by a markdown `---` rule and labelled **Turn 1**, **Turn 2**, etc.

```markdown
# Prompt

<verbatim user prompt>
```

---

### `mutation.md`

A structured log of every artifact touched. One entry per artifact. Group entries under `## Created`, `## Modified`, and `## Deleted` headings (omit a heading if empty).

Each entry must include:
- The file path relative to the project root
- A one-to-three sentence summary of *what* changed (not *why* — that goes in `summary.md`)

```markdown
# Mutation Log

## Created
- **path/to/new_file.py** — Brief description of what this file contains and what was added.

## Modified
- **path/to/existing_file.py** — Brief description of which sections changed and what the change was.

## Deleted
- **path/to/removed_file.py** — Brief description of what this file contained and why it was removed.
```

---

### `summary.md`

A human-readable narrative for someone encountering this change cold. It must cover:

1. **Intent** — What was the user trying to achieve? What problem were they solving or what capability were they adding?
2. **Context** — Any background, constraints, or prior decisions that shaped the approach (e.g. project rules in effect, patterns already established in the codebase, trade-offs considered).
3. **What changed and why** — A cohesive explanation of the mutations: not just what files were touched but the reasoning that connected the prompt to each specific change.
4. **Reasoning on key decisions** — Where meaningful choices were made (approach A vs approach B, why a file was placed here rather than there), explain the reasoning.

```markdown
# Mutation Summary

## Intent
<what the user wanted to accomplish>

## Context
<relevant background, constraints, prior decisions>

## What Changed and Why
<cohesive narrative connecting the prompt to the specific mutations>

## Key Decisions
<reasoning behind non-obvious choices; omit if everything was straightforward>
```

---

## Rules for writing the capture

- Use the Write tool to create all three files.
- Keep `prompt.md` verbatim — never sanitise or shorten it.
- Keep `mutation.md` factual and terse — it is a log, not an essay.
- Write `summary.md` for a future developer who has no conversation context.
- Do not mention the existence of the capture folder in your response to the user unless they ask; it is infrastructure, not conversation.
- If a mutation session spans multiple back-and-forth turns (e.g. the user refines the request mid-way), write a single capture at the end covering the full session, not one per turn.
