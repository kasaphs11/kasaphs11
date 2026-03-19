# date_helpers.py
# Βοηθητικές συναρτήσεις για ημερομηνίες

import datetime as dt


class ScheduleError(RuntimeError):
    def __init__(self, message: str, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or message


def is_weekend(year: int, month: int, day: int) -> bool:
    wd = dt.date(year, month, day).weekday()
    return wd in (5, 6)


def parse_days_list(s: str, days_in_month: int) -> set[int]:
    s = (s or "").strip()
    if not s:
        return set()

    out: set[int] = set()
    parts = [p.strip() for p in s.split(",") if p.strip()]
    for p in parts:
        if "-" in p:
            a, b = p.split("-", 1)
            a, b = int(a), int(b)
            lo, hi = min(a, b), max(a, b)
            for d in range(lo, hi + 1):
                if 1 <= d <= days_in_month:
                    out.add(d)
                else:
                    raise ValueError(f"Ημέρα εκτός μήνα: {d}")
        else:
            d = int(p)
            if 1 <= d <= days_in_month:
                out.add(d)
            else:
                raise ValueError(f"Ημέρα εκτός μήνα: {d}")
    return out


def day_bucket(year: int, month: int, day: int, extra_holidays: set[int]) -> str:
    if day in extra_holidays:
        return "HOLIDAY"
    return "HOLIDAY" if is_weekend(year, month, day) else "WEEKDAY"
