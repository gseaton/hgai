"""Help-topic access for the chat agent: search and read the same topics the
Web UI's Help tab shows (`docs/help/notes/**` plus the calling account's
visible `system:help` Notes — see hgai.core.help).

Runs in-process against the help core rather than over the MCP endpoint: the
MCP tools have no per-account context, and note-backed topics must only be
visible to the account that could open them in the Notes screen. The
toolkit is therefore constructed per chat turn with the requesting
account's username (see engine.build_agent).
"""

import json

from agno.tools import Toolkit

from hgai.core import help as help_core

MAX_RESULTS_CAP = 25
MAX_TOPIC_CHARS = 15000


class HgaiHelpToolkit(Toolkit):
    """Lets the chat agent answer questions about HypergraphAI itself from the
    built-in help topics instead of from memory."""

    def __init__(self, username: str, **kwargs):
        self._username = username
        super().__init__(name="hgai_help", tools=[self.help_search, self.help_get], **kwargs)

    async def help_search(self, query: str, max_results: int = 5) -> str:
        """Search the HypergraphAI help topics (documentation) by keyword.

        Use this first for any question about HypergraphAI itself — what it
        is, its concepts (hypernodes, hyperedges, hypergraphs), SHQL query
        syntax, inferencing, configuration, the REST/MCP APIs, or how to use
        the Web UI — then read the best match with help_get. Every word in
        the query must appear in a topic (id, label, description, tags, or
        text). Pass an empty query to list the topic index instead.

        Args:
            query: Keywords to look for, e.g. "point in time query" or "api key".
            max_results: How many topics to return (default 5, at most 25;
                an empty query returns up to 50 for the index).

        Returns:
            A JSON list of matching topics — id, label, description, tags,
            and a short snippet — the best match first.
        """
        blank = not (query or "").strip()
        limit = 50 if blank else max(1, min(int(max_results), MAX_RESULTS_CAP))
        topics = await help_core.all_topics(self._username)
        matched = [t for t in topics if help_core._matches(t, query, None)]
        matched = help_core._rank(matched, query, None)[:limit]
        return json.dumps([
            {
                "id": t["id"],
                "label": t["label"],
                "description": t["description"],
                "tags": t["tags"],
                **({} if blank else {"snippet": help_core.make_snippet(t["text"], query)}),
            }
            for t in matched
        ], indent=2)

    async def help_get(self, topic_id: str) -> str:
        """Read one HypergraphAI help topic in full.

        Args:
            topic_id: A topic id returned by help_search (for the landing /
                overview topic use "help-home"). Links inside a topic written
                as (help:<topic-id>) refer to other topics by id.

        Returns:
            The topic's label and description followed by its Markdown text
            (truncated if very long), or an error message if no such topic
            exists or it isn't visible to the current account.
        """
        topic = await help_core.get_topic(self._username, (topic_id or "").strip())
        if not topic:
            return f"Error: no help topic with id '{topic_id}' — use help_search to find one"
        text = topic["text"]
        if len(text) > MAX_TOPIC_CHARS:
            text = text[:MAX_TOPIC_CHARS] + f"\n\n[... truncated, {len(topic['text']) - MAX_TOPIC_CHARS} more characters not shown ...]"
        header = f"# {topic['label']}\n\n"
        if topic["description"]:
            header += f"_{topic['description']}_\n\n"
        return header + text
