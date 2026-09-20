# Mutation Summary

## Intent
Make sure Notes that an account can at least view (by scope and share list) and that carry the `system:help` tag appear in that account's Help.

## Context
Help's note-backed topics are built with the same visibility logic as the Notes list (`list_notes_visible_to`) and, for a single topic, `can_view_note`. When Note scopes were added, both of those were extended to honor scope, so Help picked the behavior up automatically — no production code change was needed for this request.

## What Changed and Why
- Verified live with an owner, a share-list account and an unrelated account across all five scopes (plus a draft and an untagged public note): Help listed and served exactly the notes each account may view; revoking a share or making a note private removed it from Help immediately.
- Added regression tests pinning this rule (scope × account matrix; tag and status conditions) so a future change to note visibility cannot silently change Help.
- Updated the authoring-help topic to spell out the rule for users.

## Key Decisions
- Kept the existing rule that only `active` notes are shown in Help (drafts/archived hidden), consistent with file-based help topics; this is documented.
- No code change: duplicating visibility logic in Help would risk drift, so Help continues to delegate to the Notes visibility functions.
- Test data (7 notes, 3 accounts) was removed after verification; suite: 262 passed, 2 pre-existing unrelated mesh-ping failures.
