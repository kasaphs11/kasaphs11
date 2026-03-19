# cross_tab.py
# Διαχείριση cross-tab αλληλεπιδράσεων:
# blocked days μεταξύ tabs, καταμέτρηση αργιών/Παρ σε άλλα tabs

import datetime as dt
import calendar

from logic.constants import MIN_GAP_STRICT


def cross_tab_blocked_days(
    assigned_days: set,
    source_tab: str,
    year: int,
    month: int,
) -> set:
    """
    Για κάθε μέρα που έχει ήδη ανατεθεί σε άλλο tab, επιστρέφει
    όλες τις blocked μέρες για το τρέχον tab:
      - Η ίδια η μέρα
      - Gap=2 (±2 μέρες)
      - Weekend rules (Παρ/Σαβ extended gap ανά service)
    """
    _, dim = calendar.monthrange(year, month)

    # Weekend gap ανά service
    req_fri = 3 if source_tab in ("AYDM", "PYLI") else 4
    req_sat = 4 if source_tab in ("AYDM", "PYLI") else 5

    blocked = set()
    for aday in assigned_days:
        # Ίδια μέρα + gap=2
        for delta in range(-MIN_GAP_STRICT, MIN_GAP_STRICT + 1):
            d = aday + delta
            if 1 <= d <= dim:
                blocked.add(d)

        try:
            wd = dt.date(year, month, aday).weekday()
        except ValueError:
            continue

        if wd == 4:  # Παρασκευή -> block τις επόμενες req_fri μέρες
            for d in range(aday + 1, aday + req_fri + 1):
                if 1 <= d <= dim:
                    blocked.add(d)
        elif wd == 5:  # Σάββατο -> block τις επόμενες req_sat μέρες
            for d in range(aday + 1, aday + req_sat + 1):
                if 1 <= d <= dim:
                    blocked.add(d)

        # Και προς τα πίσω: αν η aday ακολουθεί Παρ/Σαβ
        for delta in range(1, req_sat + 1):
            prev = aday - delta
            if 1 <= prev <= dim:
                try:
                    wd_prev = dt.date(year, month, prev).weekday()
                except ValueError:
                    continue
                if wd_prev == 4 and delta <= req_fri:
                    blocked.add(prev)
                elif wd_prev == 5 and delta <= req_sat:
                    blocked.add(prev)

    return blocked


def compute_cross_tab_counts(
    names: list,
    other_schedules: dict,   # {tab_key: {day_str: person}}
    year: int,
    month: int,
    extra_holidays: set,
) -> tuple[dict, dict]:
    """
    Μετράει για κάθε άτομο πόσες αργίες και Παρασκευές έχει ήδη
    σε άλλα tabs, ώστε να αφαιρεθούν από το quota του τρέχοντος tab.
    Επιστρέφει (cross_hol, cross_fri).
    """
    cross_hol = {p: 0 for p in names}
    cross_fri = {p: 0 for p in names}
    for _tab_key, sched in other_schedules.items():
        for day_str, person in sched.items():
            if person not in names:
                continue
            d = int(day_str)
            try:
                wd = dt.date(year, month, d).weekday()
            except ValueError:
                continue
            if d in extra_holidays or wd >= 5:
                cross_hol[person] = cross_hol.get(person, 0) + 1
            if wd == 4:
                cross_fri[person] = cross_fri.get(person, 0) + 1
    return cross_hol, cross_fri
