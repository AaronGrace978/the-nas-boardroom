"""What each seat says, and how they vote. The model may rephrase; it may not vote."""

from __future__ import annotations

from boardroom.dates import format_mtime
from boardroom.intent import confirmed, is_signature_question
from boardroom.models import Findings, Speech, Vote
from boardroom.phrasing import join_and

CHAIR = "THE CHAIR"
ARCHIVIST = "THE ARCHIVIST"
ANALYST = "THE ANALYST"
AUDITOR = "THE AUDITOR"
SCOUT = "THE SCOUT"

FRAMING = {
    "duplicate": (
        "a duplicate-cleanup proposal. The board may name a keeper. "
        "It may not move or delete."
    ),
    "question": (
        "a document question. The board may answer from files that fit the question. "
        "It may not substitute a nearby file."
    ),
    "delete": (
        "a destructive request. The Auditor holds a veto. No seat is allowed to delete."
    ),
    "review": "an open review. The board reports. It takes no action.",
}


def speeches_for(findings: Findings) -> tuple[Speech, ...]:
    return (
        _chair(findings),
        _archivist(findings),
        _analyst(findings),
        _auditor(findings),
        _scout(findings),
    )


def exhibits_for(findings: Findings) -> tuple[str, ...]:
    if findings.volume_missing:
        return (f"{findings.nas_root} is not a readable directory.",)
    bits = [f"{findings.photo_count} photos", f"{findings.document_count} documents"]
    if findings.other_count:
        bits.append(f"{findings.other_count} other")
    items = [f"{findings.file_count} files on the volume ({', '.join(bits)})."]
    if findings.kind == "duplicate":
        if not findings.groups:
            items.append("No exact-hash duplicate set.")
        for group in findings.groups:
            copies = ", ".join(copy.rel_path for copy in group.copies)
            items.append(
                f"Hash {group.short_hash}: keep {group.keeper.rel_path}; copies {copies}."
            )
        for record in findings.namesakes:
            items.append(
                f"Namesake with a different hash: {record.rel_path} ({record.short_hash})."
            )
    if findings.kind == "question":
        if findings.quarter_label and findings.quarter_start and findings.quarter_end:
            items.append(
                f"Last quarter is {findings.quarter_label}, "
                f"{findings.quarter_start.isoformat()} through {findings.quarter_end.isoformat()}."
            )
        if findings.signed_hits:
            for doc in findings.signed_hits:
                signed = doc.signed_on.isoformat() if doc.signed_on else "an unreadable date"
                items.append(f"In range: {doc.rel_path} signed {signed} by {doc.signatory}.")
        else:
            items.append("No signed document falls in range.")
        for doc in findings.signed_outside:
            when = doc.signed_on.isoformat() if doc.signed_on else "an unreadable date"
            items.append(f"Outside the answer: {doc.rel_path} signed {when}.")
    if findings.kind == "delete":
        if not findings.targets:
            items.append("No path in the request matched a file. The request was not widened.")
        for record in findings.targets:
            items.append(f"Target: {record.rel_path} (hash {record.short_hash}).")
    for ref in findings.missing_refs:
        items.append(f"Cited and missing: {ref.cited} (from {ref.source}).")
    if findings.policy_path:
        items.append(f"Retention note: {findings.policy_path}.")
    return tuple(items)


def _chair(findings: Findings) -> Speech:
    return Speech(
        "chair",
        CHAIR,
        (
            f'The question before the board is: "{findings.request}"',
            f"I frame it as {FRAMING[findings.kind]}",
            "Speakers, in order: the Archivist, the Analyst, the Auditor, the Scout. "
            "I do not vote. I will issue the verdict after the tally.",
        ),
    )


def _archivist(findings: Findings) -> Speech:
    if findings.volume_missing:
        return Speech(
            "archivist",
            ARCHIVIST,
            (
                f"I was asked to walk {findings.nas_root}. That path is not a readable directory.",
                "I will not invent an inventory.",
            ),
            Vote("archivist", "block", 0.95, "There is no volume to deliberate over."),
        )
    if findings.kind == "duplicate":
        return _archivist_duplicates(findings)
    if findings.kind == "delete":
        return _archivist_delete(findings)
    if findings.kind == "question":
        return _archivist_question(findings)
    count = _count_sentence(findings)
    return Speech(
        "archivist",
        ARCHIVIST,
        (
            count,
            "No cleanup and no delete was moved. The inventory is the whole of my report.",
        ),
        Vote("archivist", "approve", 0.62, "The inventory is on the record. No action was requested."),
    )


