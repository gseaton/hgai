"""Help topics: the content behind the Web UI's Help tab and the AI Agent's
help tools.

A help topic comes from one of two places, and both are presented through
one uniform topic shape (see `_file_topic` / `_note_topic`):

1. Markdown files under `<help_dir>/notes/**` (default `docs/help/notes`),
   read recursively. A file's topic fields — `id`, `label`, `name`,
   `description`, `tags` (and an optional `status`) — live in its YAML
   frontmatter; the rest of the file is the topic body. These ship with the
   project and are read-only from the UI.
2. Ordinary Notes carrying the tag `system:help` — visible to an account
   only if the Note itself is (owner/ACL), exactly like the Notes screen,
   so tagging a private note never leaks it to other accounts.

Media referenced by help topics lives under `<help_dir>/media/**` and is
served through `resolve_media_path` (which refuses anything that resolves
outside that directory).

Virtual help folders reuse the Notes convention: a tag shaped like
`//Folder/Sub Folder` places a topic in that folder (see the Help screen).
"""

import logging
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from hgai.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_HELP_TAG = "system:help"
HOME_RELATIVE_PATH = "home.md"
HOME_FALLBACK_ID = "help-home"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

_NOTE_PAGE_SIZE = 200
_NOTE_MAX_TOPICS = 1000
_SORT_FIELDS = ("label", "name", "system_updated", "source")


# ─── Locations ───────────────────────────────────────────────────────────────

def help_root() -> Path:
    configured = get_settings().help_dir
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[2] / "docs" / "help"


def notes_dir() -> Path:
    return help_root() / "notes"


def media_dir() -> Path:
    return help_root() / "media"


# ─── Frontmatter / file topics ───────────────────────────────────────────────

def parse_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
    """Split `raw` into (frontmatter dict, body). A file with no (or
    unparseable) frontmatter yields ({}, raw) rather than an error — a help
    file with a typo in its metadata should still show up, just less tidily."""
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        logger.warning(f"Help topic has unparseable frontmatter (ignored): {e}")
        return {}, raw[match.end():]
    if not isinstance(meta, dict):
        return {}, raw[match.end():]
    return meta, raw[match.end():]


def normalize_tags(value: Any) -> List[str]:
    """Frontmatter `tags` may be a YAML list or a comma-separated string."""
    if value is None:
        return []
    items = value.split(",") if isinstance(value, str) else list(value) if isinstance(value, (list, tuple)) else [value]
    seen: List[str] = []
    for item in items:
        tag = str(item).strip()
        if tag and tag not in seen:
            seen.append(tag)
    return seen


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _file_topic(path: Path, root: Path) -> Optional[Dict[str, Any]]:
    rel = path.relative_to(root).as_posix()
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    status = str(meta.get("status") or "active").strip().lower()
    if status != "active":
        return None

    topic_id = str(meta.get("id") or "").strip()
    if not _ID_RE.match(topic_id):
        topic_id = f"help-{_slug(rel[:-3] if rel.endswith('.md') else rel)}"

    label = str(meta.get("label") or "").strip()
    if not label:
        h1 = _H1_RE.search(body)
        label = h1.group(1) if h1 else path.stem.replace("-", " ").replace("_", " ").title()

    return {
        "id": topic_id,
        "source": "file",
        "path": rel,
        "label": label,
        "name": str(meta.get("name") or "").strip(),
        "description": str(meta.get("description") or "").strip(),
        "tags": normalize_tags(meta.get("tags")),
        "status": "active",
        "text": body.lstrip("\r\n"),
        "owner_username": None,
        "system_updated": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
    }


_file_cache: Dict[str, Tuple[int, int, Optional[Dict[str, Any]]]] = {}


