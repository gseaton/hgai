---
id: help-authoring-help
label: Adding your own help topics
name: authoring-help
description: How Help topics are found — markdown files with front matter, system:help notes, virtual folders, links and media.
tags: ["//Using the Web UI", help, authoring, markdown, frontmatter, custom-topics]
status: active
---

# Adding your own help topics

The Help tab (and the [AI Chat agent](help:help-ai-chat)) draw on two sources.

## 1. Markdown files (built-in help)

Every `*.md` file under **`docs/help/notes/`** (searched recursively) is a topic. Media for topics lives under **`docs/help/media/`**. The help root defaults to `<project>/docs/help` and can be moved with the `HGAI_HELP_DIR` setting ([Configuration](help:help-configuration)). Edits are picked up without a restart.

Each file begins with YAML front matter:

```markdown
---
id: help-my-topic
label: My Topic
name: my-topic
description: One sentence shown in lists and search results.
tags: ["//Guides/Advanced", keyword, another-keyword]
status: active
---

# My Topic

Body text in Markdown…
```

| Field | Meaning |
|---|---|
| `id` | Unique topic id used in links (`help:<id>`). Give it the `help-` prefix. If missing, one is derived from the file path. |
| `label` | Title shown in the topic tree and at the top of the topic |
| `name` | Short handle; when set it is shown as the primary text in lists |
| `description` | Summary shown in lists, and searched |
| `tags` | Tags; any of the form `//Folder/Sub Folder` place the topic in the virtual folder tree |
| `status` | `active` (default) is shown; anything else (e.g. `draft`) hides the topic |

Files or folders whose names start with a dot are ignored, and if two files use the same id the first (by path) wins.

The landing page is `notes/home.md` (id `help-home`).

## 2. Notes tagged `system:help`

Any [Note](help:help-notes) carrying the tag **`system:help`** appears as a help topic for the accounts that can view that note (its owner and anyone it is shared with) — handy for team- or project-specific guidance without touching files. Give it a `//Folder/Path` tag to place it in a folder; otherwise it lands under **Other**. Only *active* notes are used. Use **Open Note** on the topic to edit it.

## Virtual folders

Exactly as for Notes, a tag such as `//Getting Started` or `//Query Language/Advanced` creates the folder path in the **Topics** tree on the left (intermediate folders are created automatically, names merge case-insensitively). A topic can appear in several folders by carrying several folder tags.

## Links and images

| Syntax | Result |
|---|---|
| `[text](help:help-other-topic)` | Link to another help topic by id |
| `![alt](help-media:diagrams/overview.png)` | Image from `docs/help/media/` (path relative to that folder) |
| `![alt](media:<media-id>)` | Image from the [Media](help:help-media) library (useful in note topics) |
| `[text](https://example.org)` | Ordinary external link (opens in a new tab) |

## Searching and filtering

The search box requires **every word** to appear somewhere in a topic's id, label, name, description, tags or text. The tag filter requires the topic to carry the tag. Click any tag badge to filter by it; **All Topics** lists everything.

## API

`GET /api/v1/help/topics`, `/help/topics/{id}`, `/help/home` and `/help/media/{path}` ([REST API](help:help-rest-api)).
