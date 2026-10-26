# Proposal draft — The NAS Boardroom

Draft for the Round 1 PDF. The ten answers are the substantive response and stay within 500 words. Wording is still open. The disclosure under the line is outside that count.

## 1. What does the Skill do?

It convenes five on-device experts to deliberate a NAS request, vote with confidence, and file a verdict the owner can read later.

## 2. Who is the target user and problem?

Household and small-studio owners of a UGREEN AI NAS. One assistant will dedupe, answer, or delete, and a week later nobody can see which files counted as copies or why a delete was allowed.

## 3. What is your proposed solution?

The Chair frames the request and calls four seats. The Archivist covers files, hashes, and duplicates. The Analyst reads the documents or photos in scope. The Auditor applies the retention note. The Scout checks newer copies and cited paths that are missing. Each seat votes. The Chair publishes the verdict.

## 4. What is the Core User Flow?

The owner asks in plain language. The Archivist returns real paths and hashes. The Analyst reads only those paths. The Auditor reads the retention note and may veto a delete. The Scout adds gaps. The transcript shows every speech and vote. `boardroom.ledger` appends a markdown receipt. Nothing is moved or deleted.

## 5. What substantive difference does your idea offer?

Typical tools return one unreviewed answer and may act at once. This skill separates duties, records dissent, and keeps an append-only ledger, so the NAS can answer "why did you do that?" A model may phrase a speech. It does not cast votes. No cloud service is on the path.

## 6. Which UGREEN AI NAS capabilities will be used, and at which step?

File search and duplicate detection: Archivist. Document read, question answering, and photo identification: Analyst, on those paths only. Retention-note read: Auditor, before any organize step. File search for cited paths and same-named copies: Scout. Knowledge save-text: the ledger, only after previous entries are read back. A move waits for a later confirmed request.

## 7. What was your technical approach?

The skill is Markdown orchestration for Uliya. Experts do not share memory, so each step repeats the prior paths. Entrypoints are `boardroom.convene`, `boardroom.verdict`, and `boardroom.ledger`. Permissions are read on files, documents, and photos, plus save-text for the ledger. Delete is not requested. An Auditor block at 0.70 or higher vetoes a destructive request. The Python 3.10 laptop prototype uses the standard library, with optional loopback Ollama phrasing and a heuristic fallback.

## 8. What is the current development status?

Built: the five-seat loop, tally, veto, transcript, append-only ledger, and a laptop demo for duplicate cleanup, last-quarter signatures, and a blocked delete. Not built: Uliya installation, live expert calls, and a confirmed move. Still to test on a NAS: expert handoff, permission prompts, and the ledger write.

## 9. What is your final validation plan?

Core: duplicate photos yield one keeper, matching hashes, and a ledger that lists every path without deleting. Core: "what did I sign last quarter?" cites only that quarter. Edge: deleting signed contracts is blocked, the files remain, and the veto is in the ledger.

## 10. Are there any known limitations of your Project?

Duplicates are exact hashes, not lookalike photos. Quarter answers depend on dates written in the files. The veto is a skill rule, not a firmware lock. On device, save-text may rewrite the ledger; the skill refuses to save if earlier entries are missing. The laptop append is the stand-in. It depends on the UGOS file, document, photo, and knowledge experts.

---

## Disclosure (outside the word limit)

See [skills/nas-boardroom/references/disclosure.md](skills/nas-boardroom/references/disclosure.md). Python standard library (PSF License) runs the laptop prototype. pytest (MIT) runs tests only. Ollama (MIT) is optional, loopback only, speech phrasing only. Cursor's coding agent drafted the repository and is not on the runtime path. No cloud service is called.
