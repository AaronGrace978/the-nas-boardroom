"""Seed a small, fictional NAS tree for the three showcase sessions."""

from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path

from boardroom.dates import ET
from boardroom.ledger import stage_showcase

_SUNSET = b"\xff\xd8\xff\xe0" + b"sunset-campaign-still" + b"\xff\xd9"
_SUNSET_V1 = b"\xff\xd8\xff\xe0" + b"sunset-campaign-still-v1" + b"\xff\xd9"
_KITCHEN = b"\xff\xd8\xff\xe0" + b"kitchen-table-morning" + b"\xff\xd9"

_POLICY = """\
# Household retention policy

Signed contracts and tax records: retain 7 years. Do not delete.
Photo duplicates: the board may propose cleanup. A person confirms before anything moves.
Originals are never deleted automatically.
"""

_VENDOR = """\
VENDOR SERVICES AGREEMENT
Status: SIGNED
Signed on: August 14, 2026
Signatory: Avery Chen
Subject: photo archive hosting for the Q3 campaign, Harbor Supply Co.
See also: Documents/Contracts/exhibit-b-schedule.pdf
"""

_RELEASE = """\
PHOTO RELEASE
Status: SIGNED
Signed on: September 2, 2026
Signatory: Avery Chen
Subject: use of the beach campaign stills in the Q3 recap.
"""

_LEASE = """\
LEASE ADDENDUM
Status: SIGNED
Signed on: May 3, 2026
Signatory: Avery Chen
Subject: studio unit 4, term extended through May 2027.
"""

_WORKSHOP = """\
WORKSHOP RELEASE
Status: SIGNED
Signed on: October 2, 2026
Signatory: Avery Chen
Subject: liability release for the October lighting workshop.
"""

_NOTES = """\
Quarterly review notes
Date: September 12, 2026
We reviewed the vendor agreement and the beach stills.
Recording: Media/recordings/2026-09-12-quarterly-review.m4a
"""

_INVOICE = """\
INVOICE
Number: HS-441
Date: September 18, 2026
From: Harbor Supply Co.
Amount: 2400 USD
Status: UNPAID
Subject: Q3 hosting. This invoice is not a contract.
"""


def seed_nas(root: str | Path) -> Path:
    """Create the fictional volume. Overwrites files. Does not delete unknown ones."""
    base = Path(root)
    if base.exists():
        shutil.rmtree(base)
    _put(base, "Policies/retention.md", _POLICY, _at(2026, 1, 15))
    _put(base, "Photos/2026/beach-sunset.jpg", _SUNSET, _at(2026, 8, 1))
    _put(base, "Photos/2026/beach-sunset (1).jpg", _SUNSET, _at(2026, 8, 2))
    _put(base, "Downloads/beach-sunset-copy.jpg", _SUNSET, _at(2026, 9, 15))
    _put(base, "Archive/beach-sunset-v1.jpg", _SUNSET_V1, _at(2024, 6, 1))
    _put(base, "Photos/2026/kitchen-table.jpg", _KITCHEN, _at(2026, 8, 20))
    _put(base, "Documents/Contracts/2026-08-14-vendor-agreement-SIGNED.txt", _VENDOR, _at(2026, 8, 14))
    _put(base, "Documents/Contracts/2026-09-02-photo-release-SIGNED.txt", _RELEASE, _at(2026, 9, 2))
    _put(base, "Documents/Contracts/2026-05-03-lease-addendum-SIGNED.txt", _LEASE, _at(2026, 5, 3))
    _put(base, "Documents/Contracts/2026-10-02-workshop-release-SIGNED.txt", _WORKSHOP, _at(2026, 10, 2))
    _put(base, "Documents/Notes/2026-09-12-quarterly-review.txt", _NOTES, _at(2026, 9, 12))
    _put(base, "Documents/Finance/2026-Q3-hosting-invoice.txt", _INVOICE, _at(2026, 9, 18))
    return base


def _at(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, 0, tzinfo=ET)


def _put(root: Path, rel: str, content: str | bytes, when: datetime) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else content
    path.write_bytes(data)
    stamp = when.timestamp()
    os.utime(path, (stamp, stamp))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m boardroom.seed",
        description="Seed a fictional NAS tree and, if asked, stage a fresh showcase ledger.",
    )
    parser.add_argument("--nas", required=True, help="Directory to create")
    parser.add_argument(
        "--reset-ledger",
        help="Write a header-only ledger here. append() never does this itself.",
    )
    args = parser.parse_args(argv)
    seeded = seed_nas(args.nas)
    print(f"Seeded {seeded}")
    if args.reset_ledger:
        stage_showcase(args.reset_ledger)
        print(f"Staged {args.reset_ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
