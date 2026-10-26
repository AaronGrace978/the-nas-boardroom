"""Convene the board. This is the `boardroom.convene` entrypoint."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path

from boardroom.dates import clock
from boardroom.deliberate import FRAMING, exhibits_for, speeches_for
from boardroom.findings import build_findings
from boardroom.llm import phrase, probe, resolve_host
from boardroom.models import Session, Speech
from boardroom.tally import decide


def convene(
    request: str,
    *,
    nas_root: str | Path,
    today: date | None = None,
    now: datetime | None = None,
    llm: bool | None = None,
    model: str = "llama3.2",
    host: str = "http://127.0.0.1:11434",
) -> Session:
    """Run one deliberation and attach the Chair's verdict.

    Does not write the ledger and does not change files on the volume.
    `llm=None` probes loopback Ollama and falls back to the heuristic seats.
    `llm=False` skips the probe. Votes are rules in every mode.
    """
    question = " ".join(request.split())
    if not question:
        raise ValueError("the board needs a question")
    opened = clock(now)
    calendar_day = today or opened.date()
    findings = build_findings(question, nas_root, calendar_day)
    drafted = speeches_for(findings)
    speeches, mode = _maybe_phrase(drafted, llm=llm, model=model, host=host)
    decision = decide(findings, [speech.vote for speech in speeches if speech.vote is not None])
    return Session(
        docket=_docket(opened, question),
        request=question,
        kind=findings.kind,
        framing=FRAMING[findings.kind],
        nas_root=str(nas_root),
        opened_at=opened,
        today=calendar_day,
        mode=mode,
        findings=findings,
        speeches=speeches,
        exhibits=exhibits_for(findings),
        verdict=decision,
    )


def _docket(moment: datetime, request: str) -> str:
    local = clock(moment)
    stamp = local.strftime("%Y%m%d-%H%M%S")
    digest = hashlib.sha256(request.encode("utf-8")).hexdigest()[:4]
    return f"BRD-{stamp}-{digest}"


def _maybe_phrase(
    speeches: tuple[Speech, ...],
    *,
    llm: bool | None,
    model: str,
    host: str,
) -> tuple[tuple[Speech, ...], str]:
    heuristic = "heuristic; votes are rules, not model output"
    if llm is False:
        return speeches, heuristic
    resolved = resolve_host(host)
    if not resolved or not probe(resolved):
        if llm is True:
            return speeches, "heuristic, local model silent; votes are rules, not model output"
        return speeches, heuristic
    used = False
    updated: list[Speech] = []
    for speech in speeches:
        if speech.seat == "chair":
            updated.append(speech)
            continue
        source = "\n\n".join(speech.paragraphs)
        rewritten = phrase(speech.name, source, model=model, host=resolved)
        if rewritten:
            updated.append(Speech(speech.seat, speech.name, (rewritten,), speech.vote))
            used = True
        else:
            updated.append(speech)
    if used:
        return tuple(updated), f"ollama:{model} phrased the speeches; votes are rules, not model output"
    return speeches, "heuristic, local model silent; votes are rules, not model output"
