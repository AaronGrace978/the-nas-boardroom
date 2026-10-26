"""Calendar helpers. The board speaks in Eastern Time."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def clock(now: datetime | None = None) -> datetime:
    """Return an aware Eastern Time timestamp."""
    if now is None:
        return datetime.now(ET)
    if now.tzinfo is None:
        return now.replace(tzinfo=ET)
    return now.astimezone(ET)


def format_et(moment: datetime) -> str:
    local = clock(moment)
    hour = local.strftime("%I").lstrip("0") or "12"
    return f"{local.strftime('%Y-%m-%d')} {hour}:{local.strftime('%M %p')} ET"


def format_mtime(stamp: float) -> str:
    return datetime.fromtimestamp(stamp, ET).date().isoformat()


def last_quarter(day: date) -> tuple[str, date, date]:
    """Calendar quarter before `day`.

    October 26, 2026 is in Q4, so last quarter is Q3 2026
    (July 1 through September 30).
    """
    current = (day.month - 1) // 3 + 1
    if current == 1:
        year, quarter = day.year - 1, 4
    else:
        year, quarter = day.year, current - 1
    start_month = 3 * (quarter - 1) + 1
    end_month = start_month + 2
    start = date(year, start_month, 1)
    end = date(year, end_month, calendar.monthrange(year, end_month)[1])
    return f"Q{quarter} {year}", start, end


def parse_first_date(text: str) -> date | None:
    """Parse the earliest ISO or 'Month D, YYYY' date in `text`."""
    found: list[tuple[int, date]] = []
    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso:
        try:
            found.append((iso.start(), date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))))
        except ValueError:
            pass
    named = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(\d{1,2}),\s+(\d{4})\b",
        text,
        re.IGNORECASE,
    )
    if named:
        try:
            found.append(
                (
                    named.start(),
                    date(int(named.group(3)), _MONTHS[named.group(1).lower()], int(named.group(2))),
                )
            )
        except ValueError:
            pass
    if not found:
        return None
    found.sort(key=lambda item: item[0])
    return found[0][1]
