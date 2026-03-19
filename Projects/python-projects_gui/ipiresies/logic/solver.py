# solver.py
# Ενιαίος backtracking solver (hardest-days-first)
# Και compute_schedule_metadata

import calendar
import datetime as dt
import random
import time

from logic.constants import (
    MIN_GAP_STRICT, W_SCORE, F_SCORE, H_SCORE,
    SOLVER_MAX_TIME, SOLVER_MAX_RECURSION_MULT,
)
from logic.date_helpers import ScheduleError, day_bucket


def compute_schedule_metadata(
    schedule: dict[int, str],
    year: int,
    month: int,
    extra_holidays: set[int],
) -> dict:
    """Υπολογίζει τα στατιστικά (WEEKDAY/FRIDAY/HOLIDAY, score, dates)."""
    meta = {}
    for day, person in schedule.items():
        if person not in meta:
            meta[person] = {
                "WEEKDAY": 0, "FRIDAY": 0, "HOLIDAY": 0,
                "total": 0, "score": 0.0,
                "weekday_dates": [], "friday_dates": [], "holiday_dates": [],
            }
        date_obj = dt.date(year, month, day)
        weekday_num = date_obj.weekday()
        bucket = day_bucket(year, month, day, extra_holidays)

        if bucket == "HOLIDAY":
            meta[person]["HOLIDAY"] += 1
            meta[person]["holiday_dates"].append(day)
            meta[person]["score"] += H_SCORE
        elif weekday_num == 4:
            meta[person]["FRIDAY"] += 1
            meta[person]["friday_dates"].append(day)
            meta[person]["score"] += F_SCORE
        else:
            meta[person]["WEEKDAY"] += 1
            meta[person]["weekday_dates"].append(day)
            meta[person]["score"] += W_SCORE
        meta[person]["total"] += 1
    return meta


