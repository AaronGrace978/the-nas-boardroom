"""The five seats speak in order, and the three showcase requests resolve."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

import boardroom
from boardroom.intent import classify
from boardroom.llm import phrase
from boardroom.session import convene
from boardroom.transcript import render

TODAY = date(2026, 10, 26)
ROOT = Path(__file__).resolve().parents[1]


def _flat(text: str) -> str:
    return " ".join(text.split())


def _tree(root: Path) -> list[tuple[str, bytes]]:
    items = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        items.append((path.relative_to(root).as_posix(), path.read_bytes()))
    return items


def test_public_entrypoints_exist() -> None:
    assert callable(boardroom.convene)
    assert callable(boardroom.verdict)
    assert callable(boardroom.ledger.append)


def test_classification() -> None:
    assert classify("find duplicate photos and propose cleanup") == "duplicate"
    assert classify("remove duplicate photos") == "duplicate"
    assert classify("what did I sign last quarter?") == "question"
    assert classify("delete all files in Documents/Contracts, including the signed originals") == "delete"
    assert classify("how full is the shelf") == "review"


def test_seats_speak_in_order(nas: Path) -> None:
    session = convene(
        "find duplicate photos and propose cleanup",
        nas_root=nas,
        today=TODAY,
        llm=False,
    )
    text = render(session)
    names = ["THE CHAIR", "THE ARCHIVIST", "THE ANALYST", "THE AUDITOR", "THE SCOUT", "THE VOTE", "VERDICT"]
    positions = [text.index(name) for name in names]
    assert positions == sorted(positions)
    assert [speech.seat for speech in session.speeches] == [
        "chair",
        "archivist",
        "analyst",
        "auditor",
        "scout",
    ]
    assert session.speeches[0].vote is None
    assert boardroom.verdict(session).headline == session.verdict.headline
    assert session.verdict.mutated is False
    assert session.mode.startswith("heuristic")


def test_duplicate_proposal_names_a_keeper_and_changes_nothing(nas: Path) -> None:
    before = _tree(nas)
    session = convene(
        "find duplicate photos and propose cleanup",
        nas_root=nas,
        today=TODAY,
        llm=False,
    )
    assert _tree(nas) == before
    assert session.verdict.outcome == "proposed"
    assert session.verdict.veto is False
    group = session.findings.groups[0]
    assert group.keeper.rel_path == "Photos/2026/beach-sunset.jpg"
    assert {copy.rel_path for copy in group.copies} == {
        "Photos/2026/beach-sunset (1).jpg",
        "Downloads/beach-sunset-copy.jpg",
    }
    assert "Photos/2026/kitchen-table.jpg" not in {item.rel_path for item in group.members}
    assert any(item.rel_path == "Archive/beach-sunset-v1.jpg" for item in session.findings.namesakes)
    text = _flat(render(session))
    assert "Photos/2026/beach-sunset.jpg" in text
    assert "beach-sunset (1).jpg" in text
    assert "Downloads/beach-sunset-copy.jpg" in text
    assert "Archive/beach-sunset-v1.jpg" in text
    assert "2026-09-15" in text
    assert "Harbor Supply" not in text
    assert "Avery Chen" not in text
    assert "Nothing was moved or deleted" in text
    assert all(not path.endswith(".txt") for path in session.findings.reads if "retention" not in path)


def test_last_quarter_answers_with_the_two_q3_signatures(nas: Path) -> None:
    session = convene("what did I sign last quarter?", nas_root=nas, today=TODAY, llm=False)
    assert session.verdict.outcome == "answered"
    hits = [doc.rel_path for doc in session.findings.signed_hits]
    assert hits == [
        "Documents/Contracts/2026-08-14-vendor-agreement-SIGNED.txt",
        "Documents/Contracts/2026-09-02-photo-release-SIGNED.txt",
    ]
    outside = {doc.rel_path for doc in session.findings.signed_outside}
    assert "Documents/Contracts/2026-05-03-lease-addendum-SIGNED.txt" in outside
    assert "Documents/Contracts/2026-10-02-workshop-release-SIGNED.txt" in outside
    text = _flat(render(session))
    assert "Q3 2026" in text
    assert "2026-07-01" in text
    assert "2026-09-30" in text
    assert "Avery Chen" in text
    assert "Harbor Supply" in text
    assert "exhibit-b-schedule.pdf" in text
    assert "not the answer" in text
    assert "2026-09-12-quarterly-review.m4a" not in text
    reads = set(session.findings.reads)
    assert "Documents/Finance/2026-Q3-hosting-invoice.txt" not in reads
    assert "Documents/Notes/2026-09-12-quarterly-review.txt" not in reads
    assert "Policies/retention.md" in reads
    assert not any(path.endswith(".jpg") for path in reads)


def test_empty_quarter_does_not_borrow_a_neighbor(nas: Path) -> None:
    session = convene(
        "what did I sign last quarter?",
        nas_root=nas,
        today=date(2026, 4, 15),
        llm=False,
    )
    assert session.verdict.outcome == "no-finding"
    assert session.findings.quarter_label == "Q1 2026"
    assert session.findings.signed_hits == ()
    assert "2026-05-03" not in session.verdict.headline
    assert "substitute" in _flat(render(session)).lower() or "fill the gap" in _flat(render(session))


def test_risky_delete_is_blocked_and_the_files_remain(nas: Path) -> None:
    before = _tree(nas)
    request = "delete all files in Documents/Contracts, including the signed originals"
    session = convene(request, nas_root=nas, today=TODAY, llm=False)
    assert session.verdict.outcome == "blocked"
    assert session.verdict.veto is True
    auditor = next(vote for vote in session.votes if vote.seat == "auditor")
    assert auditor.position == "block"
    assert auditor.confidence >= 0.70
    assert _tree(nas) == before
    text = _flat(render(session))
    assert "retain 7 years" in text
    assert "Documents/Contracts/2026-08-14-vendor-agreement-SIGNED.txt" in text
    assert "exhibit-b-schedule.pdf" in text
    assert (nas / "Documents/Contracts/2026-08-14-vendor-agreement-SIGNED.txt").is_file()


def test_confirmation_does_not_lift_a_retention_block(nas: Path) -> None:
    session = convene(
        "I confirm delete all files in Documents/Contracts, including the signed originals",
        nas_root=nas,
        today=TODAY,
        llm=False,
    )
    assert session.verdict.outcome == "blocked"
    assert session.verdict.veto is True
    assert session.verdict.mutated is False


def test_missing_volume_is_recorded_as_unable(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-volume"
    session = convene("find duplicate photos and propose cleanup", nas_root=missing, today=TODAY, llm=False)
    assert session.verdict.outcome == "unable"
    assert "did not guess" in session.verdict.headline
    assert session.findings.file_count == 0


def test_symlink_outside_the_volume_is_ignored(nas: Path, tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text(
        "SECRET MEMO\nStatus: SIGNED\nSigned on: August 1, 2026\nSignatory: Hidden Person\n",
        encoding="utf-8",
    )
    link = nas / "Documents" / "secret.txt"
    link.symlink_to(secret)
    session = convene("what did I sign last quarter?", nas_root=nas, today=TODAY, llm=False)
    assert "Hidden Person" not in _flat(render(session))
    assert all("secret.txt" not in path for path in session.findings.reads)


def test_remote_model_host_is_refused() -> None:
    assert phrase("THE ARCHIVIST", "Keep Photos/a.jpg", model="llama3.2", host="https://example.com") is None


def test_silent_local_model_falls_back(nas: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("boardroom.session.probe", lambda host: False)
    session = convene(
        "find duplicate photos and propose cleanup",
        nas_root=nas,
        today=TODAY,
        llm=True,
        host="http://127.0.0.1:11434",
    )
    assert "heuristic" in session.mode
    assert session.verdict.outcome == "proposed"


def test_cli_prints_the_transcript_and_appends(nas: Path, tmp_path: Path) -> None:
    ledger = tmp_path / "DECISIONS.md"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["BOARDROOM_NO_LLM"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "boardroom",
            "--nas",
            str(nas),
            "--ledger",
            str(ledger),
            "--no-llm",
            "--today",
            "2026-10-26",
            "find duplicate photos and propose cleanup",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "THE ARCHIVIST" in completed.stdout
    assert "THE VOTE" in completed.stdout
    assert "VERDICT" in completed.stdout
    assert "PROPOSED" in completed.stdout
    assert ledger.is_file()
    recorded = ledger.read_text(encoding="utf-8")
    assert "find duplicate photos and propose cleanup" in recorded
    assert "## BRD-" in recorded


def test_cli_missing_volume_exits_2(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "boardroom",
            "--nas",
            str(tmp_path / "missing"),
            "--ledger",
            str(tmp_path / "DECISIONS.md"),
            "--no-llm",
            "--today",
            "2026-10-26",
            "what did I sign last quarter?",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "VERDICT  UNABLE" in completed.stdout
    assert "UNABLE" in (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
