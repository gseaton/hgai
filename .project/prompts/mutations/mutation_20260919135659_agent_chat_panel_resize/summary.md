# Mutation Summary

## Intent
Let a user drag the AI Agent Chat panel wider or narrower, since it currently has a fixed 380px width with no way to see more (or less) of a response/conversation alongside the main content.

## Context
The codebase already has a complete, working precedent for exactly this interaction: the Notes screen's folder sidebar is horizontally resizable by dragging a handle, with the chosen width persisted to `localStorage` (a deliberate, lasting preference, not per-tab transient state) and applied via a CSS custom property, plus keyboard support (arrow keys on a focused `role="separator"` handle) for accessibility. Rather than design a new resize mechanism, this was mirrored closely — the only real difference is geometric: the Notes sidebar is anchored to the *left* edge of its container (so dragging the handle rightward grows it), while the chat panel is anchored to the *right* edge of the screen (so growing it means dragging the handle *leftward* — the drag-delta-to-width formula's sign is inverted from the Notes version for exactly this reason, not because the underlying mechanism differs).

## What Changed and Why
The panel's fixed `width: 380px` became `flex: 0 0 var(--agent-chat-panel-width)`, matching how the Notes sidebar's own width is driven by `--notes-sidebar-width`. The resize handle needed a wrapping element (`#agent-chat-panel-wrap`) that the show/hide `.d-none` toggle moved onto, rather than staying on `#agent-chat-panel` itself — otherwise the handle would remain visible (and draggable) even while the chat panel was collapsed, which would be a confusing, do-nothing control to leave on-screen.

`agentChatInitPanelResize()` is a close structural copy of `notesInitSidebarResize()`: pointer-capture-based dragging (so the drag keeps tracking correctly even if the cursor moves off the thin 6px handle mid-drag), a `MIN`/`MAX` clamp (300–900px — wide enough to be a genuinely useful "read comfortably" width, capped so it can't swallow the entire main content area), and the same keyboard affordance (arrow keys move the boundary in 20px steps) for anyone who can't or doesn't want to drag with a mouse.

## Live Verification
Verified in the browser across every path the feature actually has:
1. Mouse drag: dragged the handle and confirmed the panel visibly widened (380px → 645px), with the CSS variable and `localStorage` both updated to match.
2. Persistence: reloaded the page fully and confirmed the panel restored to the exact previously-dragged width (645px) and its open/closed state, proving the preference survives a real reload rather than only living in JS memory.
3. Both clamp boundaries: dispatched a large-delta drag in each direction directly via `PointerEvent`s (more precise than fighting pixel-perfect targeting on a 6px handle through screenshot-coordinate scaling) and confirmed the width correctly clamped at exactly 900px and exactly 300px, never exceeding either bound.
4. Keyboard accessibility: focused the handle, dispatched `ArrowLeft`/`ArrowRight` `KeyboardEvent`s, and confirmed the width grew/shrank in the expected direction and steps, correctly clamping at the same 300px floor when shrinking further than the limit allows.
5. Checked the browser console throughout — zero errors.

Test-induced state (the resized width, the panel's open/closed preference, and a few leftover chat sessions/prompt-history entries from this and the prior conversation turn's testing) was cleared from `localStorage` and via the API afterward.

## Key Decisions
- **Mirror the Notes sidebar's resize mechanism exactly, inverting only the sign of the drag-to-width formula**: this project already solved "draggable, persisted, keyboard-accessible panel resize" once; a second, differently-built implementation for the same interaction would be a pure consistency cost with no offsetting benefit.
- **Move the panel's open/closed `.d-none` onto a new wrapper rather than adding a second class to `#agent-chat-panel`**: keeps the resize handle's visibility tied to the panel's visibility with a single toggle, instead of needing to remember to hide two separate elements every time the panel opens or closes.
