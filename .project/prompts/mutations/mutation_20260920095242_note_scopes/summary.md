# Mutation Summary

## Intent
Add five access scopes to Notes — private, protected (view only), protected-edit (view and edit), public (view only), public-edit (view and edit) — so notes can be reached across accounts.

## Context
- Notes already had an owner plus a per-account share list (viewer/editor). Admin bypass is applied in the API layer, and only the owner/admin can share or delete. Existing notes had no scope field, and their behavior (owner + share list) had to be preserved.
- The scope names leave some semantics open: the interpretation used is that *protected* means "the accounts I list", *public* means "every signed-in account on this server" (not anonymous visitors), and the `-edit` suffix widens view to view-and-edit for that audience.

## What Changed and Why
- **Model/access rule** — a single function, `note_access`, gives the owner/editor/viewer/none answer from the scope and share list. Scope sets the baseline audience and a per-account share-list grant can only raise it (e.g. an `editor` grant on a `protected` note still lets that account edit). `private` makes the share list inactive without discarding it.
- **Storage** — the list query was widened to the same rule (owner OR public scope OR on the share list and not private). A missing scope counts as `protected`, so existing notes keep working with no migration. A parity test evaluates the query against `note_access` for every combination to keep the two from drifting.
- **API** — responses carry the caller's effective access (`my_access`) so the UI never re-implements the rules; a dedicated `PUT /notes/{id}/scope` (owner/admin only, own audit entry) mirrors how sharing is kept separate from content edits; the list gains `scope` and `owner` filters.
- **UI** — Scope column and filters (scope, only-my-notes), a Scope select in the note editor (owner-only, with plain-language help), an owner/scope line in Browse, badges, and view-only indication. A note the user can only view still opens as view-only.
- **Help/docs** — the Notes help topic, FAQ, glossary, README and API reference describe scopes; a public `system:help` note is now a help topic for every account (verified).

## Key Decisions
- **New notes default to `private`; the model default stays `protected`** so stored pre-scope notes read exactly as they behaved. Existing chat-exported and hand-made notes are unaffected.
- **Sharing a private note promotes it to `protected`** instead of silently doing nothing.
- **Editors cannot change scope or the share list** even on `public-edit` notes; only owner/admin can, and the change is a separately audited event.
- **Global account roles are not consulted** (as before for Notes): a `readonly`-role account can edit a `public-edit` note, just as it could already be granted editor on a note.
- **Verification**: 256 tests pass (2 pre-existing unrelated mesh-ping failures). Live with real accounts: default private; stranger 403 and hidden from lists; share promotes to protected; viewer can't edit; protected-edit lets listed accounts edit; public/public-edit for a stranger (view / edit); editors can't rescope, share or delete; filters; admin `my_access`; private hides again even from former share-list members; audit trail entries; public help notes; and a real pre-scope Mongo document behaves as protected. UI checked via DOM in the browser (columns, filters, owner-only scope select for owner/admin vs simulated editor/viewer, saving scope and creating with a scope), no console errors. Test notes/accounts removed.
