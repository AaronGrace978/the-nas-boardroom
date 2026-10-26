---
name: nas-boardroom
version: "0.1.0"
description: "Five on-device experts deliberate a UGREEN NAS request, vote with confidence, and append the Chair's verdict to a decision ledger. The Archivist, Analyst, Auditor, and Scout speak in turn. Duplicate cleanup is a proposal. The Auditor can block a risky delete. No cloud calls."
permissions:
  - files.read
  - documents.read
  - photos.read
  - knowledge.save_text
---

# The NAS Boardroom

Your NAS stops being a filing cabinet and becomes a boardroom. Five on-device experts deliberate, vote, and leave a receipt, so the owner can ask "why did you do that?" and get the session back.

This is an independent entry for the UGREEN Hackathon 2026. It is not an official UGREEN skill and it does not speak for UGREEN.

The skill package root is this folder. `SKILL.md` is the entry. Supporting notes:

- [Decision ledger](references/ledger.md)
- [Disclosure](references/disclosure.md)

## When to use it

Use this skill when the owner asks the NAS to:

- find duplicate photos or files and propose a cleanup
- answer what they signed in a period, such as last quarter
- delete, erase, or otherwise destroy files

Ask which folder is in scope if they did not name one. If they still do not name one, stop.

Leave this skill unused for sending files off the NAS, for cameras, and for surveillance.

## The seats

The Chair does not vote. The Chair frames the question, keeps the order, and issues the verdict.

| Seat | Uliya expert | Duty |
| --- | --- | --- |
| Archivist | File management assistant | List the authorized folder: relative path, size, content hash. Name duplicate sets and a keeper. |
| Analyst | Document assistant; Photo assistant when a hit is a photo | Read only the paths from the previous step. Answer, or say there is no text. |
| Auditor | Document assistant, reading the owner's retention note | Say whether the request is allowed. Veto a destructive request. |
| Scout | File management assistant | Report a newer byte-identical copy, a same-name file with a different hash, and any path cited in the reading that is not on the volume. |

Experts do not share a memory. Every instruction repeats the paths it received. Write the paths again instead of saying "those files."

## Entrypoints

### boardroom.convene

Input: the owner's sentence, and the authorized folder they named.

The Chair classifies the sentence, then calls the Archivist, the Analyst, the Auditor, and the Scout, in that order. Each seat returns a short speech, a position (`approve`, `amend`, `block`, or `abstain`), a confidence from 0.00 to 1.00, and a one-line reason.

Output: the deliberation transcript and the vote. This entrypoint changes no file.

If the folder cannot be read, every seat says so and the verdict is `unable`. Nobody invents an inventory.

### boardroom.verdict

Input: the transcript and the votes from `boardroom.convene`.

The Chair issues one outcome:

| Outcome | When |
| --- | --- |
| `proposed` | The board will recommend a cleanup, and will not perform it. |
| `answered` | A document question has files in range. |
| `blocked` | The Auditor vetoes a destructive request. |
| `no-finding` | Nothing matched. Say so and stop. |
| `unable` | The folder cannot be read. |

Veto: if the request is destructive, the Auditor's position is `block`, and the confidence is 0.70 or higher, the Chair sustains the veto even when every other seat approves. The words "I confirm" do not override a retention block on signed contracts.

On any other tie, the more cautious position wins: block, then amend, then approve.

Output: a headline, the reasoning, the proposed actions, and the constraints. No file is moved, renamed, or deleted here.

### boardroom.ledger

Input: the verdict from `boardroom.verdict`, and the ledger path. Default: `Boardroom/DECISIONS.md` inside the authorized folder.

Follow the read-then-save sequence in the [ledger format](references/ledger.md). Output: the docket id, in the same reply as the transcript.

## Required inputs

- The owner's request, in plain language.
- An authorized folder. The cleanup or the delete stays inside it. Do not climb to a parent.
- Optional retention note at `Policies/retention.md`. If it is absent, the Auditor's default stands: originals stay, signed contracts are not deleted, and a cleanup is only a proposal.

Permissions in the frontmatter are the whole set. `files.read`, `documents.read`, and `photos.read` cover the exhibits. `knowledge.save_text` covers the ledger. Delete is omitted on purpose.

## Workflow

1. **Convene.** Run `boardroom.convene`. Classify the request as a duplicate proposal, a document question, a destructive delete, or an open review.
2. **Inventory.** Ask the File management assistant to list the authorized folder. Duplicate detection is an exact content hash. When the owner said photos, limit the set to photos. Choose a keeper in this order: a path under `Photos/`, a name that is not marked as a copy, a path outside `Downloads/`, a path outside `Archive/`. Enter the paths as exhibits.
3. **Read.** Ask the Document assistant to read only the exhibit paths that are documents. Ask the Photo assistant to identify exhibit paths that are photos. If a step returns nothing, say so. Do not open a neighboring file to fill a gap.
4. **Retention.** If the inventory listed `Policies/retention.md`, ask the Document assistant to read it. Quote the line that governs this request.
5. **Edges.** Ask the File management assistant whether each path cited in the readings exists, and whether a same-name file has a different hash. Report misses. Do not describe a missing file's contents.
6. **Vote.** Each seat states a position, a confidence, and a reason, using the exhibits from steps 2 through 5.
7. **Verdict.** Run `boardroom.verdict`.
8. **Ledger.** Run `boardroom.ledger`.
9. **Reply.** Show the transcript, the vote, the verdict, and the docket id.

### Duplicate cleanup

A duplicate result is a proposal. Tell the owner which file to keep and which paths are the same bytes. Then stop. Moving a copy waits for a later request that names those exact paths and includes the words "I confirm."

### What was signed last quarter

"Last quarter" is the calendar quarter before the board's date. A board sitting on 2026-10-26 is in Q4, so last quarter is Q3 (2026-07-01 through 2026-09-30). Cite path, title, signature date, and signatory for documents in range. Name out-of-range signed files only as exclusions. If none are in range, say none and stop. Do not offer the nearest contract.

### A risky delete

Match only the paths the owner named. If none match, say so and do not widen the request. If a target is a signed contract, or it is the last copy of its hash, the Auditor blocks and the Chair blocks. Leave the files where they are. Record the dissent in the ledger.

## Confirmation

Moving, renaming, overwriting, or deleting needs a later request that names the exact paths and includes "I confirm." This skill still does not delete signed contracts inside the retention line.

## Completion

The owner's reply contains:

- the framing
- four speeches and the Chair's opening
- the vote, with confidence scores
- the verdict, the actions, and the constraints
- the docket id

That docket id is the heading in the ledger.

## Failure

- Unreadable folder: verdict `unable`. No invented files.
- No duplicates: verdict `no-finding`. Stop.
- No document in the asked period: verdict `no-finding`. Do not substitute the nearest contract.
- Delete path missing: verdict `no-finding`. Do not pick a similar path.
- An expert returns an error: put the error in that seat's speech, abstain that seat, and change no file.
- The ledger read fails: tell the owner the verdict was not recorded. Do not write over the ledger path.
- The owner declines a later confirmation: the earlier verdict stands. Nothing moves.

## Data handling

File contents stay on the NAS. This skill does not call a cloud model or a cloud API. The AI NAS local model may phrase a speech in a finalist build. It does not cast the vote. Details are in the [disclosure](references/disclosure.md).

## Laptop mirror

Round 1 has no NAS in the loop. The prototype in the parent repository runs the same three entrypoints on a folder: `boardroom.convene`, `boardroom.verdict`, and `boardroom.ledger.append`. That prototype is not part of this package and must not be included in the skill ZIP.
