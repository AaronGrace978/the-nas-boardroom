# Decision ledger

The ledger is an append-only Markdown file. The default path on the NAS is `Boardroom/DECISIONS.md`, inside the folder the owner authorized. Each session adds one heading. Older headings stay as they were written.

## Header

The file starts with this header, and only when the file is absent:

```markdown
# Decision Ledger

Append-only record of NAS Boardroom verdicts. Older entries are not rewritten.
The NAS can answer "why did you do that?" from this file.
```

## One entry

```markdown
## BRD-YYYYMMDD-HHMMSS-hhhh

- **When:** 2026-10-26 2:30 PM ET
- **Calendar:** 2026-10-26
- **Question:** the owner's sentence
- **Framing:** duplicate-cleanup proposal, document question, or destructive request
- **Volume:** the authorized folder
- **Mode:** heuristic, or the local model that phrased speeches
- **Verdict:** PROPOSED, ANSWERED, BLOCKED, NO-FINDING, or UNABLE
- **Headline:** one sentence
- **Files changed:** none

### Why

The Chair's reasoning, including the tally.

### Votes

| Seat | Position | Confidence | Because |
| --- | --- | --- | --- |
| Archivist | APPROVE | 0.92 | one line |

### Actions

- What the board recommends. Empty of file changes in this skill.

### Constraints

- No file was moved, renamed, or deleted.

### Evidence

- Paths, hashes, dates, and missing citations actually returned by earlier steps.
```

`hhhh` is a short hash of the question, so two different questions in the same second do not share a docket id.

## How to save it on UGOS

The Knowledge assistant saves text. It may rewrite the file rather than append at the filesystem level. The safe sequence is:

1. Read `Boardroom/DECISIONS.md`.
2. If the read fails, stop. Tell the owner the verdict was not recorded. Do not create a replacement.
3. If the file is absent, start from the header above.
4. If the new docket id is already a heading, stop.
5. Save the previous text plus the new entry. Before saving, check that every old `## BRD-` heading is still in the text you are about to write.

The laptop prototype writes with a true append. That is the behavior this format describes. On a NAS, the read-then-save sequence above is how the same format stays honest with the save-text capability.
