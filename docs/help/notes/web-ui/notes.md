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
| ` ```yaml ` … ` ``` ` (also `yml`, `shql`) | Fenced code block with **YAML syntax highlighting** — keys, strings, numbers, booleans, comments, block scalars, flow collections, anchors/tags, and SHQL `?variables` |

## Scope — who can reach a note

Every note has a **scope**, set in the note's *Scope* field. New notes start **private**.

| Scope | Who can view | Who can edit |
|---|---|---|
| **private** | only the owner | only the owner |
| **protected** | accounts on the note's share list | only share-list accounts individually granted *editor* |
| **protected-edit** | accounts on the share list | accounts on the share list |
| **public** | every account on this server | the owner, plus share-list accounts granted *editor* |
| **public-edit** | every account on this server | every account on this server |

"Every account" means every signed-in account on this HypergraphAI server — public notes are not visible to anonymous visitors. Public notes from other accounts appear in your Notes list (see the **Owner** and **Scope** columns), and you can filter the list by scope and by *Only my notes*. A note you can only view opens as "(view only)".

Only the **owner** (or an administrator) can change a note's scope, manage its share list, or delete it — an account with *edit* access can change the content but not who sees it. Changes to scope are recorded in the note's history.

## Sharing

For **protected** notes, the owner adds accounts to the share list from the note's **Share** button, each as a **viewer** (read) or **editor** (read and change). With **protected-edit** every listed account can edit. The share list is inactive while a note is **private**: sharing a private note with someone makes it **protected** automatically. Setting a note back to private hides it from everyone else without discarding the share list.

## Search and API

Search the list and filter by tag. Via REST: `GET/POST /api/v1/notes`, `GET/PUT/DELETE /api/v1/notes/{id}`, `PUT /api/v1/notes/{id}/scope`, `POST /api/v1/notes/{id}/share` and `DELETE /api/v1/notes/{id}/share/{username}` ([REST API](help:help-rest-api)).

## Notes and Help

A note tagged **`system:help`** also shows up in the [Help tab](help:help-authoring-help) for everyone who can view it — so a **public** help note is shown to every account.