def _archivist_duplicates(findings: Findings) -> Speech:
    paragraphs = [_count_sentence(findings)]
    if not findings.groups:
        paragraphs.append(
            "No two files in scope share a hash. I will not nominate lookalikes. "
            "Names that rhyme are not copies."
        )
        return Speech(
            "archivist",
            ARCHIVIST,
            tuple(paragraphs),
            Vote("archivist", "approve", 0.90, "I approve an empty duplicate report. There is nothing to clean."),
        )
    for group in findings.groups:
        copies = join_and([copy.rel_path for copy in group.copies])
        paragraphs.append(
            f"Hash {group.short_hash} is shared by {len(group.members)} files. "
            f"I keep {group.keeper.rel_path}. "
            f"The redundant copies are {copies}."
        )
    paragraphs.append(
        "The keeper is the copy under Photos/ when there is one, then a name that is not marked "
        "as a copy, then anything outside Downloads and Archive. Same bytes are the same picture. "
        "A later timestamp is not a new version."
    )
    if findings.namesakes:
        listed = join_and(
            [f"{item.rel_path} ({item.short_hash})" for item in findings.namesakes]
        )
        paragraphs.append(f"A different file shares the name and not the hash: {listed}. It stays out of the set.")
    copies = sum(len(group.copies) for group in findings.groups)
    sets = len(findings.groups)
    return Speech(
        "archivist",
        ARCHIVIST,
        tuple(paragraphs),
        Vote(
            "archivist",
            "approve",
            0.92,
            f"{sets} duplicate set{'s' if sets != 1 else ''}, "
            f"{copies} redundant file{'s' if copies != 1 else ''}. "
            "The library copy is the keeper.",
        ),
    )


def _archivist_question(findings: Findings) -> Speech:
    signed = len(findings.signed_hits) + len(findings.signed_outside) + len(findings.unreadable_signed)
    return Speech(
        "archivist",
        ARCHIVIST,
        (
            _count_sentence(findings),
            f"I marked {signed} document{'s' if signed != 1 else ''} with a SIGNED status or a SIGNED name "
            "and handed those paths to the Analyst. The photo bytes stay hashed, not interpreted.",
        ),
        Vote(
            "archivist",
            "approve",
            0.86,
            "The signed-document paths are the whole set I will let the Analyst read.",
        ),
    )


def _archivist_delete(findings: Findings) -> Speech:
    if not findings.targets:
        return Speech(
            "archivist",
            ARCHIVIST,
            (
                _count_sentence(findings),
                "No file path in the request matches this volume. I will not widen the request to the files that do exist.",
            ),
            Vote("archivist", "approve", 0.90, "Nothing matched. I approve saying so, and nothing else."),
        )
    lines = []
    unique = []
    for record in findings.targets:
        left = findings.survivors(record)
        if left == 0:
            unique.append(record.rel_path)
            lines.append(f"{record.rel_path} is the only copy of hash {record.short_hash}.")
        else:
            noun = "copy" if left == 1 else "copies"
            lines.append(
                f"{record.rel_path} has {left} surviving {noun} of hash {record.short_hash} outside the request."
            )
    count = len(findings.targets)
    paragraphs = [
        _count_sentence(findings),
        f"The request matches {count} file{'s' if count != 1 else ''}.",
        *lines,
    ]
    if unique:
        return Speech(
            "archivist",
            ARCHIVIST,
            tuple(paragraphs),
            Vote(
                "archivist",
                "block",
                0.88,
                "At least one target is the only copy of its bytes. I block.",
            ),
        )
    return Speech(
        "archivist",
        ARCHIVIST,
        tuple(paragraphs),
        Vote(
            "archivist",
            "amend",
            0.80,
            "Every target still has a copy outside the request. I amend this into a proposal.",
        ),
    )


def _analyst(findings: Findings) -> Speech:
    if findings.volume_missing:
        return Speech(
            "analyst",
            ANALYST,
            ("I have no paths, so I have nothing to read.",),
            Vote("analyst", "abstain", 0.0, "No exhibits."),
        )
    if findings.kind == "duplicate":
        return _analyst_duplicates(findings)
    if findings.kind == "question":
        return _analyst_question(findings)
    if findings.kind == "delete":
        return _analyst_delete(findings)
    return Speech(
        "analyst",
        ANALYST,
        ("No document question was asked. I left the file contents closed.",),
        Vote("analyst", "abstain", 0.0, "Nothing to read for an open review."),
    )


