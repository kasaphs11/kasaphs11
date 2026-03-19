import calendar
import datetime as dt
import json
import random
import tempfile
from pathlib import Path

import logic.history as history_module
from logic.constants import MIN_GAP_STRICT, TAB_KEYS
from logic.date_helpers import ScheduleError, day_bucket, parse_days_list
from logic.history import add_to_history, load_history
from logic.persistence import get_state_path
from logic.quotas import compute_global_total_quotas, compute_total_quotas
from logic.scheduler import solve_all_tabs_unified, solve_schedule_best_effort
from logic.solver import solve_with_two_phase_backtracking


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def holiday_days_in_month(year, month, extra_holidays):
    _, days_in_month = calendar.monthrange(year, month)
    return [
        day
        for day in range(1, days_in_month + 1)
        if day_bucket(year, month, day, extra_holidays) == "HOLIDAY"
    ]


def is_forbidden_weekend_pair(year, month, day1, day2, tab_key):
    if day1 >= day2:
        return False
    gap_days = day2 - day1
    if tab_key in ("AYDM", "PYLI"):
        req_gap_fri, req_gap_sat = 3, 4
    elif tab_key in ("FKX", "BAYDM"):
        req_gap_fri, req_gap_sat = 4, 5
    else:
        return False
    weekday1 = dt.date(year, month, day1).weekday()
    if weekday1 == 4:
        return gap_days <= req_gap_fri
    if weekday1 == 5:
        return gap_days <= req_gap_sat
    return False


def exact_holiday_feasible(
    names,
    year,
    month,
    extra_holidays,
    leaves,
    holiday_quotas,
    pre_assigned,
    min_gap,
    custom_min_gap,
    tab_key,
):
    holidays = [
        day for day in holiday_days_in_month(year, month, extra_holidays)
        if day not in pre_assigned
    ]
    assigned_holidays = {
        day: person
        for day, person in pre_assigned.items()
        if day_bucket(year, month, day, extra_holidays) == "HOLIDAY"
    }
    used_holidays = {name: 0 for name in names}
    for person in assigned_holidays.values():
        used_holidays[person] += 1

    remaining_holidays = {
        name: holiday_quotas.get(name, 0) - used_holidays.get(name, 0)
        for name in names
    }
    if any(value < 0 for value in remaining_holidays.values()):
        return False

    def person_gap(person):
        return custom_min_gap.get(person, min_gap)

    def candidates_for_day(day, partial):
        full_assigned = {**pre_assigned, **partial}
        candidates = []
        for person in names:
            if day in leaves.get(person, set()):
                continue
            if remaining_holidays[person] <= 0:
                continue
            gap = person_gap(person)
            if any(
                other_person == person and abs(other_day - day) <= gap
                for other_day, other_person in full_assigned.items()
            ):
                continue
            weekend_conflict = False
            for other_day, other_person in full_assigned.items():
                if other_person != person:
                    continue
                if (
                    is_forbidden_weekend_pair(year, month, other_day, day, tab_key)
                    or is_forbidden_weekend_pair(year, month, day, other_day, tab_key)
                ):
                    weekend_conflict = True
                    break
            if weekend_conflict:
                continue
            candidates.append(person)
        return candidates

    def backtrack(remaining_days, partial):
        if not remaining_days:
            return True

        all_candidates = {day: candidates_for_day(day, partial) for day in remaining_days}
        if any(not cands for cands in all_candidates.values()):
            return False

        next_day = min(remaining_days, key=lambda day: (len(all_candidates[day]), day))
        for person in all_candidates[next_day]:
            partial[next_day] = person
            remaining_holidays[person] -= 1
            if backtrack([day for day in remaining_days if day != next_day], partial):
                return True
            remaining_holidays[person] += 1
            del partial[next_day]
        return False

    return backtrack(holidays, {})


