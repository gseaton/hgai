# Mutation Summary

## Intent
Add a **Help** tab to the Web UI that behaves like Notes (tag-based virtual folders, search, tag filtering) but lists only help content: markdown topics from `docs/help/notes/**` (frontmatter fields `id`, `label`, `name`, `description`, `tags`), media from `docs/help/media/**`, and any Note tagged `system:help`. Help lands on `docs/help/notes/home.md`, the AI Agent chat can use the topics to answer questions about HypergraphAI, and the README-derived help content (plus a rich home topic) had to be generated.

## Context
- The Notes screen already had a `//Folder/Sub` tag convention, folder tree, sidebar resize, and `media:`/`note:` Markdown embeds; the pluggable-module pattern, `PaginatedResponse`, `PAGINATION_LOADERS` and `showScreen` maps were reused.
- The agent chat (Agno) already received MCP tools and a web toolkit per turn.
- The user wrote `docs/helps/notes` once and `docs/help/notes` everywhere else; the singular `docs/help/notes` was used consistently.
- README was the content source; it contains a few stale claims (e.g. "14 tools", `shell.sh`) that were deliberately *not* copied (the real shell script is `hgsh.sh`, and tool counts were not stated).

## What Changed and Why
- **Backend (`hgai/core/help.py`, router)** — File topics are parsed from frontmatter (with safe fallbacks for id/label), cached by mtime so edits show without restart, and merged with `system:help` Notes that the *calling account* can view (owner/ACL). Search requires every word to match; results rank by relevance when no explicit sort is given. Media is served through an authenticated route that blocks traversal, hidden files and symlink escapes and adds a CSP sandbox header.
- **Agent access (`help_toolkit.py`, `engine.py`)** — `help_search` / `help_get` run in-process against the same core, and system instructions tell the agent to consult them (and cite topic ids) for HypergraphAI questions.
- **UI** — A new `screen-help` reuses the Notes layout. Entering Help always opens Home; the tree, search box, tag filter, "All Topics" list, back/home buttons and clickable tag badges cover navigation. Markdown supports `help:` links and `help-media:` images via placeholder substitution around marked+DOMPurify, exactly like the Notes renderer.
- **Content** — 39 topics in 8 virtual folders (Getting Started, Concepts, Using the Web UI, Query Language (SHQL), Inferencing, Integration, Administration, Reference), each with id (`help-…`), label, name, description, tags, status, plus a component-layers SVG. An integrity test guards that every topic has full frontmatter and a folder tag, ids are unique, and all `help:`/`help-media:` links resolve.
- **Ops/docs** — Dockerfile copies `docs/help`; README and API reference document the feature and `HGAI_HELP_DIR`.

## Key Decisions
- **In-process toolkit rather than MCP tools**: MCP tools have no per-account context, and note-backed topics must respect Note visibility.
- **File topic wins on id collision**; draft/archived topics are hidden; duplicate ids are skipped with a warning.
- **`//Other` bucket** in the tree for topics with no folder tag (typically `system:help` Notes), so they stay discoverable, unlike ordinary Notes.
- **Tree shows label, not name**: help `name` values are slugs; the list view keeps `name` as a small secondary line.
- **Relevance ranking added after live testing** showed that "point in time" returned the dedicated topic buried among 15 matches.
- **Code-fenced/inline-code link examples are excluded** from the link-integrity test so documentation about link syntax doesn't count as a broken link.
- **Verification**: 30 help tests pass; full suite 215 passed, 2 pre-existing unrelated failures (`tests/test_mesh.py` ping tests). Live-verified via curl (list/search/tag/media/traversal/401) and in the browser (Home default, tree, links, back, search, tag click, note-backed topic, resize handle, zero console errors); a `system:help` note was confirmed hidden from a non-authorized account until shared. Test note and test account were deleted afterward.
