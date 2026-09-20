# Mutation Log

## Modified
- **tests/test_help.py** — Added a parametrized test that a `system:help` Note is a help topic exactly when its scope lets the account view it (owner / share-list member / other account across all five scopes), and a test that visible notes lacking the `system:help` tag or not `active` are excluded.
- **docs/help/notes/web-ui/authoring-help.md** — Stated explicitly that every active `system:help` Note an account can at least view (owner, share list, or scope-based) is included in that account's Help, and that scope/share-list changes take effect immediately.
