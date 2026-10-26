"""Shared fixtures. The fictional volume is rebuilt per test."""

from __future__ import annotations

from pathlib import Path

import pytest

from boardroom.seed import seed_nas

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def nas(tmp_path: Path) -> Path:
    return seed_nas(tmp_path / "nas")
