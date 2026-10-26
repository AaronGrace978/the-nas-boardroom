"""Command line. `python -m boardroom \"...\"` convenes, prints, and appends."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from boardroom.ledger import LedgerError, append
from boardroom.session import convene
from boardroom.transcript import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m boardroom",
        description="Convene the NAS Boardroom on a local folder. Nothing is uploaded.",
    )
    parser.add_argument("request", help="The question to put before the board")
    parser.add_argument(
        "--nas",
        default=os.environ.get("BOARDROOM_NAS", "demo-nas"),
        help="Authorized folder (default: demo-nas or BOARDROOM_NAS)",
    )
    parser.add_argument(
        "--ledger",
        default=os.environ.get("BOARDROOM_LEDGER", "ledger/DECISIONS.md"),
        help="Append-only ledger path (default: ledger/DECISIONS.md)",
    )
    parser.add_argument(
        "--today",
        help="ISO date the board uses for 'last quarter' (default: the clock's Eastern Time date)",
    )
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "llama3.2"))
    parser.add_argument(
        "--host",
        default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        help="Loopback Ollama URL. Any other host is ignored.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--no-llm", action="store_true", help="Heuristic speeches only")
    mode.add_argument("--llm", action="store_true", help="Phrase speeches with a local model if it answers")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    llm: bool | None
    if args.no_llm or os.environ.get("BOARDROOM_NO_LLM") == "1":
        llm = False
    elif args.llm:
        llm = True
    else:
        llm = None

    try:
        calendar_day = date.fromisoformat(args.today) if args.today else None
    except ValueError:
        parser.error("--today must be YYYY-MM-DD")
        return 2

    try:
        session = convene(
            args.request,
            nas_root=args.nas,
            today=calendar_day,
            llm=llm,
            model=args.model,
            host=args.host,
        )
    except ValueError as exc:
        print(f"The board did not convene: {exc}", file=sys.stderr)
        return 2

    print(render(session), end="")
    try:
        docket = append(session, Path(args.ledger))
    except (LedgerError, OSError) as exc:
        print(f"Ledger    not recorded ({exc})", file=sys.stderr)
        return 3
    print(f"Ledger    {args.ledger}  # {docket}")
    if session.verdict.outcome == "unable":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
