"""Append-only decision ledger.

`append` never rewrites an earlier entry. The showcase scripts may stage a
fresh header before a demo; that helper is not part of the entrypoint.
"""

from __future__ import annotations

from pathlib import Path

from boardroom.dates import format_et
from boardroom.models import Session

HEADER = (
    "# Decision Ledger\n"
    "\n"
    "Append-only record of NAS Boardroom verdicts. Older entries are not rewritten.\n"
    'The NAS can answer "why did you do that?" from this file.\n'
)


class LedgerError(Exception):
    """The receipt could not be appended without risking the existing record."""


def stage_showcase(path: str | Path) -> None:
    """Replace a showcase ledger with the header only.

    `boardroom.ledger.append` does not call this. Demo scripts do, so a
    fresh `./demo.sh` shows three sessions and nothing older.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(HEADER, encoding="utf-8", newline="\n")


def append(session: Session, path: str | Path) -> str:
    """Append one receipt. Return the docket id.

    If this docket is already in the file, raise LedgerError and write nothing.
    """
    destination = Path(path)
    if destination.exists() and destination.is_dir():
        raise LedgerError(f"{destination} is a directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
    if session.docket in existing:
        raise LedgerError(f"{session.docket} is already in the ledger")
    entry = render_entry(session)
    with destination.open("a", encoding="utf-8", newline="\n") as handle:
        if not existing:
            handle.write(HEADER)
        elif not existing.endswith("\n"):
            handle.write("\n")
        handle.write(entry)
    return session.docket


def render_entry(session: Session) -> str:
    verdict = session.verdict
    lines = [
        "",
        f"## {session.docket}",
        "",
        f"- **When:** {format_et(session.opened_at)}",
        f"- **Calendar:** {session.today.isoformat()}",
        f"- **Question:** {_cell(session.request)}",
        f"- **Framing:** {_cell(session.framing)}",
        f"- **Volume:** {_cell(session.nas_root)}",
        f"- **Mode:** {_cell(session.mode)}",
        f"- **Verdict:** {verdict.outcome.upper()}",
        f"- **Headline:** {_cell(verdict.headline)}",
        "- **Files changed:** none",
        "",
        "### Why",
        "",
        verdict.reasoning,
        "",
        "### Votes",
        "",
        "| Seat | Position | Confidence | Because |",
        "| --- | --- | --- | --- |",
    ]
    for vote in session.votes:
        lines.append(
            f"| {vote.seat.title()} | {vote.position.upper()} | {vote.confidence:.2f} | {_cell(vote.because)} |"
        )
    lines.extend(["", "### Actions", ""])
    for action in verdict.actions:
        lines.append(f"- {_cell(action)}")
    lines.extend(["", "### Constraints", ""])
    for item in verdict.constraints:
        lines.append(f"- {_cell(item)}")
    lines.extend(["", "### Evidence", ""])
    if session.exhibits:
        for item in session.exhibits:
            lines.append(f"- {_cell(item)}")
    else:
        lines.append("- none entered")
    lines.append("")
    return "\n".join(lines)


def _cell(text: str) -> str:
    return " ".join(text.replace("|", "/").split())
