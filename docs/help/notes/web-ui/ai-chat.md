---
id: help-ai-chat
label: AI Chat agent
name: ai-chat
description: The collapsible AI Chat panel — asking questions about your hypergraphs or HypergraphAI itself, sessions, history, and saving answers as Notes.
tags: ["//Using the Web UI", ai, agent, chat, mcp, llm]
status: active
---

# AI Chat agent

The **AI Chat** button in the top bar opens a chat panel on the right side of the UI. The agent is connected to the running HypergraphAI server, so you can ask about the knowledge stored in your hypergraphs *and* about HypergraphAI itself. Drag the panel's left edge to resize it; the width is remembered.

## What the agent can do

| Capability | Used for |
|---|---|
| **hgai tools** (the server's own [MCP tools](help:help-mcp-tools)) | Reading and querying your hypergraphs — local ones, and federated ones through [meshes](help:help-meshes). The agent acts **with your account's permissions**: a graph you cannot read, write or query is refused to the agent too, and it will tell you so (see [MCP server](help:help-mcp-server)). |
| **Help topics** | Questions about HypergraphAI — what a hyperedge is, how to write SHQL, how to configure the server. The agent searches this Help library and answers from it, citing the topic ids it used. |
| **Web fetch** | Reading a specific web page you give it (private and internal network addresses are refused) |

Ask, for example: *"Who were the members of the Three Stooges in 1940?"* (answered from your data) or *"How do I run a point-in-time query?"* (answered from Help).

## Using the panel

- **Model** — choose which configured model answers. Only enabled models with an API key appear.
- **Sessions** — the agent remembers the conversation within a session. Reopen an earlier session to continue it, or start a **New session** for a clean slate.
- **Prompt history** — your last 50 prompts are kept per account (they persist across server restarts, browsers and machines) so you can reuse them.
- **Save as Note** — turn any prompt/response into a [Note](help:help-notes). The note gets an id like `hgai-note-chat-<yymmddhhmmss>-<4 digits>`, and its front matter records the prompt, vendor/model, start and stop times, duration and tokens used, followed by the response in Markdown.

## Setting it up (administrators)

Open **AI Agent** in the sidebar. A small default catalog of vendors (Anthropic, OpenAI, xAI/Grok) and models is pre-seeded but **disabled with no key**. For a vendor: add its **API key** (stored encrypted at rest), optionally a base URL, and enable it; then enable the models you want (with optional default temperature and max tokens). You can add your own vendors and models too. Only administrators can see or change vendors, models and keys.

## Notes

- **Data access is scoped to your account.** Each chat turn calls the MCP tools with a token for the signed-in account, so graph reads, writes and queries are checked exactly as they are for you in the UI or REST API. Note-backed help topics are likewise limited to notes the account can view. An administrator's agent can reach everything an administrator can.
- Answers come from a language model; check important facts against the data (the agent is instructed to say when the data or the help topics don't contain an answer).

See also: [MCP server](help:help-mcp-server), [Help authoring](help:help-authoring-help).
