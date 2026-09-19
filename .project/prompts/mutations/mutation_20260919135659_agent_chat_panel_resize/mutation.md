# Mutation Log

## Modified
- **ui/index.html** — Wrapped the AI Agent Chat panel in a new `#agent-chat-panel-wrap` (now the element the open/closed `.d-none` is applied to, so the resize handle disappears along with the panel), and added a draggable `#agent-chat-resize-handle` (`role="separator" aria-orientation="vertical" tabindex="0"`) as its first child, directly left of `#agent-chat-panel`.
- **ui/css/hgai.css** — `#agent-chat-panel`'s width is now driven by a new `--agent-chat-panel-width` CSS variable (default `380px`, via `flex: 0 0 var(...)`) instead of a fixed `380px`, with a `min-width: 300px` floor. Added `.agent-chat-resize-handle` styling (6px wide, `cursor: col-resize`, highlighted on hover/drag) and `body.agent-chat-panel-resizing` (global resize cursor + `user-select: none` while dragging), both mirroring the existing `.notes-sidebar-resize-handle`/`body.notes-sidebar-resizing` rules. The mobile (`max-width: 991.98px`) override now also hides the handle, since the panel goes full-width there.
- **ui/js/app.js** — Added `agentChatApplyPanelWidth`, `agentChatRestorePanelWidth` (called at module load, restores from `localStorage['hgai_agent_chat_panel_width']`, clamped to `[300, 900]`), and `agentChatInitPanelResize` (pointer-capture drag-to-resize, plus `ArrowLeft`/`ArrowRight` keyboard resize on the focused handle) — called from `initAgentChatPanel()`. `setAgentChatPanelOpen()` now toggles `#agent-chat-panel-wrap`'s `.d-none` instead of `#agent-chat-panel`'s own.

No files were created or deleted.
