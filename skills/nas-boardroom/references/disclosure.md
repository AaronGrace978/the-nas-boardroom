# Disclosure

This note is excluded from the proposal word limit. It travels with the skill package.

## What was written for this hackathon

The NAS Boardroom skill, its five-seat workflow, the veto rule, and the decision-ledger format are original work for UGREEN Hackathon 2026, Round 1. The skill is not an official UGREEN product and does not speak for UGREEN.

## Runtime on a UGREEN NAS

The skill package is Markdown. It calls Uliya's own experts:

- File management assistant, for search, hashes, and duplicate sets
- Document assistant, for reading and answering
- Photo assistant, when an exhibit is a photo
- Knowledge assistant, for saving the ledger text

No third-party library is shipped in this package. No cloud API is called. A finalist build may use the AI NAS local model only to phrase a speech. The vote is the veto rule plus the seats' positions, not the model's preference.

## Laptop prototype, outside this package

The parent repository contains a Python 3.10 prototype that mirrors `boardroom.convene`, `boardroom.verdict`, and `boardroom.ledger` on a plain computer. It is not part of the skill ZIP.

- Python standard library, PSF License. Hashes, dates, argument parsing, and the ledger append.
- pytest, MIT License, used only to run tests. It is not imported when the board convenes.
- Ollama, MIT License, optional. The prototype calls `http://127.0.0.1:11434` only, with proxies disabled, and only to rephrase a speech. Any other host is ignored. If nothing answers, the heuristic speeches are used. Source: https://github.com/ollama/ollama

## AI tools used to draft

Cursor's coding agent (Grok) was used to draft this repository, the skill text, and the tests. That agent is not called when the skill or the prototype runs.
