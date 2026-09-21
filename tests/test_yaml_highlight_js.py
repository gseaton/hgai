"""Runs the Node test for the Web UI's YAML highlighter (ui/js/yaml-highlight.js)
when Node.js is available; skipped otherwise."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_yaml_highlighter_js_suite_passes():
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "js" / "test_yaml_highlight.js")],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "tests passed" in result.stdout
