"""The skill package the Round 1 ZIP is cut from."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills" / "nas-boardroom"


def _frontmatter(text: str) -> str:
    assert text.startswith("---\n")
    end = text.index("\n---\n", 3)
    return text[4:end]


def test_manifest_has_the_required_fields() -> None:
    text = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
    front = _frontmatter(text)
    assert "name: nas-boardroom" in front
    assert 'version: "0.1.0"' in front
    description = re.search(r'^description: "(.*)"$', front, re.MULTILINE)
    assert description is not None
    assert 1 <= len(description.group(1)) <= 1024
    for permission in ("files.read", "documents.read", "photos.read", "knowledge.save_text"):
        assert permission in front
    assert "files.delete" not in front
    for entry in ("boardroom.convene", "boardroom.verdict", "boardroom.ledger"):
        assert entry in text


def test_reference_links_resolve() -> None:
    text = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
    for name in ("references/ledger.md", "references/disclosure.md"):
        assert name in text
        assert (PACKAGE / name).is_file()
