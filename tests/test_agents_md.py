"""AGENTS.md conformance test (issue #40).

Docs: tests/test_agents_md.doc.md
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"

MANDATORY_SECTIONS: tuple[str, ...] = (
    "# ",
    "## Architecture",
    "## Services",
    "## Quick-Start",
    "## Key Endpoints / Commands",
    "## CoDocs",
    "## Testing",
    "## Integration",
)

TOOL_NAME = "sckg"


def _read_agents_md() -> str:
    assert AGENTS_MD.exists(), f"AGENTS.md not found at {AGENTS_MD}"
    return AGENTS_MD.read_text(encoding="utf-8")


@pytest.mark.parametrize("section", MANDATORY_SECTIONS)
def test_agents_md_has_section(section: str) -> None:
    text = _read_agents_md()
    if section == "# ":
        assert re.search(r"^# .+", text, re.MULTILINE), (
            f"{TOOL_NAME}: AGENTS.md must have an H1 title (e.g. '# SIN-Code-<X>-Tool — …')"
        )
    else:
        assert section in text, (
            f"{TOOL_NAME}: AGENTS.md missing mandatory section: {section!r}"
        )


def test_agents_md_is_markdown() -> None:
    text = _read_agents_md()
    line_count = len(text.splitlines())
    assert line_count >= 60, (
        f"{TOOL_NAME}: AGENTS.md too short ({line_count} lines); "
        "expected ≥ 60 lines (standard template floor)"
    )


def test_agents_md_preserves_gitnexus_block_if_present() -> None:
    text = _read_agents_md()
    if "<!-- gitnexus:start -->" in text:
        assert "<!-- gitnexus:end -->" in text, (
            f"{TOOL_NAME}: AGENTS.md has gitnexus:start but no gitnexus:end — "
            "GitNexus index is broken. Either remove BOTH markers or add the end marker."
        )