def _analyst_duplicates(findings: Findings) -> Speech:
    if not findings.groups:
        return Speech(
            "analyst",
            ANALYST,
            ("The Archivist named no duplicate set. I did not go looking for a similar photo to stand in for one.",),
            Vote("analyst", "approve", 0.84, "I approve the empty set. I did not open the contracts."),
        )
    members = [item for group in findings.groups for item in group.members]
    jpeg = all(item.header == "jpeg" for item in members)
    if jpeg:
        body = (
            "I inspected only the duplicate set. Each file is a JPEG container with no text layer. "
            "I did not open the contracts, the invoice, or the retention note."
        )
    else:
        body = (
            "I inspected only the duplicate set. They are not all JPEG files. "
            "I am reporting the bytes I was given, and I did not open unrelated documents."
        )
    return Speech(
        "analyst",
        ANALYST,
        (
            body,
            "Nothing in those contents marks one copy as a signed original. "
            "I have no content reason to keep every copy.",
        ),
        Vote("analyst", "approve", 0.80, "The duplicate set is image data. The contracts stayed closed."),
    )


def _analyst_question(findings: Findings) -> Speech:
    if not is_signature_question(findings.request):
        return Speech(
            "analyst",
            ANALYST,
            ("This seat answers signature questions from documents marked SIGNED. This request is not one of those.",),
            Vote("analyst", "abstain", 0.0, "No signature question to answer."),
        )
    if findings.quarter_label and findings.quarter_start and findings.quarter_end:
        opener = (
            f"You asked what was signed last quarter. Counting from {findings.today.isoformat()}, "
            f"last quarter is {findings.quarter_label}, {findings.quarter_start.isoformat()} "
            f"through {findings.quarter_end.isoformat()}."
        )
    else:
        opener = "You asked about signed documents, and you did not name a period. I will list every dated signature I can read."
    paragraphs = [
        opener,
        "I read every document marked SIGNED. I did not open the photos, the invoice, or the meeting notes.",
    ]
    if findings.signed_hits:
        for doc in findings.signed_hits:
            when = doc.signed_on.isoformat() if doc.signed_on else "an unreadable date"
            subject = ""
            if doc.subject:
                sentence = doc.subject[:1].upper() + doc.subject[1:]
                if not sentence.endswith("."):
                    sentence += "."
                subject = " " + sentence
            paragraphs.append(
                f"{doc.rel_path}: {doc.title}, signed {when} by {doc.signatory}.{subject}"
            )
    else:
        window = findings.quarter_label or "the requested set"
        paragraphs.append(
            f"None of the signed documents fall in {window}. "
            "I will not move a neighboring contract in to fill the gap."
        )
    if findings.signed_outside:
        excluded = join_and(
            f"{doc.rel_path} ({doc.signed_on.isoformat()})"
            for doc in findings.signed_outside
            if doc.signed_on
        )
        paragraphs.append(f"Outside that quarter, and not the answer: {excluded}.")
    if findings.unreadable_signed:
        paragraphs.append(
            "I could not read a signature date on "
            + join_and(list(findings.unreadable_signed))
            + ". Those files are not counted."
        )
    if findings.signed_hits:
        because = (
            f"{len(findings.signed_hits)} signed document"
            f"{'' if len(findings.signed_hits) == 1 else 's'} sit in range."
        )
        confidence = 0.93
    else:
        because = "I read the signed documents. None fall in range, and I will not substitute."
        confidence = 0.91
    return Speech(
        "analyst",
        ANALYST,
        tuple(paragraphs),
        Vote("analyst", "approve", confidence, because),
    )


def _analyst_delete(findings: Findings) -> Speech:
    if not findings.targets:
        return Speech(
            "analyst",
            ANALYST,
            ("There is no matched file to read. I will not open a nearby folder in its place.",),
            Vote("analyst", "abstain", 0.0, "No target to read."),
        )
    signed = [item.rel_path for item in findings.targets if item.rel_path in set(findings.signed_paths)]
    if signed:
        return Speech(
            "analyst",
            ANALYST,
            (
                "I read the targets and left the rest of the volume closed.",
                "These are signed agreements: "
                + join_and(signed)
                + ". Deleting them deletes the text I would need the next time you ask what you signed.",
            ),
            Vote(
                "analyst",
                "block",
                0.86,
                "The targets include signed agreements. I block.",
            ),
        )
    return Speech(
        "analyst",
        ANALYST,
        ("I read the targets. None of them is a signed agreement.",),
        Vote("analyst", "amend", 0.70, "No signed agreement in the targets. I amend toward a proposal."),
    )


