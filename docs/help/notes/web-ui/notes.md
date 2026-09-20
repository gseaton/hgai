---
id: help-notes
label: Notes
name: notes
description: Markdown notes with tags, tag-based virtual folders, sharing, media embeds and internal links.
tags: ["//Using the Web UI", notes, markdown, folders, sharing]
status: active
---

# Notes

**Notes** are personal Markdown documents — independent of any hypergraph. Each has a **label** (title), an optional **name** (short subtitle), **tags**, a **status**, and Markdown **text**. Use them for research notes, meeting minutes, runbooks — or, because the AI Chat can export to them, saved answers.

## Virtual folders from tags

There is no separate folder field. A tag that starts with `//` and looks like a path becomes a folder in the sidebar tree:

- `//projects/quill` places the note two levels deep: **projects › quill**.
- Intermediate folders are created automatically.
- A note with no `//` tags still appears in the main table, just not in the tree.
- Folder names merge case-insensitively.

The sidebar always shows all of your visible notes, independent of the table's search and paging. The **Help** tab uses exactly the same convention ([Adding your own help topics](help:help-authoring-help)).

## Modes

Opening a note starts in **Browse** (read-only, rendered). Switch to **Edit** for the raw Markdown with all fields, or **Preview** to see the rendered output while keeping the other fields visible.

## Markdown extras

| Syntax | Result |
|---|---|
| `[text](note:<id or label>)` | Link to another note (a label is used only if it is unique) |
| `![alt](media:<media-id>)` | Embed an uploaded image from [Media](help:help-media) |

## Sharing

The owner can share a note with other accounts as a **viewer** (read) or **editor** (read and change). Owners and administrators can share and delete. Notes visible to you — yours plus those shared with you — appear in your list.

## Search and API

Search the list and filter by tag. Via REST: `GET/POST /api/v1/notes`, `GET/PUT/DELETE /api/v1/notes/{id}`, `POST /api/v1/notes/{id}/share` and `DELETE /api/v1/notes/{id}/share/{username}` ([REST API](help:help-rest-api)).

## Notes and Help

A note tagged **`system:help`** also shows up in the [Help tab](help:help-authoring-help) for everyone who can view it.
