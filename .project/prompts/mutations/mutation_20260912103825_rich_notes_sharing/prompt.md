# Prompt

**Turn 1:**
Please add rich note / document support per account similar to the features in the note taking project '/home/gseaton/projects/quill' with the ability to scope sharing (editing / viewing) across accounts. Please ask 3 or more questions to clarify this rich note capability implementation.

**Turn 2 (clarifying answers, via AskUserQuestion):**
- Architecture: "New first-class resource (Recommended)" — its own MongoDB collection + router, independent of the hypergraph model, same tier as Accounts/Spaces/Media.
- Feature scope for v1: "Markdown editor + live preview (Recommended), Tags + tag-based search/filtering, Media embedding via existing Media subsystem, Linking between notes"
- Sharing model: "Per-note ACL (Recommended)" — {username, role: viewer|editor} grants, independent of Spaces, private to the owner by default.
- UI depth: "Integrated into existing left-nav (Recommended)" — a "Notes" section (list + editor screens) added alongside Hypergraphs/Hypernodes/etc.
