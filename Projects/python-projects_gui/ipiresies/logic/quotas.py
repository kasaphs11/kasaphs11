# quotas.py
# Υπολογισμός quotas (total, holiday, friday, global, normalize, auto-max)

import calendar
import random

from logic.constants import W_SCORE, F_SCORE, H_SCORE, MIN_GAP_STRICT
from logic.date_helpers import ScheduleError, day_bucket
from logic.history import (
    get_person_group,
    calculate_cumulative_stats,
    build_global_cumulative_stats,
    merge_global_people,
)


# ------------------------------------------------------------------
# Simple (no history)
# ------------------------------------------------------------------

def compute_total_quotas(
    names: list[str],
    days_in_month: int,
    rng: random.Random | None = None,
) -> dict[str, int]:
    if rng is None:
        import time
        rng = random.Random(int(time.time() * 1000) % (2**32))
    base, extra = divmod(days_in_month, len(names))
    shuffled = names[:]
    rng.shuffle(shuffled)
    plus = set(shuffled[:extra])
    return {nm: (base + 1 if nm in plus else base) for nm in names}


def compute_holiday_quotas(
    names: list[str],
    total_holidays: int,
    rng: random.Random | None = None,
) -> dict[str, int]:
    if rng is None:
        import time
        rng = random.Random(int(time.time() * 1000) % (2**32))
    base, extra = divmod(total_holidays, len(names))
    shuffled = names[:]
    rng.shuffle(shuffled)
    plus = set(shuffled[:extra])
    return {nm: (base + 1 if nm in plus else base) for nm in names}


# ------------------------------------------------------------------
# History-aware
# ------------------------------------------------------------------

def compute_total_quotas_with_history(
    names: list[str],
    ranks: dict[str, str],
    days_in_month: int,
    cumulative_stats: dict[str, dict],
    rng: random.Random,
) -> dict[str, int]:
    """Quota ολικής υπηρεσίας με GROUP-BASED MIN-MAX balancing."""
    base, extra = divmod(days_in_month, len(names))
    quotas = {name: base for name in names}
    if extra == 0:
        return quotas

    groups = {"OFFICERS": [], "OTHERS": []}
    for name in names:
        groups[get_person_group(ranks.get(name, ""))].append(name)

    remaining_extra = extra

    for group_members in groups.values():
        if not group_members or remaining_extra == 0:
            continue
        group_totals = {
            n: (cumulative_stats.get(n, {}).get("total_weekdays", 0) +
                cumulative_stats.get(n, {}).get("total_fridays",  0) +
                cumulative_stats.get(n, {}).get("total_holidays", 0))
            for n in group_members
        }
        members_sorted = sorted(group_members, key=lambda n: (group_totals[n], rng.random()))
        group_extra = min(remaining_extra, len(group_members))
        for i in range(group_extra):
            quotas[members_sorted[i]] = base + 1
            remaining_extra -= 1

    if remaining_extra > 0:
        available = [n for n in names if quotas[n] == base]
        if available:
            available_sorted = sorted(
                available,
                key=lambda n: (
                    cumulative_stats.get(n, {}).get("total_weekdays", 0) +
                    cumulative_stats.get(n, {}).get("total_fridays",  0) +
                    cumulative_stats.get(n, {}).get("total_holidays", 0),
                    rng.random()
                )
            )
            for i in range(min(remaining_extra, len(available_sorted))):
                quotas[available_sorted[i]] = base + 1

    return quotas


