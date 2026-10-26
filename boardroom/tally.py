"""The Chair's arithmetic. A model does not get a ballot."""

from __future__ import annotations

from boardroom.models import Findings, Session, Verdict, Vote
from boardroom.phrasing import join_and

# An Auditor block at this confidence, or higher, vetoes a destructive request.
VETO_LINE = 0.70

_CAUTION = {"block": 0, "amend": 1, "approve": 2}


def hundredths(value: float) -> int:
    return int(round(value * 100))


def plurality(votes: list[Vote]) -> str | None:
    """Confidence-weighted plurality. Ties break toward block, then amend, then approve."""
    totals: dict[str, int] = {}
    for vote in votes:
        if vote.position == "abstain":
            continue
        totals[vote.position] = totals.get(vote.position, 0) + hundredths(vote.confidence)
    if not totals:
        return None
    return min(totals, key=lambda position: (-totals[position], _CAUTION[position]))


def auditor_vetoes(votes: list[Vote], *, kind: str, has_subject: bool) -> bool:
    if kind != "delete" or not has_subject:
        return False
    return any(
        vote.seat == "auditor"
        and vote.position == "block"
        and hundredths(vote.confidence) >= hundredths(VETO_LINE)
        for vote in votes
    )


def outcome_for(
    votes: list[Vote],
    *,
    kind: str,
    volume_missing: bool,
    has_subject: bool,
) -> tuple[str, str | None, bool]:
    """Return outcome, plurality, and whether the Auditor's veto fired."""
    if volume_missing:
        return "unable", None, False
    winner = plurality(votes)
    veto = auditor_vetoes(votes, kind=kind, has_subject=has_subject)
    if veto:
        return "blocked", winner, True
    if kind in {"duplicate", "question", "delete"} and not has_subject:
        return "no-finding", winner, False
    if winner is None:
        return "no-finding", None, False
    if winner == "block":
        return "blocked", winner, False
    if kind == "question":
        return "answered", winner, False
    if kind in {"duplicate", "delete"}:
        return "proposed", winner, False
    return "answered", winner, False


def decide(findings: Findings, votes: list[Vote]) -> Verdict:
    outcome, winner, veto = outcome_for(
        votes,
        kind=findings.kind,
        volume_missing=findings.volume_missing,
        has_subject=findings.has_subject,
    )
    return Verdict(
        outcome=outcome,  # type: ignore[arg-type]
        headline=_headline(findings, outcome),
        reasoning=_reasoning(findings, votes, outcome, winner, veto),
        actions=_actions(findings, outcome),
        constraints=_constraints(findings, votes, outcome),
        plurality=winner,
        veto=veto,
        vote_note=_vote_note(votes, outcome, winner, veto),
        mutated=False,
    )


def verdict(session: Session) -> Verdict:
    """Entrypoint `boardroom.verdict`. Recompute the Chair's verdict from the recorded votes."""
    return decide(session.findings, session.votes)


def _vote_note(votes: list[Vote], outcome: str, winner: str | None, veto: bool) -> str:
    auditor = next((vote for vote in votes if vote.seat == "auditor"), None)
    if veto and auditor is not None:
        return (
            f"Auditor veto sustained at {auditor.confidence:.2f} "
            f"(line is {VETO_LINE:.2f})."
        )
    if winner is None:
        return "No seat cast a counted vote."
    note = f"Plurality {winner.upper()}."
    if any(vote.position == "amend" for vote in votes) and outcome == "proposed":
        note += " The Auditor's amendment is binding: this session changes no files."
    return note


def _headline(findings: Findings, outcome: str) -> str:
    if outcome == "unable":
        return "The volume is not available. The board did not guess."
    if findings.kind == "duplicate" and outcome == "proposed":
        noun = "duplicate-photo cleanup" if findings.photo_only else "duplicate cleanup"
        return f"Propose a {noun}. Nothing was moved or deleted."
    if findings.kind == "duplicate" and outcome == "no-finding":
        return "No exact duplicates in scope. Nothing was nominated in their place."
    if findings.kind == "question" and outcome == "answered":
        count = len(findings.signed_hits)
        noun = "document" if count == 1 else "documents"
        if findings.quarter_label:
            return f"{count} {noun} signed in {findings.quarter_label}."
        return f"{count} signed {noun} match the question."
    if findings.kind == "question" and outcome == "no-finding":
        if findings.quarter_label:
            return f"No document on this volume was signed in {findings.quarter_label}."
        return "No signed document matched the question."
    if findings.kind == "delete" and outcome == "blocked":
        return "Blocked. The files stay where they are."
    if findings.kind == "delete" and outcome == "no-finding":
        return "No matching path. The delete was not widened."
    if findings.kind == "delete" and outcome == "proposed":
        return "Recorded as a proposal. Nothing was deleted."
    if outcome == "blocked":
        return "Blocked. No file was changed."
    return "Noted. The board took no action."


