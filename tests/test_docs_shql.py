"""Every SHQL example printed in the README and the built-in Help must at least
parse and validate — a query that can't be pasted into the Query screen is a
documentation bug. (The examples over the seed hypergraphs are also executed
against a seeded server whenever the docs change; see scripts/seeds/.)

The classic trap this guards: an unquoted `?variable` inside flow-style YAML
(`{ bind: ?x }` or `[?a, ?b]`) is not valid YAML."""

import glob
import re
from pathlib import Path

import pytest

from hgai_module_shql.parser import parse_shql, validate_shql

ROOT = Path(__file__).resolve().parent.parent
DOC_FILES = [ROOT / "README.md", ROOT / "docs" / "api-reference.md"] + sorted(
    Path(p) for p in glob.glob(str(ROOT / "docs" / "help" / "notes" / "**" / "*.md"), recursive=True)
)


def _shql_blocks():
    for path in DOC_FILES:
        text = path.read_text()
        for m in re.finditer(r"```ya?ml\n(.*?)```", text, re.S):
            block = m.group(1)
            if re.match(r"\s*shql:", block) and "/$" not in block:   # skip parameterized templates
                line = text[: m.start()].count("\n") + 2
                yield pytest.param(block, id=f"{path.relative_to(ROOT)}:{line}")


@pytest.mark.parametrize("block", list(_shql_blocks()))
def test_documented_shql_parses_and_validates(block):
    query = parse_shql(block)
    assert validate_shql(query) == []