def compute_holiday_quotas_with_history(
    names: list[str],
    total_holidays: int,
    cumulative_stats: dict[str, dict],
    ranks: dict[str, str],
    rng: random.Random,
    leaves: dict[str, set[int]] = None,
    year: int = None,
    month: int = None,
    extra_holidays: set[int] = None,
) -> dict[str, int]:
    """Quota αργιών με GROUP-BASED MIN-MAX balancing. Zero για όσους δεν έχουν αργία."""
    if leaves is None:
        leaves = {}
    if extra_holidays is None:
        extra_holidays = set()

    available_for_holidays = []
    if year and month:
        _, days_in_month = calendar.monthrange(year, month)
        for name in names:
            leave_days = leaves.get(name, set())
            if any(
                d not in leave_days and day_bucket(year, month, d, extra_holidays) == "HOLIDAY"
                for d in range(1, days_in_month + 1)
            ):
                available_for_holidays.append(name)
    else:
        available_for_holidays = names[:]

    if not available_for_holidays:
        return {name: 0 for name in names}

    base, extra = divmod(total_holidays, len(available_for_holidays))
    quotas = {name: 0 for name in names}
    for name in available_for_holidays:
        quotas[name] = base
    if extra == 0:
        return quotas

    groups = {"OFFICERS": [], "OTHERS": []}
    for name in available_for_holidays:
        groups[get_person_group(ranks.get(name, ""))].append(name)

    remaining_extra = extra
    for group_members in groups.values():
        if not group_members or remaining_extra == 0:
            continue
        members_sorted = sorted(
            group_members,
            key=lambda n: (cumulative_stats.get(n, {}).get("total_holidays", 0), rng.random())
        )
        group_extra = min(remaining_extra, len(group_members))
        for i in range(group_extra):
            quotas[members_sorted[i]] = base + 1
            remaining_extra -= 1

    if remaining_extra > 0:
        available = [n for n in available_for_holidays if quotas[n] == base]
        if available:
            available_sorted = sorted(
                available,
                key=lambda n: (cumulative_stats.get(n, {}).get("total_holidays", 0), rng.random())
            )
            for i in range(min(remaining_extra, len(available_sorted))):
                quotas[available_sorted[i]] = base + 1

    return quotas


def compute_friday_quotas_with_history(
    names: list[str],
    total_fridays: int,
    cumulative_stats: dict[str, dict],
    ranks: dict[str, str],
    rng: random.Random,
    leaves: dict[str, set[int]] = None,
    year: int = None,
    month: int = None,
) -> dict[str, int]:
    """Quota Παρασκευών με GROUP-BASED MIN-MAX balancing. Zero για όσους δεν έχουν Παρ."""
    import datetime as dt
    if leaves is None:
        leaves = {}

    available_for_fridays = []
    if year and month:
        _, days_in_month = calendar.monthrange(year, month)
        for name in names:
            leave_days = leaves.get(name, set())
            if any(
                d not in leave_days and dt.date(year, month, d).weekday() == 4
                for d in range(1, days_in_month + 1)
            ):
                available_for_fridays.append(name)
    else:
        available_for_fridays = names[:]

    if not available_for_fridays:
        return {name: 0 for name in names}

    base, extra = divmod(total_fridays, len(available_for_fridays))
    quotas = {name: 0 for name in names}
    for name in available_for_fridays:
        quotas[name] = base
    if extra == 0:
        return quotas

    groups = {"OFFICERS": [], "OTHERS": []}
    for name in available_for_fridays:
        groups[get_person_group(ranks.get(name, ""))].append(name)

    remaining_extra = extra
    for group_members in groups.values():
        if not group_members or remaining_extra == 0:
            continue
        members_sorted = sorted(
            group_members,
            key=lambda n: (cumulative_stats.get(n, {}).get("total_fridays", 0), rng.random())
        )
        group_extra = min(remaining_extra, len(group_members))
        for i in range(group_extra):
            quotas[members_sorted[i]] = base + 1
            remaining_extra -= 1

    if remaining_extra > 0:
        available = [n for n in available_for_fridays if quotas[n] == base]
        if available:
            available_sorted = sorted(
                available,
                key=lambda n: (cumulative_stats.get(n, {}).get("total_fridays", 0), rng.random())
            )
            for i in range(min(remaining_extra, len(available_sorted))):
                quotas[available_sorted[i]] = base + 1

    return quotas


# ------------------------------------------------------------------
# Global (multi-tab)
# ------------------------------------------------------------------

