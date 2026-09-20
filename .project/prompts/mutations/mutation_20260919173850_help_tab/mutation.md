# Mutation Log

## Created
- **hgai/core/help.py** — Help core: frontmatter parsing, recursive loading of `docs/help/notes/**/*.md` (mtime-cached), `system:help` Note topics (owner/ACL respected), search/tag filter/relevance ranking/sort/pagination, home topic lookup, safe media path resolution.
- **hgai/api/routers/help_topics.py** — `/help` router: `GET /topics`, `/home`, `/topics/{id}`, `/media`, `/media/{path}` (media served with CSP sandbox + nosniff); all require an authenticated account.
- **hgai_module_agentchat/help_toolkit.py** — `HgaiHelpToolkit` (Agno toolkit) with `help_search` and `help_get`, constructed per turn with the caller's username.
- **tests/test_help.py** — 30 tests: frontmatter, recursion, fallbacks, drafts, duplicates, search/tag/sort/ranking, note-backed topics, media path safety, toolkit, and integrity checks over the shipped `docs/help` content (frontmatter, folder tags, unique ids, resolvable `help:`/`help-media:` links).
- **docs/help/notes/home.md** — Landing topic (`help-home`): explanation of HypergraphAI, component diagram, and links to common topics.
- **docs/help/notes/getting-started/{what-is-hypergraphai,quick-start}.md** — Getting Started topics.
- **docs/help/notes/concepts/{hypernodes,hyperedges,hypergraphs,edge-flavors,point-in-time,spaces}.md** — Concept topics.
- **docs/help/notes/web-ui/{web-ui-tour,notes,media,visualize,query-screen,parameterized-queries,project-inference,ai-chat,authoring-help}.md** — Web UI topics, including how to author help topics.
- **docs/help/notes/shql/{shql-overview,shql-patterns,shql-filters,shql-advanced,shql-examples}.md** — Query Language topics.
- **docs/help/notes/inference/inferencing.md** — Inferencing topic.
- **docs/help/notes/integration/{rest-api,authentication,mcp-server,mcp-tools,shell}.md** — Integration topics.
- **docs/help/notes/admin/{configuration,running-locally,docker,accounts-roles,meshes,backup,indexes-performance,modules}.md** — Administration topics.
- **docs/help/notes/reference/{faq,glossary}.md** — FAQ and glossary.
- **docs/help/media/hgai-component-layers.svg** — Component-layers diagram embedded via `help-media:`.

## Modified
- **hgai/config.py** — Added `help_dir` setting (`HGAI_HELP_DIR`, default `<project>/docs/help`).
- **hgai/main.py** — Imported and registered the `help_topics` router.
- **hgai_module_agentchat/engine.py** — Added `AGENT_INSTRUCTIONS` (use help tools for HypergraphAI questions and cite topic ids) and `HgaiHelpToolkit(account.username)` in the agent's tools.
- **ui/index.html** — Added the Help sidebar link and the `screen-help` markup (toolbar, folder sidebar with resize handle, search/tag filters, topic view, list view).
- **ui/js/api.js** — Added `listHelpTopics`, `getHelpTopic`, `getHelpHome`, `downloadHelpMedia` (authenticated blob fetch).
- **ui/js/app.js** — Generalized Notes folder-tree state/render (`opts`: onOpen, stateKey, showIdSuffix) and sidebar resize (`initFolderSidebarResize`); added Help screen logic (Home default, topic view with `help:`/`help-media:`/`media:`/`note:` handling, back history, list view with pagination/sort, clickable tag badges, folder tree with "Other" bucket, State/showScreen/PAGINATION_LOADERS wiring).
- **ui/css/hgai.css** — Added Help topic-pane styles (full-height reading pane, tables, code, blockquote, image max width, link/tag styling).
- **Dockerfile** — Added `COPY docs/help/ ./docs/help/` so built-in help ships in the image.
- **README.md** — Added `HGAI_HELP_DIR` config row, a Help bullet in the Web UI section, and a Help endpoints section.
- **docs/api-reference.md** — Added a "Help" section documenting the `/help/*` endpoints and topic object.