def solve_with_two_phase_backtracking(
    names: list[str],
    year: int,
    month: int,
    extra_holidays: set[int],
    leaves: dict[str, set[int]],
    quotas: dict[str, int],
    holiday_quotas: dict[str, int],
    friday_quotas: dict[str, int] | None = None,
    preferences: dict[str, set[int]] | None = None,
    min_gap: int = 2,
    custom_min_gap: dict[str, int] | None = None,
    pre_assigned: dict[int, str] | None = None,
    log_cb=None,
    ignore_weekend_pair_days: set[int] | None = None,
    enforce_holiday_quota: bool = True,
    relaxed_constraint_days: set[int] | None = None,
    relaxed_total_tolerance: int = 0,
    relaxed_gap_value: int | None = None,
    tab_key: str = "AYDM",
    max_time: float | None = None,
    max_recursion_mult: int | None = None,
) -> tuple[dict[int, str], dict, str]:
    """
    Ενιαίος solver.
    Αναθέτει όλες τις μέρες μαζί, από τις πιο δύσκολες προς τις πιο εύκολες.
    Το interface μένει ίδιο για να μη χαλάσει η υπόλοιπη λογική του project.
    """
    if log_cb is None:
        log_cb = lambda m: print(m)
    if preferences is None:
        preferences = {}
    if custom_min_gap is None:
        custom_min_gap = {}
    if pre_assigned is None:
        pre_assigned = {}
    if friday_quotas is None:
        friday_quotas = {p: 0 for p in names}
    if relaxed_constraint_days is None:
        relaxed_constraint_days = set()
    else:
        relaxed_constraint_days = set(relaxed_constraint_days)

    log_cb("🔎 Ενιαίος solver (όλες οι μέρες μαζί, hardest-days-first)...")

    _, days_in_month = calendar.monthrange(year, month)
    all_days = list(range(1, days_in_month + 1))
    available_days = [d for d in all_days if d not in pre_assigned]
    day_types = {day: day_bucket(year, month, day, extra_holidays) for day in all_days}

    def is_holiday_day(day: int) -> bool:
        return day_types.get(day) == "HOLIDAY"

    def is_weekday_day(day: int) -> bool:
        return day_types.get(day) == "WEEKDAY"

    def is_friday_day(day: int) -> bool:
        return is_weekday_day(day) and dt.date(year, month, day).weekday() == 4

    def score_for_day(day: int) -> float:
        if is_holiday_day(day):
            return H_SCORE
        if dt.date(year, month, day).weekday() == 4:
            return F_SCORE
        return W_SCORE

    # Keep explicit day buckets available for the existing solver logic below.
    holiday_days = [d for d in available_days if is_holiday_day(d)]
    weekdays = [d for d in available_days if is_weekday_day(d)]
    log_cb(f"  📌 Προανατεθειμένες μέρες: {len(pre_assigned)}")
    log_cb(f"  📌 Αργίες: {len(holiday_days)} μέρες")
    log_cb(f"  📌 Καθημερινές: {len(weekdays)} μέρες")

    def get_min_gap(person: str) -> int:
        return custom_min_gap.get(person, min_gap)

    def effective_gap(person: str, day1: int, day2: int) -> int:
        base_gap = get_min_gap(person)
        if relaxed_gap_value is not None and (day1 in relaxed_constraint_days or day2 in relaxed_constraint_days):
            return min(base_gap, relaxed_gap_value)
        return base_gap

    def gap_conflicts_for_person(person: str, day: int, assigned: dict[int, str]) -> list[int]:
        conflicts = []
        for other_day, other_person in assigned.items():
            if other_person != person:
                continue
            if abs(other_day - day) <= effective_gap(person, day, other_day):
                conflicts.append(other_day)
        return sorted(conflicts)

    def weekend_pair_relaxed(day1: int, day2: int) -> bool:
        if ignore_weekend_pair_days is not None and (day1 in ignore_weekend_pair_days or day2 in ignore_weekend_pair_days):
            return True
        if day1 in relaxed_constraint_days or day2 in relaxed_constraint_days:
            return True
        return False

    def is_forbidden_weekend_pair(day1: int, day2: int) -> bool:
        """Service-specific Fri/Sat gap rules."""
        if day1 >= day2:
            return False
        gap_days = day2 - day1
        if tab_key in ("AYDM", "PYLI"):
            req_gap_fri, req_gap_sat = 3, 4
        elif tab_key in ("FKX", "BAYDM"):
            req_gap_fri, req_gap_sat = 4, 5
        else:
            return False
        try:
            weekday1 = dt.date(year, month, day1).weekday()
        except ValueError:
            return False
        if weekday1 == 4:
            return gap_days <= req_gap_fri
        if weekday1 == 5:
            return gap_days <= req_gap_sat
        return False

    def total_used_for_person(person: str, partial: dict[int, str]) -> int:
        return sum(1 for assigned_person in partial.values() if assigned_person == person)

    def candidates_for_day(day: int, partial: dict[int, str]) -> list[str]:
        cands = []
        full_assigned = {**pre_assigned, **partial}
        for person in names:
            if day in leaves.get(person, set()):
                continue
            if total_used_for_person(person, partial) >= int(quotas.get(person, 0)):
                continue
            if gap_conflicts_for_person(person, day, full_assigned):
                continue
            ok = True
            for other_day, other_person in full_assigned.items():
                if other_person != person:
                    continue
                if weekend_pair_relaxed(other_day, day):
                    continue
                if is_forbidden_weekend_pair(other_day, day) or is_forbidden_weekend_pair(day, other_day):
                    ok = False
                    break
            if ok:
                cands.append(person)
        return cands

    def explain_day_exclusions(day: int, partial: dict[int, str]) -> dict[str, str]:
        explanations = {}
        full_assigned = {**pre_assigned, **partial}
        for person in names:
            if day in leaves.get(person, set()):
                explanations[person] = "leave"
                continue
            total_used = total_used_for_person(person, partial)
            if total_used >= int(quotas.get(person, 0)):
                explanations[person] = f"Συμπληρώθηκε total quota ({total_used}/{int(quotas.get(person, 0))})"
                continue
            gap_conflicts = gap_conflicts_for_person(person, day, full_assigned)
            if gap_conflicts:
                explanations[person] = f"gap conflict with days {gap_conflicts}"
                continue
            weekend_conflicts = []
            for other_day, other_person in full_assigned.items():
                if other_person != person:
                    continue
                if weekend_pair_relaxed(other_day, day):
                    continue
                if is_forbidden_weekend_pair(other_day, day) or is_forbidden_weekend_pair(day, other_day):
                    weekend_conflicts.append(other_day)
            if weekend_conflicts:
                explanations[person] = f"weekend rule conflict with days {sorted(weekend_conflicts)}"
                continue
            explanations[person] = "available"
        return explanations

    assignment_projection_cache: dict[tuple[tuple[int, str], ...], tuple[bool, int, int, int]] = {}

    def assignment_projection_metrics(partial: dict[int, str]) -> tuple[bool, int, int, int]:
        key = tuple(sorted(partial.items()))
        if key in assignment_projection_cache:
            return assignment_projection_cache[key]

        remaining_days = [d for d in available_days if d not in partial]
        if not remaining_days:
            metrics = (True, 10**6, 10**6, 0)
            assignment_projection_cache[key] = metrics
            return metrics

        remaining_total = {
            person: max(0, int(quotas.get(person, 0)) - total_used_for_person(person, partial))
            for person in names
        }
        if sum(remaining_total.values()) < len(remaining_days):
            metrics = (False, -10**6, -10**6, 10**6)
            assignment_projection_cache[key] = metrics
            return metrics

        cands_by_day: dict[int, list[str]] = {}
        possible_by_person = {person: 0 for person in names}
        for day in remaining_days:
            cands = candidates_for_day(day, partial)
            if not cands:
                metrics = (False, -10**6, -10**6, 10**6)
                assignment_projection_cache[key] = metrics
                return metrics
            cands_by_day[day] = cands
            for person in cands:
                possible_by_person[person] += 1

        for person in names:
            if remaining_total[person] > possible_by_person[person]:
                metrics = (False, -10**6, -10**6, 10**6)
                assignment_projection_cache[key] = metrics
                return metrics

        ordered_days = sorted(
            remaining_days,
            key=lambda day: (len(cands_by_day[day]), day),
        )
        min_prefix_slack = 10**6
        for idx in range(len(ordered_days)):
            prefix_days = ordered_days[:idx + 1]
            prefix_people = {person for day in prefix_days for person in cands_by_day[day]}
            prefix_capacity = sum(remaining_total[person] for person in prefix_people)
            prefix_slack = prefix_capacity - len(prefix_days)
            min_prefix_slack = min(min_prefix_slack, prefix_slack)
            if prefix_slack < 0:
                metrics = (False, min_prefix_slack, -10**6, 10**6)
                assignment_projection_cache[key] = metrics
                return metrics

        all_remaining_days = sorted(remaining_days)
        min_window_slack = 10**6
        for start in range(len(all_remaining_days)):
            window_people: set[str] = set()
            for end in range(start, len(all_remaining_days)):
                window_day = all_remaining_days[end]
                window_people.update(cands_by_day[window_day])
                window_len = end - start + 1
                window_capacity = sum(remaining_total[person] for person in window_people)
                window_slack = window_capacity - window_len
                min_window_slack = min(min_window_slack, window_slack)
                if window_slack < 0:
                    metrics = (False, min_prefix_slack, min_window_slack, 10**6)
                    assignment_projection_cache[key] = metrics
                    return metrics

        singleton_count = sum(1 for cands in cands_by_day.values() if len(cands) == 1)
        metrics = (True, min_prefix_slack, min_window_slack, singleton_count)
        assignment_projection_cache[key] = metrics
        return metrics

    def choose_next_day(partial: dict[int, str]) -> tuple[int | None, list[str]]:
        remaining_days = [d for d in available_days if d not in partial]
        best_day = None
        best_cands = []
        best_key = None
        for day in remaining_days:
            cands = candidates_for_day(day, partial)
            key = (len(cands), day)
            if best_key is None or key < best_key:
                best_key = key
                best_day = day
                best_cands = cands
        return best_day, best_cands

    _max_time = max_time if max_time is not None else SOLVER_MAX_TIME
    _recursion_mult = max_recursion_mult if max_recursion_mult is not None else SOLVER_MAX_RECURSION_MULT
    max_recursion_depth = len(available_days) * _recursion_mult

    def try_one_phase() -> tuple[dict[int, str] | None, dict[str, float], int]:
        current_scores = {person: 0.0 for person in names}
        for pre_day, pre_person in pre_assigned.items():
            if pre_person in current_scores:
                current_scores[pre_person] += score_for_day(pre_day)
        recursion_cutoff_count = [0]
        schedule: dict[int, str] = {}
        start_time = time.time()
        assignment_projection_cache.clear()

        def backtrack(depth: int = 0) -> bool:
            if time.time() - start_time > _max_time:
                return False
            if depth > max_recursion_depth:
                recursion_cutoff_count[0] += 1
                return False

            feasible, _, _, _ = assignment_projection_metrics(schedule)
            if not feasible:
                return False

            if len(schedule) == len(available_days):
                return True

            day, cands = choose_next_day(schedule)
            if day is None or not cands:
                return False

            def candidate_sort_key(person: str):
                simulated_schedule = dict(schedule)
                simulated_schedule[day] = person
                feasible2, min_prefix_slack, min_window_slack, singleton_count = assignment_projection_metrics(simulated_schedule)
                remaining_total_need = int(quotas.get(person, 0)) - total_used_for_person(person, schedule)
                return (
                    1 if feasible2 else 0,
                    min_window_slack,
                    min_prefix_slack,
                    remaining_total_need,
                    1 if day in preferences.get(person, set()) else 0,
                    -current_scores[person],
                    -singleton_count,
                    random.random(),
                )

            cands.sort(key=candidate_sort_key, reverse=True)

            for person in cands:
                schedule[day] = person
                current_scores[person] += score_for_day(day)

                if backtrack(depth + 1):
                    return True

                current_scores[person] -= score_for_day(day)
                del schedule[day]

            return False

        success = backtrack(0)
        return (dict(schedule) if success else None), current_scores, recursion_cutoff_count[0]

    solved_schedule, current_scores, recursion_cutoff_hits = try_one_phase()

    if solved_schedule is None:
        hardest_days = sorted(
            available_days,
            key=lambda day: (len(candidates_for_day(day, {})), day),
        )
        holiday_hard = sum(1 for day in hardest_days[:5] if day in holiday_days)
        weekday_hard = min(5, len(hardest_days)) - holiday_hard
        title = "Αδύνατη κατανομή αργιών" if holiday_hard >= weekday_hard else "Αδύνατη κατανομή καθημερινών"

        details = "Δεν μπορούν να κατανεμηθούν οι μέρες.\n"
        details += f"Ανοιχτές μέρες: {len(available_days)}\n"
        details += f"Quota total: {quotas}\n"
        if recursion_cutoff_hits > 0:
            details += (
                f"\nΟ περιορισμός recursion χτύπησε {recursion_cutoff_hits} φορές "
                f"(max depth: {max_recursion_depth})\n"
            )
        details += "\nΠιο δύσκολες μέρες:\n"
        for day in hardest_days[:5]:
            cands = candidates_for_day(day, {})
            day_name = dt.date(year, month, day).strftime("%A")
            bucket = day_bucket(year, month, day, extra_holidays)
            details += f"  Μέρα {day} ({day_name}, {bucket}): {len(cands)} υποψήφιοι"
            if len(cands) <= 4:
                details += f" - {cands}"
            details += "\n"
            blocked = [
                f"{name}: {reason}"
                for name, reason in explain_day_exclusions(day, {}).items()
                if reason != "available"
            ]
            if blocked:
                details += f"    Αποκλεισμοί: {'; '.join(blocked)}\n"
        raise ScheduleError(title, details=details)

    def full_schedule_valid(core_schedule: dict[int, str]) -> bool:
        full = {**pre_assigned, **core_schedule}
        for day, person in core_schedule.items():
            if day in leaves.get(person, set()):
                return False
            person_days = sorted(d for d, p in full.items() if p == person)
            for idx, d1 in enumerate(person_days):
                for d2 in person_days[idx + 1:]:
                    if abs(d2 - d1) <= effective_gap(person, d1, d2):
                        return False
                    if not weekend_pair_relaxed(d1, d2):
                        if is_forbidden_weekend_pair(d1, d2) or is_forbidden_weekend_pair(d2, d1):
                            return False
        return True

    def objective_tuple(core_schedule: dict[int, str]) -> tuple[float, float, float, float, float, float, float]:
        full = {**pre_assigned, **core_schedule}
        meta_obj = compute_schedule_metadata(full, year, month, extra_holidays)
        holiday_counts = [meta_obj.get(person, {}).get("HOLIDAY", 0) for person in names]
        friday_counts = [meta_obj.get(person, {}).get("FRIDAY", 0) for person in names]
        scores = [meta_obj.get(person, {}).get("score", 0.0) for person in names]
        if not scores:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        holiday_spread = max(holiday_counts) - min(holiday_counts) if holiday_counts else 0
        friday_spread = max(friday_counts) - min(friday_counts) if friday_counts else 0
        holiday_violation = max(0, holiday_spread - 1)
        friday_violation = max(0, friday_spread - 1)
        spread_obj = max(scores) - min(scores)
        mean = sum(scores) / len(scores)
        sq = sum((s - mean) ** 2 for s in scores)
        return (
            float(holiday_violation),
            float(friday_violation),
            spread_obj,
            sq,
            max(scores),
            float(holiday_spread),
            float(friday_spread),
        )

    def improve_schedule_locally(core_schedule: dict[int, str]) -> tuple[dict[int, str], int, int]:
        improved = dict(core_schedule)
        pair_swaps = 0
        three_cycles = 0
        while True:
            base_obj = objective_tuple(improved)
            best_move = None
            best_obj = base_obj
            days = sorted(improved)

            # 1) Pair swaps
            for i, d1 in enumerate(days):
                if d1 in pre_assigned:
                    continue
                p1 = improved[d1]
                for d2 in days[i + 1:]:
                    if d2 in pre_assigned:
                        continue
                    p2 = improved[d2]
                    if p1 == p2:
                        continue
                    trial = dict(improved)
                    trial[d1], trial[d2] = p2, p1
                    if not full_schedule_valid(trial):
                        continue
                    trial_obj = objective_tuple(trial)
                    if trial_obj < best_obj:
                        best_obj = trial_obj
                        best_move = ("swap", d1, d2)

            # 2) Three-way cycles
            for i, d1 in enumerate(days):
                if d1 in pre_assigned:
                    continue
                p1 = improved[d1]
                for j in range(i + 1, len(days)):
                    d2 = days[j]
                    if d2 in pre_assigned:
                        continue
                    p2 = improved[d2]
                    if p2 == p1:
                        continue
                    for k in range(j + 1, len(days)):
                        d3 = days[k]
                        if d3 in pre_assigned:
                            continue
                        p3 = improved[d3]
                        if len({p1, p2, p3}) < 3:
                            continue

                        # Cycle A: d1<-p2, d2<-p3, d3<-p1
                        trial_a = dict(improved)
                        trial_a[d1], trial_a[d2], trial_a[d3] = p2, p3, p1
                        if full_schedule_valid(trial_a):
                            trial_obj = objective_tuple(trial_a)
                            if trial_obj < best_obj:
                                best_obj = trial_obj
                                best_move = ("cycle", d1, d2, d3, p2, p3, p1)

                        # Cycle B: d1<-p3, d2<-p1, d3<-p2
                        trial_b = dict(improved)
                        trial_b[d1], trial_b[d2], trial_b[d3] = p3, p1, p2
                        if full_schedule_valid(trial_b):
                            trial_obj = objective_tuple(trial_b)
                            if trial_obj < best_obj:
                                best_obj = trial_obj
                                best_move = ("cycle", d1, d2, d3, p3, p1, p2)

            if best_move is None:
                break

            if best_move[0] == "swap":
                _, d1, d2 = best_move
                improved[d1], improved[d2] = improved[d2], improved[d1]
                pair_swaps += 1
            else:
                _, d1, d2, d3, np1, np2, np3 = best_move
                improved[d1], improved[d2], improved[d3] = np1, np2, np3
                three_cycles += 1

        return improved, pair_swaps, three_cycles

    solved_schedule, pair_swaps_applied, three_cycles_applied = improve_schedule_locally(solved_schedule)

    final_schedule = {**pre_assigned, **solved_schedule}
    holidays_assigned = sum(1 for day in solved_schedule if day in holiday_days)
    weekdays_assigned = sum(1 for day in solved_schedule if day in weekdays)

    log_cb("  ✅ Οι μέρες κατανεμήθηκαν επιτυχώς")
    final_meta = compute_schedule_metadata(final_schedule, year, month, extra_holidays)
    final_scores = [m["score"] for m in final_meta.values()]
    spread = max(final_scores) - min(final_scores) if final_scores else 0.0
    log_cb(f"  📊 Τελικό score spread: {spread:.2f}")

    if preferences:
        total_prefs = sum(len(days) for days in preferences.values())
        matched_prefs = sum(
            1 for day, person in final_schedule.items()
            if day in preferences.get(person, set())
        )
        if total_prefs > 0:
            log_cb(f"  📌 Προτιμήσεις: {matched_prefs}/{total_prefs} ικανοποιήθηκαν ({matched_prefs/total_prefs*100:.1f}%)")

    solve_info = {
        "solver": "One-Phase Hardest-Days Backtracking",
        "pre_assigned": len(pre_assigned),
        "holidays_assigned": holidays_assigned,
        "weekdays_assigned": weekdays_assigned,
        "score_spread": spread,
        "min_gap_used": {name: get_min_gap(name) for name in names},
        "relaxed_constraint_days": sorted(relaxed_constraint_days),
        "post_optimized_swaps": pair_swaps_applied,
        "post_optimized_three_cycles": three_cycles_applied,
    }
    return final_schedule, solve_info, "One-Phase"