def compute_global_total_quotas(
    year: int,
    month: int,
    all_tabs_data: dict,
    rng: random.Random,
) -> dict[str, int]:
    """
    Global quota με OFFICERS ≤ 4, OTHERS ≤ 5, ιστορική fairness.
    """
    global_people = merge_global_people(all_tabs_data)
    names = list(global_people.keys())
    if not names:
        return {}

    ranks      = {name: pdata["rank"] for name, pdata in global_people.items()}
    cumulative = build_global_cumulative_stats(year, month, global_people)

    officers = [n for n in names if get_person_group(ranks.get(n, "")) == "OFFICERS"]
    others   = [n for n in names if get_person_group(ranks.get(n, "")) != "OFFICERS"]

    quotas: dict[str, int] = {}

    def hist_score(person: str) -> float:
        h = cumulative.get(person, {})
        return (h.get("total_weekdays", 0) * W_SCORE +
                h.get("total_fridays",  0) * F_SCORE +
                h.get("total_holidays", 0) * H_SCORE)

    def assign_group(group_names: list[str], max_cap: int):
        if not group_names:
            return
        base = max_cap - 1
        for p in group_names:
            quotas[p] = base
        ordered     = sorted(group_names, key=lambda p: (hist_score(p), rng.random()))
        plus_count  = len(group_names) // 2
        for p in ordered[:plus_count]:
            quotas[p] = max_cap

    assign_group(officers, 4)
    assign_group(others, 5)
    return quotas


def split_global_quotas_to_tabs(
    year: int,
    month: int,
    all_tabs_data: dict,
    global_total_quotas: dict[str, int],
    rng: random.Random | None = None,
) -> dict[str, dict[str, int]]:
    """Αναλογική κατανομή global quota στα tabs."""
    if rng is None:
        import time
        rng = random.Random(int(time.time() * 1000) % (2**32))
    _, dim     = calendar.monthrange(year, month)
    tab_quotas = {tab_key: {} for tab_key in all_tabs_data.keys()}

    for name, global_q in global_total_quotas.items():
        memberships = []
        for tab_key, tab_data in all_tabs_data.items():
            if name not in tab_data.get("names", []):
                continue
            leaves      = tab_data.get("leaves", {})
            avail_days  = dim - len(leaves.get(name, set()))
            memberships.append((tab_key, avail_days))

        if not memberships:
            continue

        total_avail = sum(max(1, a) for _, a in memberships)
        assigned    = 0
        provisional = []
        for tab_key, avail in memberships:
            q = (global_q * max(1, avail)) // total_avail
            provisional.append([tab_key, q])
            assigned += q

        remainder = global_q - assigned
        rng.shuffle(provisional)
        provisional.sort(
            key=lambda x: next(a for t, a in memberships if t == x[0]),
            reverse=True,
        )
        idx = 0
        while remainder > 0 and provisional:
            provisional[idx % len(provisional)][1] += 1
            remainder -= 1
            idx += 1

        for tab_key, q in provisional:
            tab_quotas[tab_key][name] = q

    # Εξισορρόπηση ώστε κάθε tab να καλύπτει ακριβώς τον μήνα
    # ΣΗΜΑΝΤΙΚΟ: σέβεται το global quota — δεν προσθέτει αν το άτομο
    # έχει ήδη φτάσει το global cap σε όλα τα tabs μαζί.
    for tab_key, tab_data in all_tabs_data.items():
        names = tab_data.get("names", [])
        _, dim = calendar.monthrange(year, month)
        current_sum = sum(tab_quotas[tab_key].get(n, 0) for n in names)
        diff = dim - current_sum

        if diff > 0 and names:
            avail_sorted = names[:]
            rng.shuffle(avail_sorted)
            avail_sorted.sort(
                key=lambda n: dim - len(tab_data.get("leaves", {}).get(n, set())),
                reverse=True,
            )
            i = 0
            stuck = 0
            while diff > 0:
                p = avail_sorted[i % len(avail_sorted)]
                # Έλεγχος global cap: άθροισμα σε όλα τα tabs
                total_assigned = sum(
                    tab_quotas[tk].get(p, 0)
                    for tk in all_tabs_data
                )
                global_cap = global_total_quotas.get(p)
                if global_cap is None or total_assigned < global_cap:
                    tab_quotas[tab_key][p] = tab_quotas[tab_key].get(p, 0) + 1
                    diff -= 1
                    stuck = 0
                else:
                    stuck += 1
                    if stuck >= len(avail_sorted):
                        # Κανείς δεν μπορεί να πάρει άλλη — αναγκαστική ανάθεση
                        tab_quotas[tab_key][p] = tab_quotas[tab_key].get(p, 0) + 1
                        diff -= 1
                        stuck = 0
                i += 1

        elif diff < 0 and names:
            pool = names[:]
            rng.shuffle(pool)
            pool.sort(key=lambda n: tab_quotas[tab_key].get(n, 0), reverse=True)
            i = 0
            while diff < 0 and pool:
                p = pool[i % len(pool)]
                if tab_quotas[tab_key].get(p, 0) > 0:
                    tab_quotas[tab_key][p] -= 1
                    diff += 1
                i += 1

    return tab_quotas