def _auditor(findings: Findings) -> Speech:
    if findings.volume_missing:
        return Speech(
            "auditor",
            AUDITOR,
            ("I cannot apply a retention rule to a volume I cannot see.",),
            Vote("auditor", "block", 0.90, "No volume, no action."),
        )
    policy = _policy_paragraph(findings)
    if findings.kind == "duplicate":
        return Speech(
            "auditor",
            AUDITOR,
            (
                policy,
                "A cleanup of photo duplicates may be proposed. Deletion is not on the table. "
                "I amend the motion: name the keeper, hold the redundant copies for a person to confirm, "
                "and move nothing in this session.",
            ),
            Vote(
                "auditor",
                "amend",
                0.90,
                "Policy allows a proposal. It does not allow a silent delete. I amend.",
            ),
        )
    if findings.kind == "question":
        return Speech(
            "auditor",
            AUDITOR,
            (
                policy,
                "This is a question, not a delete. The answer stays on the files you asked about. "
                "I approve that scope. Documents from another quarter stay out of the answer, "
                "and the photo library stays closed.",
            ),
            Vote(
                "auditor",
                "approve",
                0.84,
                "The question is in scope. I approve an answer that does not widen it.",
            ),
        )
    if findings.kind == "delete":
        return _auditor_delete(findings, policy)
    return Speech(
        "auditor",
        AUDITOR,
        (policy, "No motion is on the floor. I have nothing to veto."),
        Vote("auditor", "abstain", 0.0, "No action was proposed."),
    )


def _auditor_delete(findings: Findings, policy: str) -> Speech:
    if not findings.targets:
        return Speech(
            "auditor",
            AUDITOR,
            (
                policy,
                "There is no matching path. Silence is not a license to delete something else.",
            ),
            Vote(
                "auditor",
                "abstain",
                0.0,
                "No matching path. I will not widen a delete to the rest of the volume.",
            ),
        )
    signed = [item for item in findings.targets if item.rel_path in set(findings.signed_paths)]
    last_copy = [item for item in findings.targets if findings.survivors(item) == 0]
    if signed:
        return Speech(
            "auditor",
            AUDITOR,
            (
                policy,
                "The request would destroy signed contracts inside the retention line. "
                "Saying 'I confirm' does not lift that line. I vote to block.",
            ),
            Vote(
                "auditor",
                "block",
                0.97,
                "Signed contracts sit inside the retention line. A confirmation phrase does not lift it. I block the delete.",
            ),
        )
    if last_copy:
        return Speech(
            "auditor",
            AUDITOR,
            (
                policy,
                "This would destroy the last copy of "
                + join_and([item.rel_path for item in last_copy])
                + ". I block it.",
            ),
            Vote("auditor", "block", 0.93, "This would destroy the last copy of a file. I block."),
        )
    if not confirmed(findings.request):
        return Speech(
            "auditor",
            AUDITOR,
            (
                policy,
                "The hashes survive elsewhere, and you have not confirmed the exact paths. I block an unconfirmed delete.",
            ),
            Vote(
                "auditor",
                "block",
                0.91,
                "The copies are redundant, and the owner has not confirmed the exact delete. I block.",
            ),
        )
    return Speech(
        "auditor",
        AUDITOR,
        (
            policy,
            "Confirmation is on the record, and a copy of each hash survives. "
            "Even then, this session only records a proposal. It does not delete.",
        ),
        Vote(
            "auditor",
            "amend",
            0.84,
            "Confirmation is on the record and the hashes survive elsewhere. This session still only records a proposal.",
        ),
    )


def _scout(findings: Findings) -> Speech:
    if findings.volume_missing:
        return Speech(
            "scout",
            SCOUT,
            ("I cannot watch the edge of a volume that is not there.",),
            Vote("scout", "abstain", 0.0, "No volume."),
        )
    if findings.kind == "duplicate":
        return _scout_duplicates(findings)
    if findings.kind == "question":
        return _scout_question(findings)
    if findings.kind == "delete":
        return _scout_delete(findings)
    return Speech(
        "scout",
        SCOUT,
        ("No edge was asked about. I abstain.",),
        Vote("scout", "abstain", 0.0, "No edge to report."),
    )


