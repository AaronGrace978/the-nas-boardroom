"""Build the exhibit list. Seats speak from this, not from a second look."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from pathlib import Path, PurePosixPath

from boardroom.corpus import scan
from boardroom.dates import last_quarter, parse_first_date
from boardroom.intent import (
    classify,
    is_signature_question,
    photo_scope,
    wants_last_quarter,
)
from boardroom.models import (
    DuplicateGroup,
    FileRec,
    Findings,
    Kind,
    MissingRef,
    SignedDoc,
)

_PATH_IN_TEXT = re.compile(r"(?:[A-Za-z0-9_.\-]+/)+[A-Za-z0-9_.\-]+\.[A-Za-z0-9]{1,8}")
_STATUS_SIGNED = re.compile(r"(?m)^Status:\s*SIGNED\s*$")
_FIELD = {
    "signatory": re.compile(r"(?m)^Signatory:\s*(.+?)\s*$"),
    "subject": re.compile(r"(?m)^Subject:\s*(.+?)\s*$"),
    "signed_on": re.compile(r"(?m)^Signed on:\s*(.+?)\s*$"),
}


def build_findings(request: str, nas_root: str | Path, today: date) -> Findings:
    display = str(nas_root)
    root = Path(nas_root).expanduser()
    kind = classify(request)
    if not root.exists() or not root.is_dir():
        return _blank(kind, request, display, today, missing=True)

    files = scan(root)
    policy = _policy_file(files)
    quote = _policy_quote(policy.text, kind) if policy and policy.text else None
    photos = photo_scope(request) if kind == "duplicate" else False

    groups: tuple[DuplicateGroup, ...] = ()
    namesakes: tuple[FileRec, ...] = ()
    hits: tuple[SignedDoc, ...] = ()
    outside: tuple[SignedDoc, ...] = ()
    unreadable: tuple[str, ...] = ()
    signed_paths: tuple[str, ...] = ()
    targets: tuple[FileRec, ...] = ()
    analyst_reads: tuple[str, ...] = ()
    missing: tuple[MissingRef, ...] = ()
    quarter_label: str | None = None
    quarter_start: date | None = None
    quarter_end: date | None = None

    if kind == "duplicate":
        groups, namesakes = _duplicate_sets(request, files)
    elif kind == "question" and is_signature_question(request):
        (
            hits,
            outside,
            unreadable,
            signed_paths,
            analyst_reads,
            quarter_label,
            quarter_start,
            quarter_end,
        ) = _signatures(request, files, today)
        missing = _missing(files, [doc.rel_path for doc in hits])
    elif kind == "question":
        analyst_reads = tuple(
            item.rel_path for item in files if item.kind == "document" and item.text
        )
    elif kind == "delete":
        targets = tuple(_deletion_targets(request, files))
        signed_paths = tuple(item.rel_path for item in files if _as_signed(item))
        analyst_reads = tuple(item.rel_path for item in targets if item.text is not None)
        missing = _missing(files, list(analyst_reads))

    reads_list = list(analyst_reads)
    if policy is not None:
        reads_list.append(policy.rel_path)
    reads = tuple(dict.fromkeys(reads_list))

    return Findings(
        kind=kind,
        request=request,
        nas_root=display,
        volume_missing=False,
        today=today,
        file_count=len(files),
        photo_count=sum(1 for item in files if item.kind == "photo"),
        document_count=sum(1 for item in files if item.kind == "document"),
        other_count=sum(1 for item in files if item.kind == "other"),
        files=files,
        groups=groups,
        namesakes=namesakes,
        signed_hits=hits,
        signed_outside=outside,
        signed_paths=signed_paths,
        unreadable_signed=unreadable,
        missing_refs=missing,
        targets=targets,
        reads=reads,
        policy_path=policy.rel_path if policy else None,
        policy_quote=quote,
        quarter_label=quarter_label,
        quarter_start=quarter_start,
        quarter_end=quarter_end,
        photo_only=photos,
    )


def _blank(kind: Kind, request: str, display: str, today: date, *, missing: bool) -> Findings:
    return Findings(
        kind=kind,
        request=request,
        nas_root=display,
        volume_missing=missing,
        today=today,
        file_count=0,
        photo_count=0,
        document_count=0,
        other_count=0,
        files=(),
        groups=(),
        namesakes=(),
        signed_hits=(),
        signed_outside=(),
        signed_paths=(),
        unreadable_signed=(),
        missing_refs=(),
        targets=(),
        reads=(),
        policy_path=None,
        policy_quote=None,
        quarter_label=None,
        quarter_start=None,
        quarter_end=None,
        photo_only=photo_scope(request) if kind == "duplicate" else False,
    )


def _policy_file(files: tuple[FileRec, ...]) -> FileRec | None:
    for record in files:
        if record.rel_path.lower() == "policies/retention.md":
            return record
    for record in files:
        if "retention" in record.rel_path.lower() and record.text:
            return record
    return None


def _policy_quote(text: str, kind: Kind) -> str | None:
    lines = [line.strip(" -") for line in text.splitlines() if line.strip() and not line.startswith("#")]
    if not lines:
        return None
    needles = {
        "delete": ("do not delete", "retain", "original"),
        "duplicate": ("duplicate", "photo", "confirm"),
        "question": ("contract", "retain", "original"),
        "review": ("original",),
    }[kind]
    for needle in needles:
        for line in lines:
            if needle in line.lower():
                return line
    return lines[0]


def stem_of(rel_path: str) -> str:
    stem = PurePosixPath(rel_path).stem.lower().replace("_", "-")
    previous = None
    while previous != stem:
        previous = stem
        stem = re.sub(r"\s*\(\d+\)$", "", stem)
        stem = re.sub(r"-(copy|duplicate|dup)$", "", stem)
        stem = re.sub(r"-v\d+$", "", stem)
    return stem


def keeper_key(record: FileRec) -> tuple:
    rel = record.rel_path.lower()
    copyish = 1 if re.search(r"copy|\(\d+\)|duplicate", rel) else 0
    return (
        0 if rel.startswith("photos/") else 1,
        copyish,
        1 if rel.startswith("downloads/") else 0,
        1 if rel.startswith("archive/") else 0,
        record.mtime,
        len(rel),
        rel,
    )


def _duplicate_sets(
    request: str, files: tuple[FileRec, ...]
) -> tuple[tuple[DuplicateGroup, ...], tuple[FileRec, ...]]:
    pool = [item for item in files if item.kind == "photo"] if photo_scope(request) else list(files)
    grouped: dict[str, list[FileRec]] = defaultdict(list)
    for record in pool:
        grouped[record.sha256].append(record)
    groups: list[DuplicateGroup] = []
    for digest, members in sorted(grouped.items()):
        if len(members) < 2:
            continue
        ordered = sorted(members, key=keeper_key)
        groups.append(DuplicateGroup(digest, ordered[0], tuple(ordered[1:])))

    by_stem: dict[str, list[FileRec]] = defaultdict(list)
    for record in pool:
        by_stem[stem_of(record.rel_path)].append(record)
    namesakes: list[FileRec] = []
    seen: set[str] = set()
    for group in groups:
        member_paths = {item.rel_path for item in group.members}
        for record in by_stem.get(stem_of(group.keeper.rel_path), []):
            if record.rel_path in member_paths or record.rel_path in seen:
                continue
            if record.sha256 != group.sha256:
                namesakes.append(record)
                seen.add(record.rel_path)
    return tuple(groups), tuple(namesakes)


def _as_signed(record: FileRec) -> SignedDoc | None:
    if record.text is None:
        return None
    named = "SIGNED" in PurePosixPath(record.rel_path).name.upper()
    if not named and not _STATUS_SIGNED.search(record.text):
        return None
    title = next((line.strip() for line in record.text.splitlines() if line.strip()), record.rel_path)
    if title.startswith("#"):
        title = title.lstrip("#").strip()
    signatory_match = _FIELD["signatory"].search(record.text)
    subject_match = _FIELD["subject"].search(record.text)
    signed_line = _FIELD["signed_on"].search(record.text)
    signed_on = parse_first_date(signed_line.group(1)) if signed_line else None
    return SignedDoc(
        rel_path=record.rel_path,
        title=title,
        signed_on=signed_on,
        signatory=signatory_match.group(1).strip() if signatory_match else "unspecified",
        subject=subject_match.group(1).strip() if subject_match else "",
    )


def _signatures(
    request: str, files: tuple[FileRec, ...], today: date
) -> tuple[
    tuple[SignedDoc, ...],
    tuple[SignedDoc, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    str | None,
    date | None,
    date | None,
]:
    parsed = [doc for record in files if (doc := _as_signed(record)) is not None]
    readable = tuple(doc for doc in parsed if doc.signed_on is not None)
    unreadable = tuple(doc.rel_path for doc in parsed if doc.signed_on is None)
    paths = tuple(doc.rel_path for doc in parsed)
    reads = paths
    label: str | None = None
    start: date | None = None
    end: date | None = None
    if wants_last_quarter(request):
        label, start, end = last_quarter(today)
        hits = tuple(doc for doc in readable if start <= doc.signed_on <= end)
        outside = tuple(doc for doc in readable if doc.signed_on < start or doc.signed_on > end)
    else:
        hits = readable
        outside = ()
    return hits, outside, unreadable, paths, reads, label, start, end


def _deletion_targets(request: str, files: tuple[FileRec, ...]) -> list[FileRec]:
    prefixes: list[str] = []
    for match in re.finditer(
        r"(?:in|under|inside|within)\s+([A-Za-z0-9_./\\-]+)", request, re.IGNORECASE
    ):
        prefixes.append(match.group(1).replace("\\", "/").strip("/"))
    for match in re.finditer(r"[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+", request):
        prefixes.append(match.group(0).replace("\\", "/").strip("/"))
    # Preserve order, drop duplicates.
    ordered: list[str] = []
    for prefix in prefixes:
        if prefix and prefix.lower() not in {item.lower() for item in ordered}:
            ordered.append(prefix)

    if not ordered and re.search(
        r"\b(everything|entire volume|whole volume|all files|every file)\b",
        request,
        re.IGNORECASE,
    ):
        return list(files)

    matched: list[FileRec] = []
    seen: set[str] = set()
    lowered = request.lower()
    for record in files:
        rel = record.rel_path
        hit = False
        for prefix in ordered:
            probe = prefix.lower()
            current = rel.lower()
            if current == probe or current.startswith(probe + "/"):
                hit = True
                break
        name = rel.split("/")[-1].lower()
        if not hit and name and name in lowered:
            hit = True
        if hit and rel not in seen:
            matched.append(record)
            seen.add(rel)
    return matched


def _missing(files: tuple[FileRec, ...], sources: list[str]) -> tuple[MissingRef, ...]:
    known = {record.rel_path.lower() for record in files}
    by_path = {record.rel_path: record for record in files}
    found: list[MissingRef] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        record = by_path.get(source)
        if record is None or not record.text:
            continue
        for match in _PATH_IN_TEXT.finditer(record.text):
            cited = match.group(0)
            key = (source, cited)
            if key in seen:
                continue
            if cited.lower() in known or cited.lower() == source.lower():
                continue
            if any(path.endswith("/" + cited.lower()) or path == cited.lower() for path in known):
                continue
            seen.add(key)
            found.append(MissingRef(source=source, cited=cited))
    return tuple(found)