# ------------------------------------------------------------------
# Normalize / auto-max helpers
# ------------------------------------------------------------------

def normalize_quotas_with_max(
    names: list[str],
    quotas_total: dict[str, int],
    days_in_month: int,
    max_caps: dict[str, int] | None,
) -> dict[str, int]:
    if not max_caps:
        return {nm: int(quotas_total.get(nm, 0)) for nm in names}

    q = {nm: int(quotas_total.get(nm, 0)) for nm in names}
    for nm in names:
        mx = max_caps.get(nm)
        if mx is None:
            continue
        try:
            mx_i = int(mx)
        except Exception:
            continue
        if mx_i > 0:
            q[nm] = min(q[nm], mx_i)

    remaining = days_in_month - sum(q.values())
    if remaining < 0:
        raise ScheduleError("Τα MAX όρια οδηγούν σε υπερανάθεση.", details="Έλεγξε τα MAX.")

    def headroom(nm: str) -> int:
        mx = max_caps.get(nm)
        if mx is None:
            return 10**9
        try:
            mx_i = int(mx)
        except Exception:
            return 10**9
        return 10**9 if mx_i <= 0 else mx_i - q[nm]

    while remaining > 0:
        candidates = [nm for nm in names if headroom(nm) > 0]
        if not candidates:
            raise ScheduleError("Τα MAX όρια είναι πολύ χαμηλά.", details="Αυξησε τα MAX.")
        candidates.sort(key=lambda nm: (-headroom(nm), q[nm]))
        q[candidates[0]] += 1
        remaining -= 1

    return q