def _actions(findings: Findings, outcome: str) -> tuple[str, ...]:
    if findings.volume_missing:
        return ("Do not invent an inventory.",)
    if outcome == "no-finding" and findings.kind == "duplicate":
        return ("Tell the owner no exact duplicates were found, and stop.",)
    if outcome == "no-finding" and findings.kind == "question":
        return ("Tell the owner nothing in range was signed, and do not offer a file from another period.",)
    if outcome == "no-finding" and findings.kind == "delete":
        return ("Tell the owner no path matched, and do not widen the delete.",)
    if outcome == "blocked":
        return ("Leave every file where it is.",)
    if findings.kind == "duplicate" and outcome == "proposed":
        lines: list[str] = []
        for group in findings.groups:
            lines.append(f"Keep {group.keeper.rel_path} (hash {group.short_hash}).")
            for copy in group.copies:
                lines.append(f"Hold {copy.rel_path} for confirmation. Do not delete it.")
        return tuple(lines)
    if findings.kind == "question" and outcome == "answered":
        return tuple(
            f"Cite {doc.rel_path}, signed {doc.signed_on.isoformat()} by {doc.signatory}."
            for doc in findings.signed_hits
            if doc.signed_on is not None
        )
    if findings.kind == "delete" and outcome == "proposed":
        return tuple(
            f"Record a proposal for {target.rel_path}. Do not delete it in this session."
            for target in findings.targets
        )
    return ("No action.",)


def _constraints(findings: Findings, votes: list[Vote], outcome: str) -> tuple[str, ...]:
    lines = ["No file was moved, renamed, or deleted."]
    if findings.kind == "duplicate" and outcome == "proposed":
        lines.append("A later session may move a copy only after the owner confirms that exact path.")
    if findings.kind == "delete" and outcome == "blocked":
        lines.append("The Auditor's veto is sustained. A confirmation phrase does not override retention.")
    if findings.kind == "question":
        lines.append("Keep documents signed outside the asked period out of the answer.")
        if findings.missing_refs:
            lines.append("Name missing citations. Do not invent their contents.")
    if any(vote.position == "amend" for vote in votes) and outcome == "proposed":
        lines.append("Amendments from the seats are part of the verdict.")
    return tuple(lines)


def _reasoning(
    findings: Findings,
    votes: list[Vote],
    outcome: str,
    winner: str | None,
    veto: bool,
) -> str:
    tally = _tally_phrase(votes)
    auditor = next((vote for vote in votes if vote.seat == "auditor"), None)
    if outcome == "unable":
        return (
            "The volume path is not a directory the Archivist can read. "
            "The board will not invent files in its place. "
            f"Tally: {tally}."
        )
    if findings.kind == "duplicate" and outcome == "proposed" and findings.groups:
        group = findings.groups[0]
        sentences = [
            f"The Archivist showed hash {group.short_hash} on {len(group.members)} files "
            f"and named {group.keeper.rel_path} as the keeper.",
            "The Analyst inspected that set and left the contracts closed.",
            "The Auditor amends a cleanup into a proposal. I adopt the amendment: nothing moves.",
        ]
        if findings.namesakes:
            sentences.append(
                f"The Scout kept {findings.namesakes[0].rel_path} out of the set, "
                "because the name matches and the bytes do not."
            )
        sentences.append(f"Tally: {tally}. Plurality {winner}.")
        return " ".join(sentences)
    if findings.kind == "duplicate" and outcome == "no-finding":
        return (
            "The Archivist found no exact-hash duplicates in scope. "
            "I will not nominate a lookalike. "
            f"Tally: {tally}."
        )
    if findings.kind == "question" and outcome == "answered":
        cited = join_and([doc.rel_path for doc in findings.signed_hits])
        sentences = [f"The Analyst's answer is {cited}."]
        if findings.quarter_label and findings.quarter_start and findings.quarter_end:
            sentences.insert(
                0,
                f"For a board using calendar date {findings.today.isoformat()}, last quarter is "
                f"{findings.quarter_label} ({findings.quarter_start.isoformat()} through "
                f"{findings.quarter_end.isoformat()}).",
            )
        if findings.signed_outside:
            sentences.append("Files signed outside that window were read only so they could be excluded.")
        if findings.missing_refs:
            missing = join_and(ref.cited for ref in findings.missing_refs)
            sentences.append(f"The Scout reports {missing} cited and absent. I will not guess what it says.")
        sentences.append(f"Tally: {tally}.")
        return " ".join(sentences)
    if findings.kind == "question" and outcome == "no-finding":
        return (
            "The Analyst read the signed documents and found none in range. "
            "I will not stretch the period to include a neighboring contract. "
            f"Tally: {tally}."
        )
    if findings.kind == "delete" and outcome == "blocked" and veto and auditor is not None:
        return (
            f"The Auditor votes block at {auditor.confidence:.2f}. "
            f"The veto line is {VETO_LINE:.2f}. I sustain it. "
            "The targets include material the retention rule keeps, or an unconfirmed delete. "
            "The Archivist and the Scout spoke to last copies and broken citations. "
            "No file was deleted. "
            f"Tally: {tally}."
        )
    if outcome == "blocked":
        return f"The plurality is block. I sustain it. No file was changed. Tally: {tally}."
    if findings.kind == "delete" and outcome == "proposed":
        return (
            "The veto line was not met. I record a proposal and stop. Nothing was deleted. "
            f"Tally: {tally}."
        )
    if findings.kind == "delete" and outcome == "no-finding":
        return (
            "No path in the request matches a file on the volume. "
            "I will not widen the delete. "
            f"Tally: {tally}."
        )
    return f"The board reviewed the volume and took no action. Tally: {tally}."


def _tally_phrase(votes: list[Vote]) -> str:
    if not votes:
        return "no votes"
    return ", ".join(
        f"{vote.seat} {vote.position} {vote.confidence:.2f}" for vote in votes
    )
