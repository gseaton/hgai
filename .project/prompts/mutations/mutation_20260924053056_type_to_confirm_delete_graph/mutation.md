# Mutation Log

## Modified
- **ui/index.html** — Added a hidden-by-default "type to confirm" input group (`#modal-confirm-match-group`, a label and `#modal-confirm-match-input`) inside the shared `#modal-confirm` delete-confirmation modal's body, alongside the existing message text.
- **ui/js/app.js** —
  - `State` gained `confirmRequireText` (defaults `null`).
  - `confirmDelete(msg, cb, requireText = null)` gained an optional third parameter: when set, it shows the match input (with a label naming the exact required text), disables the Delete button, and resets the input; when omitted (all 13 pre-existing call sites), behavior is unchanged.
  - New `input` listener on `#modal-confirm-match-input` enables/disables `#btn-confirm-delete` based on an exact string match against `State.confirmRequireText`.
  - `#btn-confirm-delete`'s click handler gained a defensive re-check of the typed value before proceeding (in addition to the button's own disabled state).
  - New `hidden.bs.modal` listener on `#modal-confirm` resets `confirmCallback`, `confirmRequireText`, the match input, and the button's disabled state on any close (Delete, Cancel, or the X button).
  - `window.deleteGraph` now passes the hypergraph's `id` as `confirmDelete`'s third argument, and the confirmation message states the deletion cannot be undone.

## Verification
- `node -c ui/js/app.js` — syntax check passed.
- Confirmed via `curl` against a disposable server instance (port 8369, since cleaned up) that the edited `index.html`/`app.js` are served byte-for-byte as written — no build step or caching involved.
- Interactive in-browser verification (Claude in Chrome) was attempted but the browser extension could not reach the disposable server (`ERR_CONNECTION_REFUSED`) despite the server's own logs confirming successful requests from other clients on the same port — an environment network-isolation issue between this job's shell and the browser extension, not a defect in the change. Correctness was instead verified by a full manual trace of the logic (all 13 unaffected call sites, the hypergraph-delete call site, Cancel/X-close cleanup, and the Enter-key-in-a-formless-input non-issue) against the confirmed-served source.
