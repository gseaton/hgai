"""Tests for hgsh's telemetry reporting (Phase 4 of
docs/architect/telemetry-20260929061557.md §4's hgsh row).

hgsh runs as a separate process from the server (see
shell/hgai_shell.py::HgaiClient), so its telemetry goes through the same
authenticated /telemetry/ingest endpoint the Web UI uses — exercised for
real in tests/test_telemetry_ingest.py. These tests cover the shell-side
pieces: canonical command naming across aliases, and that reporting never
raises into the command loop.
"""

from unittest.mock import MagicMock, patch

import pytest

from shell.hgai_shell import HgaiClient, HgaiShell, _canonical_command_name


@pytest.mark.parametrize("typed, expected", [
    ("delete-node", "delete-node"),
    ("dn", "delete-node"),          # alias -> canonical name, not the alias typed
    ("de", "delete-edge"),
    ("sq", "shql"),
    ("sv", "shql-validate"),
    ("mq", "mesh-query"),
])
def test_canonical_command_name_resolves_aliases_to_their_real_command(typed, expected):
    shell = HgaiShell()
    # handle() maps both an alias and its full name to the same bound method
    # (e.g. "dn" and "delete-node" both -> shell.cmd_delete_node); reproduce
    # that here rather than importing its inline dict.
    bound = getattr(shell, "cmd_" + expected.replace("-", "_"))
    assert _canonical_command_name(typed, bound) == expected


def test_canonical_command_name_falls_back_to_the_typed_command_for_lambdas():
    assert _canonical_command_name("cls", lambda a: None) == "cls"


def test_track_feature_is_a_noop_before_login():
    client = HgaiClient("http://localhost:8357")  # no token set
    with patch.object(client, "_client") as mock_http:
        client.track_feature("shell.ls")
    mock_http.post.assert_not_called()


def test_track_feature_posts_to_the_ingest_endpoint_when_authenticated():
    client = HgaiClient("http://localhost:8357", token="tok")
    client._client = MagicMock()
    client.track_feature("shell.import-rdf", {"format": "ttl"}, outcome="ok")
    args, kwargs = client._client.post.call_args
    assert args[0] == "http://localhost:8357/api/v1/telemetry/ingest"
    assert kwargs["json"]["surface"] == "shell"
    assert kwargs["json"]["feature"] == "shell.import-rdf"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


def test_track_feature_never_raises_even_if_the_request_fails():
    client = HgaiClient("http://localhost:8357", token="tok")
    client._client = MagicMock()
    client._client.post.side_effect = RuntimeError("network is down")
    client.track_feature("shell.ls")  # must not raise
