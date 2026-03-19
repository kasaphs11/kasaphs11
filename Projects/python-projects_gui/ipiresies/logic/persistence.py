# persistence.py
# Διαχείριση path αρχείων και βοηθητικές συναρτήσεις I/O

import os
import sys


def get_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # Αυτό το αρχείο βρίσκεται στο logic/persistence.py
    # Ανεβαίνουμε ένα επίπεδο στο project root.
    this_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(this_dir)


def get_json_dir() -> str:
    """Ο φάκελος `json/` που περιέχει όλα τα JSON αρχεία."""
    return os.path.join(get_base_dir(), "json")


def get_state_path() -> str:
    """Αρχείο για τα inputs (άτομα, ρυθμίσεις)."""
    return os.path.join(get_json_dir(), "scheduler_people.json")


def get_schedule_path() -> str:
    """Αρχείο για τα παραγόμενα προγράμματα."""
    return os.path.join(get_json_dir(), "scheduler_schedule.json")


def safe_int(s: str, default: int) -> int:
    try:
        return int(str(s).strip())
    except Exception:
        return default