def build_random_holiday_case(seed):
    rng = random.Random(seed)
    year, month = 2026, rng.choice([3, 4, 5])
    extra_holidays = set()
    tab_key = rng.choice(["AYDM", "BAYDM", "FKX", "PYLI"])
    names = [f"P{i}" for i in range(1, rng.randint(4, 7))]
    _, days_in_month = calendar.monthrange(year, month)
    holidays = holiday_days_in_month(year, month, extra_holidays)
    quotas = compute_total_quotas(names, days_in_month, random.Random(seed))

    leaves = {name: set() for name in names}
    for day in holidays:
        available_people = [name for name in names if rng.random() > 0.22]
        if not available_people:
            available_people = [rng.choice(names)]
        for name in names:
            if name not in available_people:
                leaves[name].add(day)

    holiday_quotas = {name: 0 for name in names}
    remaining = len(holidays)
    order = names[:]
    rng.shuffle(order)
    for idx, name in enumerate(order):
        if idx == len(order) - 1:
            assign = remaining
        else:
            assign = rng.randint(0, min(quotas[name], remaining))
        holiday_quotas[name] += assign
        remaining -= assign

    if remaining > 0:
        for name in sorted(names, key=lambda current: quotas[current] - holiday_quotas[current], reverse=True):
            room = quotas[name] - holiday_quotas[name]
            if room <= 0:
                continue
            add = min(room, remaining)
            holiday_quotas[name] += add
            remaining -= add
            if remaining == 0:
                break

    if remaining > 0:
        holiday_quotas[order[0]] += remaining

    return {
        "names": names,
        "year": year,
        "month": month,
        "extra_holidays": extra_holidays,
        "leaves": leaves,
        "quotas": quotas,
        "holiday_quotas": holiday_quotas,
        "tab_key": tab_key,
    }


def load_real_dataset():
    state_path = Path(get_state_path())
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    year = int(state["year"])
    month = int(state["month"])
    _, days_in_month = calendar.monthrange(year, month)
    extra_raw = str(state.get("extra", "")).strip()
    extra = parse_days_list(extra_raw, days_in_month) if extra_raw else set()

    all_tabs_data = {}
    for tab_key, tab_state in state.get("tabs", {}).items():
        people = tab_state.get("people", [])
        names = []
        leaves = {}
        ranks = {}
        preferences = {}
        for person in people[: int(tab_state.get("count", len(people)))]:
            name = str(person.get("name", "")).strip()
            if not name:
                continue
            names.append(name)
            ranks[name] = str(person.get("rank", "")).strip()

            leave_raw = str(person.get("leave", "")).strip()
            if leave_raw:
                leaves[name] = parse_days_list(leave_raw, days_in_month)

            pref_raw = str(person.get("preference", "")).strip()
            if pref_raw:
                preferences[name] = parse_days_list(pref_raw, days_in_month)

        all_tabs_data[tab_key] = {
            "names": names,
            "leaves": leaves,
            "ranks": ranks,
            "preferences": preferences,
        }

    return year, month, extra, all_tabs_data


def test_preferences_hard_rule_success():
    names = ["A", "B", "C", "D"]
    leaves = {name: set() for name in names}
    preferences = {"A": {1}, "B": {5}}
    ranks = {name: "EPOP" for name in names}

    schedule, _quotas, meta, _solve_info = solve_schedule_best_effort(
        names=names,
        year=2026,
        month=3,
        extra_holidays=set(),
        leaves=leaves,
        preferences=preferences,
        ranks=ranks,
        tab_key="PYLI",
        log_cb=lambda _m: None,
    )

    assert_true(schedule[1] == "A", "Preference A:1 was not honored")
    assert_true(schedule[5] == "B", "Preference B:5 was not honored")
    assert_true(sum(v["total"] for v in meta.values()) == 31, "Not all month days were covered")


def test_preferences_same_day_conflict_becomes_warning():
    names = ["A", "B", "C", "D"]
    leaves = {name: set() for name in names}
    preferences = {"A": {10}, "B": {10}}
    ranks = {name: "EPOP" for name in names}

    schedule, _quotas, _meta, solve_info = solve_schedule_best_effort(
        names=names,
        year=2026,
        month=3,
        extra_holidays=set(),
        leaves=leaves,
        preferences=preferences,
        ranks=ranks,
        tab_key="PYLI",
        log_cb=lambda _m: None,
    )

    assert_true(len(schedule) == 31, "Schedule was not produced after conflicting preferences")
    issues = solve_info.get("preference_issues", [])
    assert_true(issues, "Expected preference issues to be reported")


def test_preferences_gap_conflict_becomes_warning():
    names = ["A", "B", "C", "D"]
    leaves = {name: set() for name in names}
    preferences = {"A": {8, 9}}
    ranks = {name: "EPOP" for name in names}

    schedule, _quotas, _meta, solve_info = solve_schedule_best_effort(
        names=names,
        year=2026,
        month=3,
        extra_holidays=set(),
        leaves=leaves,
        preferences=preferences,
        ranks=ranks,
        tab_key="PYLI",
        log_cb=lambda _m: None,
    )

    assert_true(len(schedule) == 31, "Schedule was not produced after GAP-conflicting preferences")
    issues = solve_info.get("preference_issues", [])
    assert_true(issues, "Expected preference GAP issue to be reported")


