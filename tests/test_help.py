"""Tests for the Help system (hgai/core/help.py, the help router's path
handling, hgai_module_agentchat/help_toolkit.py) and an integrity check over
the shipped topics in docs/help/notes.

Note-backed topics go through hgai.core.notes (storage-backed, so — per this
project's convention, see tests/test_notes.py — verified live rather than
unit tested); here `list_notes_visible_to` / `get_note` are patched with
plain fakes, which is enough to test the help-specific logic layered on top
(tag filter, visibility check, id precedence, active-only).
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from hgai.core import help as help_core
from hgai_module_agentchat.help_toolkit import HgaiHelpToolkit

REAL_HELP_ROOT = Path(__file__).resolve().parents[1] / "docs" / "help"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / "notes" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def help_root(tmp_path):
    help_core._file_cache.clear()
    with patch.object(help_core, "help_root", return_value=tmp_path):
        yield tmp_path
    help_core._file_cache.clear()


def _note(id_, label="A note", tags=("system:help",), owner="alice", acl=None, status="active", text="body", name="", scope="protected"):
    return SimpleNamespace(
        id=id_, label=label, name=name, tags=list(tags), owner_username=owner, acl=acl or [], scope=scope,
        status=status, text=text, system_updated=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


# ─── frontmatter ─────────────────────────────────────────────────────────────

def test_parse_frontmatter_splits_meta_and_body():
    meta, body = help_core.parse_frontmatter("---\nid: x\ntags: [a, b]\n---\n# Title\ntext\n")
    assert meta == {"id": "x", "tags": ["a", "b"]}
    assert body == "# Title\ntext\n"


def test_parse_frontmatter_absent_or_broken_never_raises():
    assert help_core.parse_frontmatter("# just markdown\n") == ({}, "# just markdown\n")
    meta, body = help_core.parse_frontmatter("---\nid: [unclosed\n---\nbody\n")
    assert meta == {} and body == "body\n"
    meta, body = help_core.parse_frontmatter("---\n- a\n- b\n---\nbody\n")
    assert meta == {} and body == "body\n"


def test_normalize_tags_accepts_list_or_comma_string_and_dedupes():
    assert help_core.normalize_tags(["//Docs", " shql ", "shql", ""]) == ["//Docs", "shql"]
    assert help_core.normalize_tags("a, b,,a") == ["a", "b"]
    assert help_core.normalize_tags(None) == []


# ─── file topics ─────────────────────────────────────────────────────────────

def test_file_topics_read_recursively_with_frontmatter_fields(help_root):
    _write(help_root, "home.md", "---\nid: help-home\nlabel: Home\nname: Start\ndescription: Landing\ntags: ['//Getting Started']\n---\n# Welcome\n")
    _write(help_root, "deep/er/topic.md", "---\nid: help-deep\nlabel: Deep\n---\nbody\n")
    topics = {t["id"]: t for t in help_core.load_file_topics()}
    assert set(topics) == {"help-home", "help-deep"}
    home = topics["help-home"]
    assert (home["label"], home["name"], home["description"], home["tags"]) == ("Home", "Start", "Landing", ["//Getting Started"])
    assert home["source"] == "file" and home["path"] == "home.md"
    assert home["text"].startswith("# Welcome")
    assert topics["help-deep"]["path"] == "deep/er/topic.md"


def test_file_topic_defaults_when_frontmatter_is_thin(help_root):
    _write(help_root, "some-file_name.md", "# The Real Title\n\ntext\n")
    _write(help_root, "no-heading.md", "just text\n")
    topics = {t["path"]: t for t in help_core.load_file_topics()}
    assert topics["some-file_name.md"]["id"] == "help-some-file-name"
    assert topics["some-file_name.md"]["label"] == "The Real Title"
    assert topics["no-heading.md"]["label"] == "No Heading"


def test_invalid_frontmatter_id_falls_back_to_path_derived_id(help_root):
    _write(help_root, "sub/a.md", "---\nid: 'has spaces/and slash'\n---\nx\n")
    assert help_core.load_file_topics()[0]["id"] == "help-sub-a"


def test_draft_hidden_files_and_non_markdown_are_skipped(help_root):
    _write(help_root, "draft.md", "---\nid: help-draft\nstatus: draft\n---\nx\n")
    _write(help_root, ".hidden/secret.md", "---\nid: help-secret\n---\nx\n")
    _write(help_root, "notes.txt", "not markdown")
    _write(help_root, "ok.md", "---\nid: help-ok\n---\nx\n")
    assert [t["id"] for t in help_core.load_file_topics()] == ["help-ok"]


def test_duplicate_ids_keep_the_first_by_path_order(help_root):
    _write(help_root, "a.md", "---\nid: help-dup\nlabel: First\n---\nx\n")
    _write(help_root, "b.md", "---\nid: help-dup\nlabel: Second\n---\nx\n")
    topics = help_core.load_file_topics()
    assert [t["label"] for t in topics] == ["First"]


def test_edited_file_is_picked_up_without_restart(help_root):
    _write(help_root, "a.md", "---\nid: help-a\nlabel: Old\n---\nx\n")
    assert help_core.load_file_topics()[0]["label"] == "Old"
    _write(help_root, "a.md", "---\nid: help-a\nlabel: New label, longer\n---\nx\n")
    assert help_core.load_file_topics()[0]["label"] == "New label, longer"


def test_missing_help_dir_yields_no_topics(tmp_path):
    with patch.object(help_core, "help_root", return_value=tmp_path / "does-not-exist"):
        assert help_core.load_file_topics() == []


# ─── search / list / sort ────────────────────────────────────────────────────

@pytest.fixture
def three_topics(help_root):
    _write(help_root, "home.md", "---\nid: help-home\nlabel: Home\ntags: ['//Getting Started', overview]\n---\nWelcome to HypergraphAI\n")
    _write(help_root, "shql.md", "---\nid: help-shql\nlabel: SHQL Overview\ndescription: The query language\ntags: ['//Querying', shql]\n---\nPoint-in-time queries use the at key.\n")
    _write(help_root, "api.md", "---\nid: help-api\nlabel: REST API\ntags: ['//Reference', api]\n---\nEndpoints and authentication.\n")


@pytest.mark.asyncio
async def test_list_filters_by_search_words_and_tags(three_topics):
    with patch.object(help_core, "load_note_topics", AsyncMock(return_value=[])):
        total, items = await help_core.list_topics("alice", search="point time")
        assert [t["id"] for t in items] == ["help-shql"]

        total, items = await help_core.list_topics("alice", tags=["SHQL"])
        assert [t["id"] for t in items] == ["help-shql"]

        total, items = await help_core.list_topics("alice", search="hypergraphai", tags=["overview"])
        assert [t["id"] for t in items] == ["help-home"]

        total, items = await help_core.list_topics("alice", search="nonexistent-term")
        assert (total, items) == (0, [])


@pytest.mark.asyncio
async def test_list_omits_body_text_sorts_and_paginates(three_topics):
    with patch.object(help_core, "load_note_topics", AsyncMock(return_value=[])):
        total, items = await help_core.list_topics("alice")
        assert total == 3
        assert all("text" not in t for t in items)
        assert [t["label"] for t in items] == ["Home", "REST API", "SHQL Overview"]

        _, desc = await help_core.list_topics("alice", sort=[("label", -1)])
        assert [t["label"] for t in desc] == ["SHQL Overview", "REST API", "Home"]

        total, page = await help_core.list_topics("alice", skip=1, limit=1)
        assert total == 3 and [t["label"] for t in page] == ["REST API"]


@pytest.mark.asyncio
async def test_unknown_sort_fields_fall_back_to_label(three_topics):
    with patch.object(help_core, "load_note_topics", AsyncMock(return_value=[])):
        _, items = await help_core.list_topics("alice", sort=[("password_hash", 1)])
        assert [t["label"] for t in items] == ["Home", "REST API", "SHQL Overview"]


# ─── home / get ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_home_topic_is_notes_home_md(help_root):
    _write(help_root, "zzz.md", "---\nid: help-home\nlabel: Fallback id holder\n---\nx\n")
    _write(help_root, "home.md", "---\nid: help-landing\nlabel: Landing\n---\nx\n")
    assert (await help_core.get_home_topic("alice"))["id"] == "help-landing"


@pytest.mark.asyncio
async def test_home_topic_falls_back_to_help_home_id_then_none(help_root):
    assert await help_core.get_home_topic("alice") is None
    _write(help_root, "start/here.md", "---\nid: help-home\nlabel: H\n---\nx\n")
    assert (await help_core.get_home_topic("alice"))["id"] == "help-home"


@pytest.mark.asyncio
async def test_get_topic_returns_text_for_file_topics(three_topics):
    topic = await help_core.get_topic("alice", "help-shql")
    assert "Point-in-time" in topic["text"]


# ─── note-backed topics ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_note_topics_are_active_system_help_notes_and_file_id_wins(help_root):
    _write(help_root, "a.md", "---\nid: help-a\nlabel: File A\n---\nx\n")
    notes = [_note("n1", label="Team runbook"), _note("n2", status="archived"), _note("help-a", label="Impostor")]
    fake = AsyncMock(return_value=(3, notes))
    with patch("hgai.core.notes.list_notes_visible_to", fake):
        topics = await help_core.all_topics("alice")
    assert sorted(t["id"] for t in topics) == ["help-a", "n1"]
    assert next(t for t in topics if t["id"] == "help-a")["source"] == "file"
    note_topic = next(t for t in topics if t["id"] == "n1")
    assert (note_topic["source"], note_topic["owner_username"]) == ("note", "alice")
    # The caller's visibility and the system:help tag are asked of the notes layer, not re-derived here.
    assert fake.await_args.args == ("alice",)
    assert fake.await_args.kwargs["tags"] == ["system:help"]


@pytest.mark.asyncio
async def test_get_topic_for_a_note_requires_tag_visibility_and_active(help_root):
    async def run(note, username="alice"):
        with patch("hgai.core.notes.get_note", AsyncMock(return_value=note)):
            return await help_core.get_topic(username, "n1")

    assert (await run(_note("n1")))["source"] == "note"
    assert await run(_note("n1", tags=["other"])) is None            # not a help note
    assert await run(_note("n1", status="draft")) is None
    assert await run(_note("n1", owner="alice"), username="mallory") is None   # private to its owner
    shared = _note("n1", owner="alice", acl=[SimpleNamespace(username="bob", role="viewer")])
    assert (await run(shared, username="bob"))["id"] == "n1"           # visible via ACL
    assert await run(None) is None


# ─── snippets ────────────────────────────────────────────────────────────────

def test_snippet_centers_on_first_hit_and_marks_truncation():
    text = "intro " * 50 + "the needle is here " + "tail " * 50
    snippet = help_core.make_snippet(text, "needle", width=60)
    assert "needle" in snippet and snippet.startswith("…") and snippet.endswith("…")
    assert help_core.make_snippet("short text", "zzz", width=60) == "short text"
    assert help_core.make_snippet("", "x") == ""


# ─── media path safety ───────────────────────────────────────────────────────

def test_media_resolution_allows_nested_files_and_blocks_escapes(help_root):
    (help_root / "media" / "img").mkdir(parents=True)
    (help_root / "media" / "img" / "pic.png").write_bytes(b"png")
    (help_root / "secret.txt").write_text("outside the media dir")
    (help_root / "media" / ".hidden.png").write_bytes(b"x")

    assert help_core.resolve_media_path("img/pic.png") == (help_root / "media" / "img" / "pic.png").resolve()
    assert help_core.resolve_media_path("../secret.txt") is None
    assert help_core.resolve_media_path("img/../../secret.txt") is None
    assert help_core.resolve_media_path("/etc/passwd") is None
    assert help_core.resolve_media_path("img\\pic.png") is None
    assert help_core.resolve_media_path("img/pic.png\x00.txt") is None
    assert help_core.resolve_media_path(".hidden.png") is None
    assert help_core.resolve_media_path("img") is None            # a directory
    assert help_core.resolve_media_path("missing.png") is None
    assert help_core.resolve_media_path("") is None


def test_media_symlink_escape_is_blocked(help_root):
    (help_root / "media").mkdir()
    outside = help_root / "outside.txt"
    outside.write_text("nope")
    (help_root / "media" / "link.txt").symlink_to(outside)
    assert help_core.resolve_media_path("link.txt") is None


def test_list_media_is_recursive_and_typed(help_root):
    (help_root / "media" / "a").mkdir(parents=True)
    (help_root / "media" / "a" / "d.svg").write_text("<svg/>")
    (help_root / "media" / "b.png").write_bytes(b"x")
    items = {i["path"]: i for i in help_core.list_media()}
    assert set(items) == {"a/d.svg", "b.png"}
    assert items["a/d.svg"]["content_type"] == "image/svg+xml"


# ─── agent toolkit ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_toolkit_search_returns_json_with_snippets(three_topics):
    toolkit = HgaiHelpToolkit("alice")
    with patch.object(help_core, "load_note_topics", AsyncMock(return_value=[])):
        results = json.loads(await toolkit.help_search("point-in-time"))
        assert [r["id"] for r in results] == ["help-shql"]
        assert "Point-in-time" in results[0]["snippet"]

        index = json.loads(await toolkit.help_search(""))
        assert len(index) == 3 and all("snippet" not in r for r in index)

        assert json.loads(await toolkit.help_search("zzzznothing")) == []


@pytest.mark.asyncio
async def test_toolkit_get_returns_markdown_or_error(three_topics):
    toolkit = HgaiHelpToolkit("alice")
    with patch.object(help_core, "load_note_topics", AsyncMock(return_value=[])):
        text = await toolkit.help_get("help-shql")
        assert text.startswith("# SHQL Overview") and "The query language" in text and "at key" in text
    with patch("hgai.core.notes.get_note", AsyncMock(return_value=None)):
        assert (await toolkit.help_get("no-such-topic")).startswith("Error: no help topic")


def test_toolkit_registers_both_tools():
    functions = HgaiHelpToolkit("alice").get_async_functions()
    assert {"help_search", "help_get"} <= set(functions)


# ─── integrity of the shipped topics in docs/help ────────────────────────────

def _shipped():
    help_core._file_cache.clear()
    with patch.object(help_core, "help_root", return_value=REAL_HELP_ROOT):
        return help_core.load_file_topics()


def test_shipped_home_topic_exists_and_is_the_landing_page():
    home = [t for t in _shipped() if t["path"] == "home.md"]
    assert len(home) == 1
    assert home[0]["id"] == "help-home" and home[0]["tags"]


def test_every_shipped_topic_has_complete_frontmatter_and_a_folder_tag():
    problems = []
    for t in _shipped():
        raw_meta, _ = help_core.parse_frontmatter((REAL_HELP_ROOT / "notes" / t["path"]).read_text(encoding="utf-8"))
        for field in ("id", "label", "name", "description", "tags"):
            if not raw_meta.get(field):
                problems.append(f"{t['path']}: missing frontmatter '{field}'")
        if not t["id"].startswith("help-"):
            problems.append(f"{t['path']}: id '{t['id']}' should start with 'help-'")
        if not any(tag.startswith("//") and len(tag) > 2 for tag in t["tags"]):
            problems.append(f"{t['path']}: no '//Folder' tag, so it would not appear in the folder tree")
        if not t["text"].strip():
            problems.append(f"{t['path']}: empty body")
    assert not problems, "\n".join(problems)


def test_shipped_topic_ids_and_paths_are_unique():
    raw_ids = []
    for path in sorted((REAL_HELP_ROOT / "notes").rglob("*.md")):
        meta, _ = help_core.parse_frontmatter(path.read_text(encoding="utf-8"))
        raw_ids.append(meta.get("id"))
    assert len(raw_ids) == len(set(raw_ids)), "duplicate ids in docs/help/notes"
    assert len(raw_ids) == len(_shipped()), "some help files were skipped as invalid/duplicate/draft"


def test_shipped_help_links_and_media_references_resolve():
    topics = _shipped()
    ids = {t["id"] for t in topics}
    media = {m["path"] for m in (lambda: [i for i in _list_real_media()])()}
    broken = []
    for t in topics:
        # Link *syntax* shown as an example inside code fences / `inline code`
        # isn't a real link, so it is excluded from the check.
        prose = re.sub(r"`[^`\n]*`", "", re.sub(r"```.*?```", "", t["text"], flags=re.S))
        for target in re.findall(r"\]\(help:([^)\s]+)\)", prose):
            if target not in ids:
                broken.append(f"{t['path']}: (help:{target}) has no such topic")
        for target in re.findall(r"\]\(help-media:([^)\s]+)\)", prose):
            if target not in media:
                broken.append(f"{t['path']}: (help-media:{target}) has no such file in docs/help/media")
    assert not broken, "\n".join(broken)


def _list_real_media():
    with patch.object(help_core, "help_root", return_value=REAL_HELP_ROOT):
        return help_core.list_media()


def test_search_ranks_title_matches_above_body_only_matches():
    def topic(id_, label, text, tags=None, desc=""):
        return {"id": id_, "source": "file", "path": None, "label": label, "name": "", "description": desc,
                "tags": tags or [], "status": "active", "text": text, "owner_username": None, "system_updated": None}

    topics = [
        topic("help-a-faq", "A Frequently Asked", "mentions point in time once"),
        topic("help-point-in-time", "Point-in-time queries", "body"),
        topic("help-other", "Other", "point time in body"),
    ]
    ordered = help_core._rank([t for t in topics if help_core._matches(t, "point in time", None)], "point in time", None)
    assert [t["id"] for t in ordered][0] == "help-point-in-time"
    # an explicit sort overrides relevance, and no search falls back to label order
    assert [t["label"] for t in help_core._rank(topics, "point in time", [("label", 1)])] == ["A Frequently Asked", "Other", "Point-in-time queries"]
    assert [t["label"] for t in help_core._rank(topics, None, None)] == ["A Frequently Asked", "Other", "Point-in-time queries"]


def test_a_public_note_is_a_help_topic_for_any_account_but_a_private_one_is_not():
    with patch("hgai.core.notes.get_note", AsyncMock(return_value=_note("n2", owner="alice", scope="public"))):
        assert asyncio.run(help_core.get_topic("mallory", "n2"))["id"] == "n2"
    with patch("hgai.core.notes.get_note", AsyncMock(return_value=_note("n3", owner="alice", scope="private"))):
        assert asyncio.run(help_core.get_topic("mallory", "n3")) is None


@pytest.mark.parametrize("scope, share_list_member, stranger", [
    ("private", False, False),
    ("protected", True, False),
    ("protected-edit", True, False),
    ("public", True, True),
    ("public-edit", True, True),
])
def test_a_system_help_note_is_a_help_topic_exactly_when_scope_lets_the_account_view_it(scope, share_list_member, stranger):
    """Help includes every active `system:help` Note the account can at least view."""
    note = _note("n9", owner="alice", scope=scope, acl=[SimpleNamespace(username="bob", role="viewer")])
    with patch("hgai.core.notes.get_note", AsyncMock(return_value=note)):
        assert bool(asyncio.run(help_core.get_topic("alice", "n9"))) is True                # owner
        assert bool(asyncio.run(help_core.get_topic("bob", "n9"))) is share_list_member
        assert bool(asyncio.run(help_core.get_topic("mallory", "n9"))) is stranger


def test_a_visible_note_without_the_system_help_tag_or_not_active_is_not_a_help_topic():
    for note in (_note("n8", scope="public", tags=("other",)), _note("n7", scope="public", status="draft")):
        with patch("hgai.core.notes.get_note", AsyncMock(return_value=note)):
            assert asyncio.run(help_core.get_topic("mallory", note.id)) is None
