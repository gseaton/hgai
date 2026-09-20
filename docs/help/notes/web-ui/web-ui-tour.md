---
id: help-web-ui
label: Web UI tour
name: web-ui
description: A tour of every screen in the HypergraphAI Web UI and what each one is for.
tags: ["//Using the Web UI", ui, screens, navigation, overview]
status: active
---

# Web UI tour

The Web UI is served at `/ui/` (for example `http://localhost:8357/ui/`). Sign in with your account; the left sidebar lists the screens you can use. Screens marked *(admin)* only appear for administrators.

| Screen | What it's for | Learn more |
|---|---|---|
| **Dashboard** | Overview of your hypergraphs with counts and activity | — |
| **Hypergraphs** | Create, edit, inspect, **export** to a file and **import** from one | [Hypergraphs](help:help-hypergraphs), [Export and import](help:help-export-import) |
| **Hypernodes** | Full create/read/update/delete of nodes, with attribute editing, filtering, sorting and media | [Hypernodes](help:help-hypernodes) |
| **Hyperedges** | Full CRUD of edges, with member management | [Hyperedges](help:help-hyperedges) |
| **Media** | Upload, browse and manage files that can be attached to nodes, edges and notes | [Media](help:help-media) |
| **Notes** | Personal and shared Markdown documents, organized in tag-based folders | [Notes](help:help-notes) |
| **Visualize** | Interactive 3D view of a hypergraph | [Visualize](help:help-visualize) |
| **Query (SHQL)** | Editor for SHQL queries, with examples, history and results | [Query screen](help:help-query-screen) |
| **Parameterized Queries** | Reusable SHQL templates with typed parameters | [Parameterized Queries](help:help-parameterized-queries) |
| **Project Inference** | Materialize inferred facts into a hypergraph | [Project Inference](help:help-project-inference) |
| **Help** | This documentation | [Adding your own help topics](help:help-authoring-help) |
| **AI Agent** *(admin)* | Configure AI vendors, models and keys for the chat panel | [AI Chat](help:help-ai-chat) |
| **Spaces** *(admin)* | Manage multi-tenant spaces and their members | [Spaces](help:help-spaces) |
| **Accounts** *(admin)* | Manage users, roles, permissions and space memberships | [Accounts and roles](help:help-accounts-roles) |
| **Meshes** *(admin)* | Register servers and federate queries | [Meshes](help:help-meshes) |
| **System** *(admin)* | Server information, the query cache, and an API explorer | [Configuration](help:help-configuration) |

## Always available

- The **AI Chat** button in the top bar opens a collapsible chat panel on the right ([AI Chat](help:help-ai-chat)). Drag its left edge to resize it.
- The folder sidebar in **Notes** and **Help** can be resized by dragging the handle between it and the main panel.
- Table columns marked sortable can be sorted by clicking a header; hold **Shift** to add secondary sort keys.
