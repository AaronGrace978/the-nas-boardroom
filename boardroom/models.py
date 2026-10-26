"""Records that move from the volume to the vote to the ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

Kind = Literal["duplicate", "question", "delete", "review"]
Outcome = Literal["proposed", "answered", "blocked", "no-finding", "unable"]
Position = Literal["approve", "amend", "block", "abstain"]

_POSITIONS = {"approve", "amend", "block", "abstain"}


@dataclass(frozen=True)
class FileRec:
    rel_path: str
    size: int
    mtime: float
    sha256: str
    kind: str
    header: str = "binary"
    text: str | None = None

    @property
    def short_hash(self) -> str:
        return self.sha256[:12]


@dataclass(frozen=True)
class SignedDoc:
    rel_path: str
    title: str
    signed_on: date | None
    signatory: str
    subject: str


@dataclass(frozen=True)
class MissingRef:
    source: str
    cited: str


@dataclass(frozen=True)
class DuplicateGroup:
    sha256: str
    keeper: FileRec
    copies: tuple[FileRec, ...]

    @property
    def short_hash(self) -> str:
        return self.sha256[:12]

    @property
    def members(self) -> tuple[FileRec, ...]:
        return (self.keeper, *self.copies)


@dataclass(frozen=True)
class Findings:
    """What the seats are allowed to talk about for one request."""

    kind: Kind
    request: str
    nas_root: str
    volume_missing: bool
    today: date
    file_count: int
    photo_count: int
    document_count: int
    other_count: int
    files: tuple[FileRec, ...]
    groups: tuple[DuplicateGroup, ...]
    namesakes: tuple[FileRec, ...]
    signed_hits: tuple[SignedDoc, ...]
    signed_outside: tuple[SignedDoc, ...]
    signed_paths: tuple[str, ...]
    unreadable_signed: tuple[str, ...]
    missing_refs: tuple[MissingRef, ...]
    targets: tuple[FileRec, ...]
    reads: tuple[str, ...]
    policy_path: str | None
    policy_quote: str | None
    quarter_label: str | None
    quarter_start: date | None
    quarter_end: date | None
    photo_only: bool

    @property
    def has_subject(self) -> bool:
        if self.volume_missing:
            return False
        if self.kind == "duplicate":
            return bool(self.groups)
        if self.kind == "question":
            return bool(self.signed_hits)
        if self.kind == "delete":
            return bool(self.targets)
        return True

    def survivors(self, record: FileRec) -> int:
        """Copies of this hash that a delete of `targets` would leave behind."""
        doomed = {item.rel_path for item in self.targets}
        return sum(
            1
            for item in self.files
            if item.sha256 == record.sha256 and item.rel_path not in doomed
        )


@dataclass(frozen=True)
class Vote:
    seat: str
    position: Position
    confidence: float
    because: str

    def __post_init__(self) -> None:
        if self.position not in _POSITIONS:
            raise ValueError(f"unknown position: {self.position}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence}")


@dataclass(frozen=True)
class Speech:
    seat: str
    name: str
    paragraphs: tuple[str, ...]
    vote: Vote | None = None


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    headline: str
    reasoning: str
    actions: tuple[str, ...]
    constraints: tuple[str, ...]
    plurality: str | None
    veto: bool
    vote_note: str
    mutated: bool = False


@dataclass(frozen=True)
class Session:
    docket: str
    request: str
    kind: Kind
    framing: str
    nas_root: str
    opened_at: datetime
    today: date
    mode: str
    findings: Findings
    speeches: tuple[Speech, ...]
    exhibits: tuple[str, ...]
    verdict: Verdict

    @property
    def votes(self) -> list[Vote]:
        return [speech.vote for speech in self.speeches if speech.vote is not None]