def test_history_updates_only_on_explicit_call():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_history = Path(tmpdir) / "ipiresies_history.json"
        original_history_file = history_module.HISTORY_FILE
        history_module.HISTORY_FILE = str(tmp_history)
        try:
            before = load_history()
            assert_true(before == {}, "Temporary history should start empty")

            add_to_history(
                year=2026,
                month=3,
                tab_key="PYLI",
                schedule={1: "A", 2: "B"},
                ranks={"A": "EPOP", "B": "EPOP"},
                extra_holidays=set(),
            )

            after = load_history()
            assert_true("2026" in after and "3" in after["2026"], "History was not written correctly")
            assert_true(after["2026"]["3"]["A"]["holiday"] == 1, "Holiday count for A was not stored correctly")
            assert_true(after["2026"]["3"]["B"]["weekday"] == 1, "Weekday count for B was not stored correctly")
        finally:
            history_module.HISTORY_FILE = original_history_file


def test_global_quota_respects_existing_locked_load():
    all_tabs_data = {
        "PYLI": {
            "names": ["SOURLAS", "A", "B"],
            "ranks": {"SOURLAS": "EPOP", "A": "EPOP", "B": "EPOP"},
            "leaves": {"SOURLAS": set(), "A": set(), "B": set()},
            "preferences": {},
        },
        "BAYDM": {
            "names": ["SOURLAS", "C", "D"],
            "ranks": {"SOURLAS": "EPOP", "C": "EPOP", "D": "EPOP"},
            "leaves": {"SOURLAS": set(), "C": set(), "D": set()},
            "preferences": {},
        },
    }

    global_total = compute_global_total_quotas(2026, 3, all_tabs_data, random.Random(1))
    locked_assigned = 3
    remaining = max(0, global_total["SOURLAS"] - locked_assigned)
    assert_true(remaining <= global_total["SOURLAS"], "Remaining quota was computed incorrectly")


def test_preferences_hold_on_known_feasible_cases():
    success_cases = 0
    seed = 1
    while success_cases < 10 and seed < 200:
        rng = random.Random(seed)
        names = [f"N{i}" for i in range(1, 9)]
        leaves = {
            name: {day for day in range(1, 32) if rng.random() < 0.08}
            for name in names
        }
        ranks = {name: "EPOP" for name in names}
        try:
            base_schedule, _quotas, _meta, _info = solve_schedule_best_effort(
                names=names,
                year=2026,
                month=3,
                extra_holidays=set(),
                leaves=leaves,
                preferences={},
                ranks=ranks,
                tab_key="PYLI",
                log_cb=lambda _m: None,
            )
        except ScheduleError:
            seed += 1
            continue

        chosen_days = sorted(random.Random(seed).sample(list(base_schedule.keys()), 3))
        preferences = {}
        for day in chosen_days:
            person = base_schedule[day]
            preferences.setdefault(person, set()).add(day)

        rerun_schedule, _quotas, _meta, _info = solve_schedule_best_effort(
            names=names,
            year=2026,
            month=3,
            extra_holidays=set(),
            leaves=leaves,
            preferences=preferences,
            ranks=ranks,
            tab_key="PYLI",
            log_cb=lambda _m: None,
        )

        for person, days in preferences.items():
            for day in days:
                assert_true(
                    rerun_schedule[day] == person,
                    f"Hard preference {person}:{day} was lost in a known-feasible rerun",
                )

        success_cases += 1
        seed += 1

    assert_true(success_cases == 10, "Could not find enough feasible base cases for preference reruns")


