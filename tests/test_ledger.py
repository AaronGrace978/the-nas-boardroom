"""The ledger grows by appending. Earlier bytes stay put."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from boardroom.dates import ET
from boardroom.ledger import HEADER, LedgerError, append, render_entry
from boardroom.session import convene

TODAY = date(2026, 10, 26)


def _session(nas: Path, request: str, stamp: datetime):
    return convene(request, nas_root=nas, today=TODAY, now=stamp, llm=False)


def test_append_creates_a_header_then_only_adds(nas: Path, tmp_path: Path) -> None:
    ledger = tmp_path / "notes" / "DECISIONS.md"
    first = _session(nas, "find duplicate photos and propose cleanup", datetime(2026, 10, 26, 14, 0, tzinfo=ET))
    second = _session(nas, "what did I sign last quarter?", datetime(2026, 10, 26, 14, 1, tzinfo=ET))

    append(first, ledger)
    after_first = ledger.read_bytes()
    assert after_first.startswith(HEADER.encode("utf-8"))
    assert after_first.count(b"## BRD-") == 1
    assert b"find duplicate photos and propose cleanup" in after_first
    assert b"PROPOSED" in after_first

    append(second, ledger)
    after_second = ledger.read_bytes()
    assert after_second.startswith(after_first)
    assert after_second.count(b"# Decision Ledger") == 1
    assert after_second.count(b"## BRD-") == 2
    assert b"what did I sign last quarter?" in after_second
    assert b"ANSWERED" in after_second


def test_a_second_copy_of_the_same_docket_is_refused(nas: Path, tmp_path: Path) -> None:
    ledger = tmp_path / "DECISIONS.md"
    session = _session(nas, "find duplicate photos and propose cleanup", datetime(2026, 10, 26, 15, 0, tzinfo=ET))
    append(session, ledger)
    before = ledger.read_bytes()
    with pytest.raises(LedgerError):
        append(session, ledger)
    assert ledger.read_bytes() == before


def test_entry_carries_the_vote_and_the_evidence(nas: Path) -> None:
    session = _session(
        nas,
        "delete all files in Documents/Contracts, including the signed originals",
        datetime(2026, 10, 26, 16, 0, tzinfo=ET),
    )
    entry = render_entry(session)
    assert f"## {session.docket}" in entry
    assert "BLOCKED" in entry
    assert "Files changed:** none" in entry
    assert "Auditor" in entry
    assert "0.97" in entry
    assert "Documents/Contracts/2026-08-14-vendor-agreement-SIGNED.txt" in entry


def test_append_refuses_a_directory(nas: Path, tmp_path: Path) -> None:
    session = _session(nas, "find duplicate photos and propose cleanup", datetime(2026, 10, 26, 17, 0, tzinfo=ET))
    with pytest.raises(LedgerError):
        append(session, tmp_path)
