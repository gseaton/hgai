# Response Summary

## Question / Intent
The user asked where the account share list appears on the Note editor, and (in the second, unfinished sentence) what should happen if it is not a field on the editor. The message ended mid-sentence ("If the account share list field is NOT currently on the Notes editor."), so the intended follow-up action was unclear.

## Answer / Recommendation
There is **no share-list field in the Note editor form**. The share list lives in a separate **Share dialog** (`#modal-note-share`, `ui/index.html`) opened by the **Share** button (people icon, `#btn-note-share-open`) in the Note modal's header bar, just left of the close (×) button.

- The button is only shown for an existing note, and only to its owner or an admin (`noteIsOwner`, `ui/js/app.js`); it is hidden for new notes and for editors/viewers.
- The dialog shows the owner, the note's current scope and hint, the current share list (username, role badge, revoke ×), and an add row (username box, viewer/editor select, Grant).
- Changes in the dialog are applied immediately via the share/unshare endpoints — they are not part of the editor's Save.
- Related places: the **Scope** select is in the editor's Classification section (Edit/Preview modes, next to Status); the Notes list has a **Shared With** column and a per-row share button for owners/admins.

An offer was made to add the share list as an editable field inside the editor (in the Classification section next to Scope), and the user was asked to confirm, since the request was cut off.

## Context
Share list and scope behavior: `hgai/core/notes.py` (`note_access`, `share_note`), `hgai/api/routers/notes.py`; UI in `ui/js/app.js` (`openNoteShareModal`, `loadNoteShares`).