def repair_total_quotas_for_availability(
    names: list[str],
    quotas_total: dict[str, int],
    days_in_month: int,
    leaves: dict[str, set[int]],
    max_caps: dict[str, int] | None = None,
    log_cb=None,
) -> dict[str, int]:
    """
    Διορθώνει τα TOTAL quotas ώστε να μην υπάρχει προφανές τοπικό αδιέξοδο
    από τα ίδια τα leave patterns.

    Ιδέα:
    για τα πιο δύσκολα prefix-σύνολα ημερών, η ένωση των διαθέσιμων ατόμων
    πρέπει να έχει άθροισμα quota τουλάχιστον ίσο με το πλήθος αυτών των ημερών.
    """
    if log_cb is None:
        log_cb = lambda m: None

    repaired = {nm: int(quotas_total.get(nm, 0)) for nm in names}
    open_days = list(range(1, days_in_month + 1))
    static_cands_by_day = {
        d: [p for p in names if d not in leaves.get(p, set())]
        for d in open_days
    }
    static_caps = {
        p: min(
            int(max_caps.get(p, days_in_month)) if max_caps else days_in_month,
            sum(1 for d in open_days if p in static_cands_by_day[d]),
        )
        for p in names
    }

    constraint_demands: dict[frozenset[str], int] = {}

    def register_constraint(people: set[str], demand: int) -> None:
        if not people or demand <= 0:
            return
        key = frozenset(people)
        if demand > constraint_demands.get(key, 0):
            constraint_demands[key] = demand

    for start in open_days:
        people_union: set[str] = set()
        for end in range(start, days_in_month + 1):
            people_union.update(static_cands_by_day[end])
            register_constraint(people_union, end - start + 1)

    hardest_days = sorted(open_days, key=lambda d: (len(static_cands_by_day[d]), d))
    prefix_people: set[str] = set()
    for idx, day in enumerate(hardest_days):
        prefix_people.update(static_cands_by_day[day])
        register_constraint(prefix_people, idx + 1)

    constraints = sorted(
        constraint_demands.items(),
        key=lambda item: (len(item[0]), -item[1], sorted(item[0])),
    )

    def total_for(group: frozenset[str]) -> int:
        return sum(repaired.get(p, 0) for p in group)

    def transfer_is_safe(donor: str, recipient: str) -> bool:
        if repaired.get(donor, 0) <= 0:
            return False
        if donor == recipient:
            return False
        for group, demand in constraints:
            delta = 0
            if donor in group and recipient not in group:
                delta = -1
            elif recipient in group and donor not in group:
                delta = 1
            if total_for(group) + delta < demand:
                return False
        return True

    max_rounds = max(1, len(constraints) * max(1, len(names)))
    for _ in range(max_rounds):
        progress = False
        for group, demand in constraints:
            shortage = demand - total_for(group)
            if shortage <= 0:
                continue

            recipients = sorted(
                [p for p in group if repaired.get(p, 0) < static_caps.get(p, 0)],
                key=lambda p: (repaired.get(p, 0), -static_caps.get(p, 0), p),
            )
            if not recipients:
                continue

            for recipient in recipients:
                while shortage > 0 and repaired.get(recipient, 0) < static_caps.get(recipient, 0):
                    safe_donors = sorted(
                        [p for p in names if p not in group and transfer_is_safe(p, recipient)],
                        key=lambda p: (repaired.get(p, 0), p),
                        reverse=True,
                    )
                    if not safe_donors:
                        break

                    donor = safe_donors[0]
                    repaired[donor] -= 1
                    repaired[recipient] = repaired.get(recipient, 0) + 1
                    shortage -= 1
                    progress = True

                if shortage <= 0:
                    break

        if not progress:
            break

    return repaired


def compute_auto_max_from_leaves(
    names: list[str],
    days_in_month: int,
    leaves: dict[str, set[int]],
    min_gap: int = 2,
    log_cb=None,
) -> tuple[dict[str, int], dict[str, int]]:
    """
    Αυτόματος υπολογισμός MAX από διαθεσιμότητα.
    Επιστρέφει (auto_max, custom_min_gap).
    """
    if log_cb is None:
        log_cb = lambda m: print(m)

    auto_max        = {}
    custom_min_gap  = {}
    GAP1_THRESHOLD  = 3

    for name in names:
        leave_days    = leaves.get(name, set())
        available_days = [d for d in range(1, days_in_month + 1) if d not in leave_days]
        num_available  = len(available_days)

        if num_available == 0:
            raise ScheduleError(
                f"Αδύνατο πρόγραμμα: {name}",
                details=f"Ο/Η {name} δεν έχει καμία διαθέσιμη μέρα (όλες άδειες)!"
            )

        max_with_gap2 = (num_available + min_gap) // (min_gap + 1)
        max_with_gap1 = (num_available + 1) // 2

        if num_available < days_in_month / GAP1_THRESHOLD:
            if max_with_gap1 > max_with_gap2:
                auto_max[name]       = max_with_gap1
                custom_min_gap[name] = 1
                log_cb(f"  🔒 AUTO-MAX: {name} έχει μόνο {num_available} διαθέσιμες μέρες → MAX={max_with_gap1} (με GAP=1)")
            else:
                auto_max[name]       = max_with_gap2
                custom_min_gap[name] = 2
                log_cb(f"  🔒 AUTO-MAX: {name} έχει μόνο {num_available} διαθέσιμες μέρες → MAX={max_with_gap2} (με GAP=2)")
        elif num_available < days_in_month / 2:
            auto_max[name]       = max_with_gap2
            custom_min_gap[name] = 2
            log_cb(f"  🔒 AUTO-MAX: {name} έχει {num_available} διαθέσιμες μέρες → MAX={max_with_gap2} (με GAP=2)")
        else:
            custom_min_gap[name] = min_gap

    return auto_max, custom_min_gap


