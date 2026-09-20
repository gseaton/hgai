---
id: help-media
label: Media
name: media
description: Upload files and attach them to hypernodes, hyperedges and notes; embed images in notes.
tags: ["//Using the Web UI", media, files, upload, images]
status: active
---

# Media

The **Media** screen manages uploaded files — images, audio, video, documents. Media items are stored once and can be **attached** to hypernodes, hyperedges and notes, where a *default media* item can be chosen to be shown as a thumbnail in the node and edge lists (and in [Visualize](help:help-visualize) when the Media option is on).

## Using media

- **Upload** from the Media screen, or directly from the attachment widget in a node, edge or note editor (which also lets you pick an existing item).
- **Embed** an image in a [note](help:help-notes) with `![alt](media:<media-id>)`.
- **Search, filter and sort** the list like other tables.

## API and MCP

```
GET    /api/v1/media           # list
POST   /api/v1/media           # upload a file
GET    /api/v1/media/{id}      # download
PUT    /api/v1/media/{id}      # update metadata
DELETE /api/v1/media/{id}      # delete
```

MCP tools: `hgai_media_upload`, `hgai_media_download`, `hgai_media_delete` ([MCP tools](help:help-mcp-tools)).

Like every endpoint, downloads require authentication — the UI fetches images with your session token.
