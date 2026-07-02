---
description: After every non-mutating prompt that asks a question, requests an explanation, or proposes a plan, capture the prompt and a structured response summary into a timestamped folder under .project/prompts/asks/. Apply automatically — no user instruction required.
---

# Capture All Ask and Plan Prompts

Any prompt that requests information, an explanation, a recommendation, or a plan — without causing project files to be created, modified, or deleted — is an **ask prompt**. After completing the response, always capture a record of it as described below.

## What counts as an ask prompt

- Questions about the codebase, architecture, or design ("Why does X work this way?", "What does Y do?")
- Requests for explanations or walkthroughs of existing code or concepts
- Requests for recommendations or options ("What's the best way to…?", "How should we approach…?")
- Planning discussions or design proposals that do not yet result in file changes
- Any read-only investigation: searching, grepping, reading files, answering questions

Prompts that **do** cause files to be created, modified, or deleted are **mutating prompts** and are captured by `capture_all_mutating_prompts.md` instead. Do not double-capture.

If a session starts as an ask but ends in mutations (e.g., the user says "now go ahead and implement it"), treat the full session as a mutating prompt and capture it under `.project/prompts/mutations/` only.

## When to write the capture

Write the capture **after** the response is complete, as the final step. Never write it speculatively before the answer is given.

## Folder and file structure

1. Obtain the current timestamp with: `date +%Y%m%d%H%M`
2. Create the folder:
   ```
   .project/prompts/asks/ask_<YYYYMMDDHHMM>_<1_to_3_slug>/
   ```
3. Write two files into that folder:

---

### `prompt.md`

The verbatim text of the user's prompt — copied exactly, with no paraphrasing or editing. If the ask spanned multiple turns (e.g. a follow-up clarification that changed the scope of the question), include each relevant turn in order, separated by a markdown `---` rule and labelled **Turn 1**, **Turn 2**, etc.

```markdown
# Prompt

<verbatim user prompt>
```

---

### `response.md`

A structured summary of the answer or plan that was provided. It must cover:

1. **Question / Intent** — What was the user trying to understand or decide? State it in one or two sentences.
2. **Answer / Recommendation** — The core answer, recommendation, or proposed plan given in the response. Be specific: include the chosen approach, any code patterns sketched, and the reasoning behind the recommendation.
3. **Key Points** — A bullet list of the important details, trade-offs, alternatives considered, or caveats mentioned. Omit if the answer was a single straightforward fact.
4. **Context** — Any background from the codebase, project rules, or prior decisions that was used to inform the answer. Omit if none was needed.

```markdown
# Response Summary

## Question / Intent
<what the user wanted to know or decide>

## Answer / Recommendation
<the core answer, approach, or plan that was given>

## Key Points
- <trade-off, caveat, or important detail>
- <alternative considered and why it was not recommended>

## Context
<relevant background, constraints, or prior decisions that shaped the answer>
```

---

## Rules for writing the capture

- Use the Write tool to create both files.
- Keep `prompt.md` verbatim — never sanitise or shorten it.
- Write `response.md` for a future developer who has no conversation context and needs to understand what was asked and what was decided, without re-reading the full exchange.
- Do not mention the existence of the capture folder in your response to the user unless they ask; it is infrastructure, not conversation.
- If the ask spanned multiple back-and-forth turns before the final answer was settled, write a single capture at the end covering the full session, not one per turn.
- Omit the **Key Points** or **Context** sections of `response.md` if they add no information (e.g., a one-line factual answer needs neither).
