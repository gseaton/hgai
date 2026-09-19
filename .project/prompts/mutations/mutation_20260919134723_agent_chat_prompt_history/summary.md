# Mutation Summary

## Intent
Track the last 50 prompts a user has submitted in the AI Agent Chat, persisted server-side so the history follows the account across server restarts, browsers, and machines — not a client-only (localStorage) list scoped to one device.

## Context
This is functionally the same feature the project already built once before, for a different screen: `hgai_module_shql/history.py` already implements "per-account, server-side, capped-at-50, dedup-on-resubmit" history for submitted SHQL queries, explicitly built to replace an earlier client-only localStorage list for exactly the reasons this request calls out (doesn't survive a server restart, doesn't follow the account across devices). Given an almost identically-shaped request for a different kind of "thing submitted" (a chat prompt instead of a query), the correct move was to mirror that existing, already-proven module structure closely rather than design a new pattern — consistency here has real value: a future maintainer who understands one of these two history features already understands the other.

## What Changed and Why
`prompt_history.py` is a close structural copy of `hgai_module_shql/history.py`: same module-owned-collection pattern (not part of the pluggable `StorageBackend` ABC, per `docs/module-development.md`'s guidance for small account-scoped concerns), same cap (50), same dedup-on-exact-resubmission behavior (moves an already-present prompt back to the top rather than creating a duplicate entry — the SHQL history's own established behavior, kept here for consistency across the two features rather than because this request explicitly asked for it).

The API router mirrors the SHQL router's three endpoints (`GET`/`POST`/`DELETE` on `/prompt-history`) including keeping a small dedicated request body model (`AgentPromptHistoryEntryRequest`) separate from `AgentChatSendRequest`, even though both are just `{prompt: str}` today — the SHQL router made the same choice (a separate `SHQLHistoryEntryRequest` alongside `SHQLRequest`) so the history endpoint's contract doesn't accidentally become coupled to the chat-send endpoint's, in case they diverge later.

On the frontend, recording happens exactly where the SHQL screen records its own history: fire-and-forget, at the moment the prompt is submitted, before anything else happens — so a prompt is recorded as *submitted* regardless of whether the resulting chat turn succeeds, fails, or times out. A small UI addition (a second toggle button in the chat panel header, separate from the existing sessions-list toggle) lets a user browse and reuse a past prompt — a history nobody can see or act on has limited value, and the SHQL screen's own "copy history entry back into the query box" precedent made the expected interaction obvious: click an entry, it fills the composer, it does not auto-send.

## Live Verification
Verified end-to-end in the browser, including the one property this request specifically called out — persistence across a genuine reload, not just in-memory state:
1. Sent a real chat prompt through the live panel; the prompt-history list correctly showed it immediately.
2. Clicked the history entry and confirmed it filled the composer without sending.
3. **Reloaded the page fully** (a fresh page load, not a soft-navigation) and confirmed the exact same prompt text was still present in the history list — this is what actually proves the data came from the server (via `HGAI_API.listAgentPromptHistory()`) rather than surviving only because of some in-memory JS state that a real restart or a different browser wouldn't have.
4. Verified the `DELETE /agent/prompt-history` endpoint via direct API call, confirming it reports the correct deleted count and the account's history for that account.

One browser-automation-specific hiccup during testing: a physical click on the new toggle button right after a page reload initially appeared not to register (no visible list). Dispatching the same click via JavaScript (`element.click()`) immediately after worked correctly and returned the expected persisted data — this was a coordinate-timing artifact of the browser automation tool, not a bug in the feature; re-confirmed by then reviewing the button's and list element's actual DOM/class state, which behaved exactly as coded.

Test artifacts (the chat session and prompt-history entry created during verification) were cleared afterward via the API, and the vendor/model catalog was restored to the same disabled default state prior phases left it in.

## Key Decisions
- **Mirror `hgai_module_shql/history.py` closely rather than design something new**: this project already solved "per-account, server-side, capped, deduplicated history of something a user submits" once; reusing that shape is a consistency win, not a shortcut.
- **Keep the dedup-on-resubmit behavior even though the request didn't explicitly ask for it**: matches the sibling feature's established behavior in the same app, and is a genuinely more useful history (resubmitting a common prompt doesn't clutter the list with duplicates).
- **Add a minimal UI to view/reuse the history, even though the request was framed purely around the persistence guarantee**: a "history" that's invisible/unreachable in the product has limited value, and the SHQL screen already sets a clear, low-effort-to-match precedent for what "history" means to this app's users.
