"""The NAS Boardroom: five local seats, one verdict, a receipt on the volume."""

from __future__ import annotations

from boardroom import ledger
from boardroom.session import convene
from boardroom.tally import verdict

__all__ = ["convene", "verdict", "ledger", "__version__"]
__version__ = "0.1.0"