def load_file_topics() -> List[Dict[str, Any]]:
    """Every active topic under `<help_dir>/notes`, recursively, in a stable
    (path-sorted) order. Parsed files are cached by (mtime, size), so editing
    a help file shows up on the next request without a server restart, while
    an unchanged file isn't re-read or re-parsed."""
    root = notes_dir()
    if not root.is_dir():
        return []

    topics: List[Dict[str, Any]] = []
    seen_ids: Dict[str, str] = {}
    for path in sorted(root.rglob("*.md")):
        rel_parts = path.relative_to(root).parts
        if any(part.startswith(".") for part in rel_parts) or not path.is_file():
            continue
        key = str(path)
        try:
            st = path.stat()
            cached = _file_cache.get(key)
            if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
                topic = cached[2]
            else:
                topic = _file_topic(path, root)
                _file_cache[key] = (st.st_mtime_ns, st.st_size, topic)
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Help topic '{path}' could not be read (skipped): {e}")
            continue
        if topic is None:
            continue
        if topic["id"] in seen_ids:
            logger.warning(
                f"Duplicate help topic id '{topic['id']}' in '{topic['path']}' "
                f"(already used by '{seen_ids[topic['id']]}') — skipped"
            )
            continue
        seen_ids[topic["id"]] = topic["path"]
        topics.append(dict(topic, tags=list(topic["tags"])))
    return topics


# ─── Note-backed topics ──────────────────────────────────────────────────────

def _note_topic(note: Any) -> Dict[str, Any]:
    return {
        "id": note.id,
        "source": "note",
        "path": None,
        "label": note.label,
        "name": note.name or "",
        "description": "",
        "tags": list(note.tags or []),
        "status": note.status,
        "text": note.text or "",
        "owner_username": note.owner_username,
        "system_updated": note.system_updated,
    }


async def load_note_topics(username: str) -> List[Dict[str, Any]]:
    """Active Notes visible to `username` that carry the `system:help` tag."""
    from hgai.core.notes import list_notes_visible_to

    topics: List[Dict[str, Any]] = []
    skip = 0
    while skip < _NOTE_MAX_TOPICS:
        total, notes = await list_notes_visible_to(
            username, tags=[SYSTEM_HELP_TAG], skip=skip, limit=_NOTE_PAGE_SIZE,
        )
        topics.extend(_note_topic(n) for n in notes if n.status == "active")
        skip += _NOTE_PAGE_SIZE
        if skip >= total:
            break
    return topics


async def all_topics(username: str) -> List[Dict[str, Any]]:
    """File topics plus the caller's visible `system:help` Notes. A file
    topic wins over a Note that happens to share its id."""
    topics = load_file_topics()
    taken = {t["id"] for t in topics}
    for topic in await load_note_topics(username):
        if topic["id"] not in taken:
            topics.append(topic)
    return topics


# ─── Search / list / get ─────────────────────────────────────────────────────

def _haystack(topic: Dict[str, Any]) -> str:
    parts = [topic["id"], topic["label"], topic["name"], topic["description"], " ".join(topic["tags"]), topic["text"]]
    return "\n".join(parts).lower()


def _matches(topic: Dict[str, Any], search: Optional[str], tags: Optional[List[str]]) -> bool:
    if tags:
        have = {t.lower() for t in topic["tags"]}
        if not all(t.lower() in have for t in tags):
            return False
    if search and search.strip():
        hay = _haystack(topic)
        if not all(term in hay for term in search.lower().split()):
            return False
    return True


def _sort_key(field: str):
    if field == "system_updated":
        return lambda t: t["system_updated"] or datetime.min.replace(tzinfo=timezone.utc)
    return lambda t: str(t.get(field) or "").lower()


def _sort(topics: List[Dict[str, Any]], sort: Optional[List[Tuple[str, int]]]) -> List[Dict[str, Any]]:
    spec = [(f, d) for f, d in (sort or []) if f in _SORT_FIELDS] or [("label", 1)]
    result = list(topics)
    for field, direction in reversed(spec):  # stable sorts, least-significant key first
        result.sort(key=_sort_key(field), reverse=direction < 0)
    return result


