"""Render a session as minutes a person can read aloud."""

from __future__ import annotations

import textwrap

from boardroom.dates import format_et
from boardroom.models import Session, Speech, Vote

_WIDTH = 72
_SEAT_LABEL = {
    "archivist": "Archivist",
    "analyst": "Analyst",
    "auditor": "Auditor",
    "scout": "Scout",
}


def render(session: Session) -> str:
    rule = "=" * _WIDTH
    thin = "-" * _WIDTH
    lines = [
        rule,
        "THE NAS BOARDROOM",
        thin,
        f"Docket    {session.docket}",
        f"When      {format_et(session.opened_at)}",
        f"Calendar  {session.today.isoformat()}",
        f"Volume    {session.nas_root}",
        f"Mode      {session.mode}",
        thin,
        textwrap.fill(
            session.request,
            width=_WIDTH,
            initial_indent="Question  ",
            subsequent_indent="          ",
            break_long_words=False,
            break_on_hyphens=False,
        ),
        "",
    ]
    for speech in session.speeches:
        lines.append(_speech(speech))
        lines.append("")
        if speech.seat == "chair":
            lines.append("EXHIBITS")
            if session.exhibits:
                for item in session.exhibits:
                    lines.append(_wrap(item, initial="  - ", subsequent="    "))
            else:
                lines.append("  - none entered")
            lines.append("")
            continue
        if speech.vote is not None:
            lines.extend(_vote_lines(speech.vote))
            lines.append("")
    lines.append("THE VOTE")
    lines.append(_table(session.votes))
    lines.append("")
    lines.append(_wrap(session.verdict.vote_note, initial="  ", subsequent="  "))
    lines.append("")
    lines.append(f"VERDICT  {session.verdict.outcome.upper()}")
    lines.append(_wrap(session.verdict.headline, initial="  ", subsequent="  "))
    lines.append("")
    lines.append(_wrap(session.verdict.reasoning, initial="  ", subsequent="  "))
    lines.append("")
    lines.append("  Actions")
    for action in session.verdict.actions:
        lines.append(_wrap(action, initial="  - ", subsequent="    "))
    lines.append("")
    lines.append("  Constraints")
    for item in session.verdict.constraints:
        lines.append(_wrap(item, initial="  - ", subsequent="    "))
    lines.append(rule)
    return "\n".join(lines) + "\n"


def _speech(speech: Speech) -> str:
    parts = [speech.name]
    for paragraph in speech.paragraphs:
        parts.append(_wrap(paragraph, initial="  ", subsequent="  "))
        parts.append("")
    return "\n".join(parts).rstrip()


def _vote_lines(vote: Vote) -> list[str]:
    return [
        f"  Vote        {vote.position.upper()}",
        f"  Confidence  {vote.confidence:.2f}",
        _wrap(vote.because, initial="  Because     ", subsequent="              "),
    ]


def _table(votes: list[Vote]) -> str:
    rows = [
        "  Seat        Position   Confidence",
        "  ----------  ---------  ----------",
    ]
    for vote in votes:
        label = _SEAT_LABEL.get(vote.seat, vote.seat.title())
        rows.append(f"  {label:<10}  {vote.position.upper():<9}  {vote.confidence:.2f}")
    return "\n".join(rows)


def _wrap(text: str, *, initial: str = "", subsequent: str | None = None) -> str:
    return textwrap.fill(
        " ".join(text.split()),
        width=_WIDTH,
        initial_indent=initial,
        subsequent_indent=initial if subsequent is None else subsequent,
        break_long_words=False,
        break_on_hyphens=False,
    )
