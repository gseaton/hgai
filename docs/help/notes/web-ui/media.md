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
- **Preview** a file from its preview button on the Media screen or in an attachment list. Images, audio and video play in the preview dialog. **YAML files** (`application/yaml`, `application/x-yaml`, `text/yaml`, or any `.yml` / `.yaml` file whose stored type is generic) open in a wide dialog with syntax highlighting and line numbers — handy for checking a hypergraph export (`*.export.yml`) or a SHQL query file before importing or running it. Very large YAML files preview only their first few thousand lines (a notice says so); use **Download** for the whole file. Other file types show metadata only.

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
