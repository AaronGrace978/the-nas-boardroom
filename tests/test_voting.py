"""Voting rules: plurality, caution on a tie, and the Auditor's veto."""

from __future__ import annotations

import pytest

from boardroom.models import Vote
from boardroom.tally import VETO_LINE, auditor_vetoes, outcome_for, plurality


def _vote(seat: str, position: str, confidence: float, because: str = "because") -> Vote:
    return Vote(seat, position, confidence, because)  # type: ignore[arg-type]


def _ballots(auditor_position: str, auditor_confidence: float) -> list[Vote]:
    return [
        _vote("archivist", "approve", 0.99),
        _vote("analyst", "approve", 0.99),
        _vote("auditor", auditor_position, auditor_confidence),
        _vote("scout", "approve", 0.99),
    ]


def test_confidence_and_position_are_checked() -> None:
    with pytest.raises(ValueError):
        _vote("auditor", "block", 1.2)
    with pytest.raises(ValueError):
        _vote("auditor", "yes", 0.5)


def test_abstain_does_not_move_the_sum() -> None:
    votes = [
        _vote("archivist", "abstain", 0.9),
        _vote("analyst", "approve", 0.4),
        _vote("auditor", "abstain", 0.0),
        _vote("scout", "block", 0.4),
    ]
    assert plurality(votes) == "block"


def test_tie_breaks_toward_the_cautious_position() -> None:
    votes = [
        _vote("archivist", "approve", 0.50),
        _vote("analyst", "abstain", 0.0),
        _vote("auditor", "block", 0.50),
        _vote("scout", "abstain", 0.0),
    ]
    assert plurality(votes) == "block"


def test_veto_line_blocks_a_delete_even_when_the_others_approve() -> None:
    outcome, _winner, veto = outcome_for(
        _ballots("block", VETO_LINE),
        kind="delete",
        volume_missing=False,
        has_subject=True,
    )
    assert veto is True
    assert outcome == "blocked"


def test_just_under_the_veto_line_follows_the_plurality() -> None:
    outcome, winner, veto = outcome_for(
        _ballots("block", 0.69),
        kind="delete",
        volume_missing=False,
        has_subject=True,
    )
    assert veto is False
    assert winner == "approve"
    assert outcome == "proposed"


def test_veto_does_not_apply_to_a_duplicate_proposal() -> None:
    outcome, winner, veto = outcome_for(
        _ballots("block", 0.97),
        kind="duplicate",
        volume_missing=False,
        has_subject=True,
    )
    assert auditor_vetoes(_ballots("block", 0.97), kind="duplicate", has_subject=True) is False
    assert veto is False
    assert winner == "approve"
    assert outcome == "proposed"


def test_a_delete_with_no_target_is_a_no_finding_not_a_veto() -> None:
    outcome, _winner, veto = outcome_for(
        _ballots("block", 0.97),
        kind="delete",
        volume_missing=False,
        has_subject=False,
    )
    assert veto is False
    assert outcome == "no-finding"


def test_missing_volume_is_unable() -> None:
    outcome, winner, veto = outcome_for(
        _ballots("approve", 0.9),
        kind="duplicate",
        volume_missing=True,
        has_subject=False,
    )
    assert outcome == "unable"
    assert winner is None
    assert veto is False