def _scout_duplicates(findings: Findings) -> Speech:
    paragraphs: list[str] = []
    for group in findings.groups:
        newer = [copy for copy in group.copies if copy.mtime > group.keeper.mtime]
        for copy in newer:
            paragraphs.append(
                f"{copy.rel_path} matches the keeper byte for byte and is newer "
                f"({format_mtime(copy.mtime)} versus {format_mtime(group.keeper.mtime)} "
                f"on {group.keeper.rel_path}). A later arrival of the same bytes is still a copy."
            )
        if not newer:
            paragraphs.append(
                f"No redundant copy of hash {group.short_hash} is newer than {group.keeper.rel_path}."
            )
    if findings.namesakes:
        for record in findings.namesakes:
            paragraphs.append(
                f"{record.rel_path} shares a name with the keeper and not the hash "
                f"({record.short_hash}). "
                "It is an older namesake, not a duplicate. Leave it out of the cleanup set."
            )
    if not paragraphs:
        paragraphs.append(
            "I checked for a newer byte-identical file and for a same-name file with a different hash. "
            "Neither is on the volume."
        )
    if findings.namesakes:
        position, confidence, because = (
            "amend",
            0.74,
            "A newer copy is still a copy, and the different-hash namesake stays out of the set.",
        )
    elif findings.groups:
        position, confidence, because = (
            "amend",
            0.74,
            "A newer byte-identical file is still a copy. The proposal should say so.",
        )
    else:
        position, confidence, because = (
            "approve",
            0.70,
            "No edge case to add. I approve the empty report.",
        )
    return Speech("scout", SCOUT, tuple(paragraphs), Vote("scout", position, confidence, because))


def _scout_question(findings: Findings) -> Speech:
    if findings.missing_refs:
        listed = join_and(f"{ref.cited} (named by {ref.source})" for ref in findings.missing_refs)
        return Speech(
            "scout",
            SCOUT,
            (
                f"The documents in the answer cite paths that are not on the volume: {listed}.",
                "I will not invent those files, and I will not answer as if I had read them.",
            ),
            Vote(
                "scout",
                "amend",
                0.68,
                "A cited path is missing. Name the gap, and do not invent the file.",
            ),
        )
    if not findings.signed_hits:
        return Speech(
            "scout",
            SCOUT,
            ("Nothing in range cites a missing file, because nothing in range was signed.",),
            Vote("scout", "approve", 0.66, "No in-range document, so no missing citation to chase."),
        )
    return Speech(
        "scout",
        SCOUT,
        ("I checked the paths cited by the documents in the answer. The ones they name are on the volume.",),
        Vote("scout", "approve", 0.70, "No missing citation in the documents that answer the question."),
    )


def _scout_delete(findings: Findings) -> Speech:
    if not findings.targets:
        return Speech(
            "scout",
            SCOUT,
            ("No path matched, so there is no edge to tear.",),
            Vote("scout", "abstain", 0.0, "No target, no edge."),
        )
    paragraphs = []
    if findings.missing_refs:
        for ref in findings.missing_refs:
            paragraphs.append(
                f"{ref.cited} is already missing, and {ref.source} is the file that names it. "
                "Deleting that file would erase the citation too."
            )
    last = [item.rel_path for item in findings.targets if findings.survivors(item) == 0]
    if last:
        paragraphs.append(
            "These targets have no second copy anywhere else I can see: " + join_and(last) + "."
        )
    if not paragraphs:
        paragraphs.append("Each target hash survives outside the request. The edge is intact.")
        return Speech(
            "scout",
            SCOUT,
            tuple(paragraphs),
            Vote("scout", "amend", 0.66, "The hashes survive elsewhere. I amend toward a proposal."),
        )
    return Speech(
        "scout",
        SCOUT,
        tuple(paragraphs),
        Vote(
            "scout",
            "block",
            0.80,
            "A target is the last copy, or it is the only citation of a missing file. I block.",
        ),
    )


def _count_sentence(findings: Findings) -> str:
    bits = [f"{findings.photo_count} photos", f"{findings.document_count} documents"]
    if findings.other_count:
        bits.append(f"{findings.other_count} other")
    return (
        f"I walked the volume and counted {findings.file_count} files: {join_and(bits)}."
    )


def _policy_paragraph(findings: Findings) -> str:
    if findings.policy_path and findings.policy_quote:
        return (
            f"I read {findings.policy_path}. The line that governs this motion: "
            f"\"{findings.policy_quote}\""
        )
    return (
        "No retention note is on the volume. My default stands: originals stay, "
        "signed contracts are not deleted, and a cleanup is only a proposal until a person confirms it."
    )