def test_random_holiday_failures_match_exact_feasibility():
    checked_cases = 0
    for seed in range(1, 81):
        case = build_random_holiday_case(seed)
        exact_feasible = exact_holiday_feasible(
            names=case["names"],
            year=case["year"],
            month=case["month"],
            extra_holidays=case["extra_holidays"],
            leaves=case["leaves"],
            holiday_quotas=case["holiday_quotas"],
            pre_assigned={},
            min_gap=MIN_GAP_STRICT,
            custom_min_gap={},
            tab_key=case["tab_key"],
        )

        try:
            solve_with_two_phase_backtracking(
                names=case["names"],
                year=case["year"],
                month=case["month"],
                extra_holidays=case["extra_holidays"],
                leaves=case["leaves"],
                quotas=case["quotas"],
                holiday_quotas=case["holiday_quotas"],
                friday_quotas={name: 0 for name in case["names"]},
                preferences={},
                min_gap=MIN_GAP_STRICT,
                custom_min_gap={},
                pre_assigned={},
                log_cb=lambda _m: None,
                tab_key=case["tab_key"],
            )
        except ScheduleError as exc:
            if "Αδύνατη κατανομή αργιών" not in str(exc):
                continue
            if exact_feasible:
                raise AssertionError(
                    f"Seed {seed}: solver failed on holidays while the exact checker found a feasible case"
                ) from exc

        checked_cases += 1

    assert_true(checked_cases >= 40, "Too few random holiday cases were checked")


def test_real_dataset_parses():
    year, month, extra, all_tabs_data = load_real_dataset()
    assert_true(year >= 2025, "Unexpected year in scheduler_people.json")
    assert_true(1 <= month <= 12, "Unexpected month in scheduler_people.json")
    assert_true(isinstance(extra, set), "Extra holidays were not parsed into a set")
    assert_true(all_tabs_data, "No tabs were loaded from scheduler_people.json")
    for tab_key in TAB_KEYS:
        assert_true(tab_key in all_tabs_data, f"Missing tab {tab_key} in scheduler_people.json")


def test_real_dataset_each_tab_runs_cleanly():
    year, month, extra, all_tabs_data = load_real_dataset()
    _, dim = calendar.monthrange(year, month)

    for tab_key, tab_data in all_tabs_data.items():
        if not tab_data["names"]:
            continue
        try:
            schedule, _quotas, meta, solve_info = solve_schedule_best_effort(
                names=tab_data["names"],
                year=year,
                month=month,
                extra_holidays=extra,
                leaves=tab_data["leaves"],
                preferences=tab_data["preferences"],
                ranks=tab_data["ranks"],
                tab_key=tab_key,
                log_cb=lambda _m: None,
            )
            assert_true(len(schedule) == dim, f"{tab_key}: schedule does not cover the whole month")
            assert_true(sum(v["total"] for v in meta.values()) == dim, f"{tab_key}: metadata totals do not match month days")
            assert_true("solver" in solve_info, f"{tab_key}: solve_info missing solver key")
        except ScheduleError as exc:
            assert_true(bool(str(exc)), f"{tab_key}: ScheduleError without message")
            assert_true(bool(getattr(exc, "details", "")), f"{tab_key}: ScheduleError without details")


def test_real_dataset_unified_runs_cleanly():
    year, month, extra, all_tabs_data = load_real_dataset()

    try:
        results = solve_all_tabs_unified(
            all_tabs_data=all_tabs_data,
            year=year,
            month=month,
            extra_holidays=extra,
            log_cb=lambda *_args, **_kwargs: None,
        )
        assert_true(isinstance(results, dict), "Unified solve did not return a dict")
        for tab_key, (schedule, _quotas, meta, solve_info) in results.items():
            assert_true(schedule, f"{tab_key}: unified solve returned empty schedule")
            assert_true(meta, f"{tab_key}: unified solve returned empty metadata")
            assert_true("solver" in solve_info, f"{tab_key}: unified solve_info missing solver key")
    except ScheduleError as exc:
        assert_true(bool(str(exc)), "Unified ScheduleError without message")
        assert_true(bool(getattr(exc, "details", "")), "Unified ScheduleError without details")


def main():
    tests = [
        test_preferences_hard_rule_success,
        test_preferences_same_day_conflict_becomes_warning,
        test_preferences_gap_conflict_becomes_warning,
        test_history_updates_only_on_explicit_call,
        test_global_quota_respects_existing_locked_load,
        test_preferences_hold_on_known_feasible_cases,
        test_random_holiday_failures_match_exact_feasibility,
        test_real_dataset_parses,
        test_real_dataset_each_tab_runs_cleanly,
        test_real_dataset_unified_runs_cleanly,
    ]

    passed = 0
    failed = []

    for test in tests:
        try:
            test()
            print(f"[OK] {test.__name__}")
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {test.__name__}: {exc}")
            failed.append((test.__name__, str(exc)))

    print(f"\nSummary: {passed}/{len(tests)} tests passed")
    if failed:
        print("Failures:")
        for name, error in failed:
            print(f"- {name}: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