def assign_max_constrained_people(
    names: list[str],
    year: int,
    month: int,
    extra_holidays: set[int],
    leaves: dict[str, set[int]],
    max_caps: dict[str, int],
    custom_min_gap: dict[str, int] | None = None,
    log_cb=None,
) -> tuple[dict[int, str], dict[str, int]]:
    """
    Pre-ανάθεση ατόμων με MAX constraint.
    Επιστρέφει (schedule, remaining_quotas).
    """
    import random as _rnd
    import time as _tm

    if log_cb is None:
        log_cb = lambda m: print(m)
    if custom_min_gap is None:
        custom_min_gap = {}

    _, days_in_month = calendar.monthrange(year, month)
    all_days         = list(range(1, days_in_month + 1))
    schedule         = {}
    remaining_quotas = {}

    max_people    = []
    normal_people = []

    for name in names:
        if name in max_caps and max_caps[name] is not None:
            try:
                max_val = int(max_caps[name])
                if max_val > 0:
                    max_people.append((name, max_val))
                    remaining_quotas[name] = 0
                    continue
            except Exception:
                continue
        normal_people.append(name)
        remaining_quotas[name] = 0

    if not max_people:
        log_cb("  ℹ️  Κανένα άτομο με MAX constraint")
        return {}, remaining_quotas

    log_cb("  🎯 ΦΑΣΗ 0: Ανάθεση MAX-constrained ατόμων")

    for person, max_services in max_people:
        person_min_gap = custom_min_gap.get(person, 2)
        log_cb(f"    Ανάθεση {person}: MAX={max_services}, GAP={person_min_gap}")

        leave_days = leaves.get(person, set())
        available  = [d for d in all_days if d not in leave_days and d not in schedule]

        if len(available) < max_services:
            raise ScheduleError(
                f"Αδύνατο MAX για {person}",
                details=f"{person} έχει MAX={max_services} αλλά μόνο {len(available)} διαθέσιμες μέρες!"
            )

        forced_pattern = []
        for day in available:
            if all(abs(day - ad) > person_min_gap for ad in forced_pattern):
                forced_pattern.append(day)
                if len(forced_pattern) == max_services:
                    break

        if len(forced_pattern) != max_services:
            raise ScheduleError(
                f"Αδύνατο pattern για {person}",
                details=f"{person} MAX={max_services}, GAP={person_min_gap} — δεν χωράνε στις {len(available)} διαθέσιμες μέρες!"
            )

        log_cb(f"      ✅ Pattern με GAP={person_min_gap}: {forced_pattern}")
        for day in forced_pattern:
            schedule[day] = person

    days_used      = len(schedule)
    days_remaining = days_in_month - days_used
    if normal_people:
        base, extra = divmod(days_remaining, len(normal_people))
        rng     = _rnd.Random(int(_tm.time() * 1000) % (2**32))
        shuffled = normal_people[:]
        rng.shuffle(shuffled)
        plus = set(shuffled[:extra])
        for name in normal_people:
            remaining_quotas[name] = base + (1 if name in plus else 0)

    log_cb(f"    ✅ Pre-assigned: {days_used} μέρες")
    log_cb(f"    📊 Υπόλοιπα quotas: {remaining_quotas}")
    return schedule, remaining_quotas


def compute_person_total_history(cumulative_stats: dict[str, dict]) -> int:
    return (
        cumulative_stats.get("total_weekdays", 0) +
        cumulative_stats.get("total_fridays",  0) +
        cumulative_stats.get("total_holidays", 0)
    )