def _relevance(topic: Dict[str, Any], search: str) -> int:
    """Heuristic score of how well a (already matching) topic fits `search`:
    words found in the title-ish fields count far more than words that merely
    occur somewhere in the body, and the whole phrase appearing in a title,
    id or description counts most of all."""
    phrase = " ".join(search.lower().split())
    label = topic["label"].lower()
    ident = topic["id"].lower()
    name = (topic["name"] or "").lower()
    desc = (topic["description"] or "").lower()
    tags = " ".join(topic["tags"]).lower()
    body = topic["text"].lower()
    score = 0
    if phrase in label:
        score += 20
    if phrase.replace(" ", "-") in ident or phrase.replace(" ", "-") in name:
        score += 15
    if phrase in desc:
        score += 8
    for term in phrase.split():
        score += 10 * (term in label) + 8 * (term in ident or term in name)
        score += 5 * (term in tags) + 3 * (term in desc) + 1 * (term in body)
    return score


def _rank(topics: List[Dict[str, Any]], search: Optional[str], sort: Optional[List[Tuple[str, int]]]) -> List[Dict[str, Any]]:
    """An explicit `sort` wins; otherwise a search ranks by relevance (ties by
    label) and no search sorts by label."""
    if not sort and search and search.strip():
        return sorted(topics, key=lambda t: (-_relevance(t, search), t["label"].lower()))
    return _sort(topics, sort)


def without_text(topic: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in topic.items() if k != "text"}


async def list_topics(
    username: str,
    search: Optional[str] = None,
    tags: Optional[List[str]] = None,
    skip: int = 0,
    limit: int = 50,
    sort: Optional[List[Tuple[str, int]]] = None,
) -> Tuple[int, List[Dict[str, Any]]]:
    """(total, page of topics *without* their body text) matching the filters."""
    matched = [t for t in await all_topics(username) if _matches(t, search, tags)]
    ordered = _rank(matched, search, sort)
    return len(ordered), [without_text(t) for t in ordered[skip:skip + limit]]


async def get_topic(username: str, topic_id: str) -> Optional[Dict[str, Any]]:
    for topic in load_file_topics():
        if topic["id"] == topic_id:
            return topic
    from hgai.core.notes import can_view_note, get_note

    note = await get_note(topic_id)
    if note and note.status == "active" and SYSTEM_HELP_TAG in (note.tags or []) and can_view_note(note, username):
        return _note_topic(note)
    return None


async def get_home_topic(username: str) -> Optional[Dict[str, Any]]:
    """The landing topic: `notes/home.md`, or failing that the topic whose id
    is `help-home`."""
    topics = load_file_topics()
    for topic in topics:
        if (topic["path"] or "").lower() == HOME_RELATIVE_PATH:
            return topic
    for topic in topics:
        if topic["id"] == HOME_FALLBACK_ID:
            return topic
    return None


def make_snippet(text: str, search: Optional[str], width: int = 240) -> str:
    """A short excerpt of `text` around the first search term found in it
    (or the start of the text when there is no search / no hit)."""
    flat = " ".join(text.split())
    if not flat:
        return ""
    start = 0
    if search:
        lowered = flat.lower()
        hits = [lowered.find(term) for term in search.lower().split() if lowered.find(term) >= 0]
        if hits:
            start = max(0, min(hits) - width // 4)
    snippet = flat[start:start + width]
    return ("…" if start > 0 else "") + snippet + ("…" if start + width < len(flat) else "")


# ─── Media ───────────────────────────────────────────────────────────────────

def resolve_media_path(relative: str) -> Optional[Path]:
    """Absolute path of a help media file, or None if it doesn't exist or
    would resolve outside the media directory (`..` segments, absolute
    paths, symlink escapes). Callers should treat None as a plain 404."""
    if not relative or "\x00" in relative or "\\" in relative:
        return None
    root = media_dir().resolve()
    try:
        candidate = (root / relative).resolve()
    except (OSError, RuntimeError):
        return None
    if candidate != root and root not in candidate.parents:
        return None
    if any(part.startswith(".") for part in candidate.relative_to(root).parts):
        return None
    return candidate if candidate.is_file() else None


def list_media() -> List[Dict[str, Any]]:
    root = media_dir()
    if not root.is_dir():
        return []
    items = []
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if not path.is_file() or any(part.startswith(".") for part in rel_parts):
            continue
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        items.append({
            "path": path.relative_to(root).as_posix(),
            "filename": path.name,
            "content_type": content_type,
            "size_bytes": path.stat().st_size,
        })
    return items
