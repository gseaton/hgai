"""Error fingerprinting and `kind: "error"` event construction (plan §7).

Shared by every surface's error path (REST exception handlers, SHQL's
`execute_shql` boundary; MCP and the others follow in later phases) so a
bug fingerprints the same way regardless of which surface caught it.
"""

import hashlib
import re
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from .events import build_event

# Only frames under the project root are ever reported — a stdlib or
# site-packages frame is never "ours" to report, and the plan is explicit
# that stack frames carry no source text or locals, only file:line:function.
_REPO_ROOT = Path(__file__).resolve().parents[1]

# Redacts any single- or double-quoted run — this is how the vast majority
# of user-data-bearing values enter an error message in this codebase (e.g.
# `f"Hypergraph not found: {ref!r}"`, plan §7's own worked example): `!r` on
# a string produces exactly this shape. Bounded length guards against a
# pathological huge message; two-arg alternation keeps quote characters from
# leaking through unescaped.
_QUOTED = re.compile(r"'[^']{0,200}'|\"[^\"]{0,200}\"")


def templatize_message(message: str) -> str:
    """The *template* of an exception message — same shape, no data.

    `"Hypergraph not found: 'my-project'"` and `"Hypergraph not found:
    'other-project'"` both become `"Hypergraph not found: '…'"`, so two
    occurrences of the same underlying bug against different customers'
    data fingerprint identically instead of flooding distinct "unique"
    errors per graph name (plan §7). This is a generic, message-level
    heuristic rather than every raise site passing an explicit template —
    lower precision, but it needs no changes anywhere error messages are
    built, and covers the common `{value!r}` / `f"...{x}..."` shape.
    """
    return _QUOTED.sub("'…'", message)


def stack_frames(tb: Optional[Any], limit: int = 8) -> List[Dict[str, Any]]:
    """Repo-relative `{file, line, function}` for every in-repo frame in
    `tb`, innermost last — no source text (plan §7 is explicit: none, ever).
    A frame outside the repo (stdlib, a dependency) is dropped; this project
    doesn't get to explain someone else's code."""
    frames: List[Dict[str, Any]] = []
    for fs in traceback.extract_tb(tb):
        try:
            rel = Path(fs.filename).resolve().relative_to(_REPO_ROOT)
        except ValueError:
            continue
        frames.append({"file": str(rel), "line": fs.lineno, "function": fs.name})
    return frames[-limit:]


def fingerprint(exc_type: str, frame_key: str, template: str) -> str:
    """sha256(exception_type + frame + message_template) (plan §7).

    `frame_key` should be the *innermost* repo frame — the one closest to
    where the exception was actually raised, not the outer entry point every
    error passing through the same chokepoint (e.g. `execute_shql`) would
    otherwise share, which would make every SHQL bug fingerprint identically
    regardless of its real location.
    """
    return hashlib.sha256(f"{exc_type}|{frame_key}|{template}".encode("utf-8")).hexdigest()


def build_error_event(
    exc: BaseException,
    *,
    surface: str,
    surface_context: str,
    feature: str,
    duration_ms: float,
    outcome: str,
    account: Optional[Dict[str, Any]],
    http_status: Optional[int] = None,
) -> Dict[str, Any]:
    """One `kind: "error"` event record (plan §3/§7) for `exc`."""
    frames = stack_frames(exc.__traceback__)
    frame_key = f"{frames[-1]['file']}:{frames[-1]['line']}:{frames[-1]['function']}" if frames else "no-repo-frame"
    template = templatize_message(str(exc))
    exc_type = type(exc).__name__
    return build_event(
        kind="error", surface=surface, feature=feature, duration_ms=duration_ms, outcome=outcome,
        account=account, attributes={},
        error={
            "fingerprint": fingerprint(exc_type, frame_key, template),
            "type": exc_type,
            "message_template": template,
            "surface_context": surface_context,
            "http_status": http_status,
            "stack_frames": frames,
        },
    )


def build_error_event_from_message(
    exc_type: str,
    message: str,
    *,
    surface: str,
    surface_context: str,
    feature: str,
    duration_ms: float,
    outcome: str,
    account: Optional[Dict[str, Any]],
    http_status: Optional[int] = None,
) -> Dict[str, Any]:
    """`build_error_event`'s counterpart for a failure that was already
    caught and turned into a `{"error": ..., "type": ...}` string before
    telemetry ever saw it (e.g. an MCP tool's own try/except, plan §4's MCP
    row) — no live exception, so no traceback to extract `stack_frames`
    from. `frame_key` falls back to `surface_context:feature`, which is
    still a stable per-call-site key (two different tools raising the same
    generic `"type"` still fingerprint differently), just coarser than a
    real stack frame.
    """
    template = templatize_message(message)
    frame_key = f"{surface_context}:{feature}"
    return build_event(
        kind="error", surface=surface, feature=feature, duration_ms=duration_ms, outcome=outcome,
        account=account, attributes={},
        error={
            "fingerprint": fingerprint(exc_type, frame_key, template),
            "type": exc_type,
            "message_template": template,
            "surface_context": surface_context,
            "http_status": http_status,
            "stack_frames": [],
        },
    )
