# scheduler.py
# Κύρια ενορχήστρωση solver: solve_schedule_best_effort, solve_all_tabs_unified
# Περιλαμβάνει fallbacks και progressive constraint relaxation

import calendar
import datetime as dt
import random
import re
import time

from logic.constants import MIN_GAP_STRICT, TAB_KEYS, TAB_TITLES
from logic.date_helpers import ScheduleError, day_bucket
from logic.history import calculate_cumulative_stats
from logic.quotas import (
    compute_total_quotas,
    compute_total_quotas_with_history,
    compute_holiday_quotas_with_history,
    compute_friday_quotas_with_history,
    normalize_quotas_with_max,
    repair_total_quotas_for_availability,
    compute_auto_max_from_leaves,
)
from logic.cross_tab import cross_tab_blocked_days, compute_cross_tab_counts
from logic.solver import solve_with_two_phase_backtracking, compute_schedule_metadata

_solve_counter = 0

def solve_schedule_best_effort(
    names: list[str],
    year: int,
    month: int,
    extra_holidays: set[int],
    leaves: dict[str, set[int]],
    preferences: dict[str, set[int]] = None,
    ranks: dict[str, str] | None = None,
    tab_key: str = "AYDM",
    log_cb=None,
    cross_tab_holidays: dict[str, int] | None = None,
    cross_tab_fridays: dict[str, int] | None = None,
    preset_quotas: dict[str, int] | None = None,
    preset_holiday_quotas: dict[str, int] | None = None,
    preset_friday_quotas: dict[str, int] | None = None,
) -> tuple[dict[int, str], dict[str, int], dict, dict]:
    """
    Κύριος solver ενός tab με hardest-days-first strategy + score balancing.
    MAX caps υπολογίζονται αυτόματα από άδειες.
    Περιλαμβάνει πολλαπλές προσπάθειες και progressive fallbacks.
    """
    global _solve_counter
    _solve_counter += 1

    if log_cb is None:
        log_cb = lambda m: print(m)
    if cross_tab_holidays is None:
        cross_tab_holidays = {}
    if cross_tab_fridays is None:
        cross_tab_fridays = {}
    if preferences is None:
        preferences = {}
    if not names:
        raise ScheduleError("Δεν υπάρχουν άτομα!", details="Πρόσθεσε τουλάχιστον ένα άτομο.")
    if ranks is None:
        ranks = {}

    _, days_in_month = calendar.monthrange(year, month)

    total_holidays = sum(
        1 for d in range(1, days_in_month + 1)
        if day_bucket(year, month, d, extra_holidays) == "HOLIDAY"
    )
    total_fridays = sum(
        1 for d in range(1, days_in_month + 1)
        if dt.date(year, month, d).weekday() == 4
    )

    log_cb("🔍 Έλεγχος διαθεσιμότητας...")
    auto_max, custom_min_gap = compute_auto_max_from_leaves(
        names, days_in_month, leaves, MIN_GAP_STRICT, log_cb
    )
    combined_max_caps = auto_max.copy()

    def _make_rng(label: str, attempt: int = 0) -> random.Random:
        seed_payload = (
            time.time_ns(),
            _solve_counter,
            label,
            attempt,
            tab_key,
            year,
            month,
            tuple(sorted(extra_holidays)),
        )
        return random.Random(hash(seed_payload))

    # ── Builders ─────────────────────────────────────────────────
    def build_quotas(rng: random.Random) -> dict[str, int]:
        if preset_quotas is not None:
            return dict(preset_quotas)
        cumulative_stats = calculate_cumulative_stats(year, month, tab_key, names)
        if ranks and cumulative_stats:
            q_init = compute_total_quotas_with_history(names, ranks, days_in_month, cumulative_stats, rng)
        else:
            q_init = compute_total_quotas(names, days_in_month, rng)
        q_norm = normalize_quotas_with_max(names, q_init, days_in_month, combined_max_caps)
        return repair_total_quotas_for_availability(
            names=names,
            quotas_total=q_norm,
            days_in_month=days_in_month,
            leaves=leaves,
            max_caps=combined_max_caps,
            log_cb=log_cb,
        )

    def build_holiday_quotas(rng, quotas, forced_holiday_counts, forced_pre=None):
        return {p: int(quotas.get(p, 0)) for p in names}

    def build_friday_quotas(rng, quotas, forced_friday_counts):
        return {p: 0 for p in names}

    def build_forced_preassigned(rng: random.Random) -> tuple[dict[int, str], list[str]]:
        """Κλειδώνει τις έγκυρες επιθυμίες και κρατά προειδοποιήσεις για όσες αγνοήθηκαν."""

        person_pref_days: dict[str, list[int]] = {}
        forced: dict[int, str] = {}
        assigned_by_person: dict[str, list[int]] = {}
        issues: list[str] = []

        def can_force(person: str, day: int) -> tuple[bool, str | None]:
            person_gap = custom_min_gap.get(person, MIN_GAP_STRICT)
            for other_day in assigned_by_person.get(person, []):
                if abs(other_day - day) <= person_gap:
                    return False, f"η μέρα {day} συγκρούεται με την ήδη ζητημένη μέρα {other_day} λόγω GAP"
            return True, None

        for p, days in (preferences or {}).items():
            if p not in names or not days:
                continue
            valid_days = sorted({int(x) for x in days})
            accepted_days: list[int] = []
            for d in valid_days:
                if not (1 <= d <= days_in_month):
                    issues.append(f"Η επιθυμία του {p} για τη μέρα {d} αγνοήθηκε, γιατί είναι εκτός του τρέχοντος μήνα.")
                    continue
                if d in leaves.get(p, set()):
                    issues.append(f"Η επιθυμία του {p} για τη μέρα {d} αγνοήθηκε, γιατί συγκρούεται με άδεια.")
                    continue
                if d in forced and forced[d] != p:
                    issues.append(
                        f"Η επιθυμία του {p} για τη μέρα {d} αγνοήθηκε, γιατί τη μέρα {d} την έχει ήδη ζητήσει ο {forced[d]}."
                    )
                    continue
                accepted_days.append(d)

            person_pref_days[p] = accepted_days

        for person, days in sorted(person_pref_days.items(), key=lambda item: (len(item[1]), item[0])):
            assigned_by_person.setdefault(person, [])
            for day in days:
                if day in forced and forced[day] != person:
                    issues.append(
                        f"Η επιθυμία του {person} για τη μέρα {day} αγνοήθηκε, γιατί τη μέρα {day} την έχει ήδη ζητήσει ο {forced[day]}."
                    )
                    continue
                ok, reason = can_force(person, day)
                if not ok:
                    issues.append(f"Η επιθυμία του {person} για τη μέρα {day} αγνοήθηκε, γιατί {reason}.")
                    continue
                forced[day] = person
                assigned_by_person[person].append(day)

        if forced:
            forced_str = ", ".join(f"{d}:{p}" for d, p in sorted(forced.items()))
            log_cb(f"📌 Επιθυμίες που κλειδώθηκαν: {forced_str}")
        if issues:
            for issue in issues:
                log_cb(f"  ⚠️ {issue}")

        return forced, issues

    # ── Main attempt loop ─────────────────────────────────────────
    best_spread     = float("inf")
    best_schedule   = None
    best_quotas     = None
    best_meta       = None
    best_solve_info = {}
    last_error      = None

    forced_pre:             dict[int, str]   = {}
    forced_holiday_counts:  dict[str, int]   = {p: 0 for p in names}
    forced_friday_counts:   dict[str, int]   = {p: 0 for p in names}
    preference_issues:      list[str]        = []

    TRIES_A = 40

    def run_attempt(attempt_num, rng, override_max_time=None, override_max_recursion_mult=None):
        nonlocal last_error, forced_pre, forced_holiday_counts, forced_friday_counts, preference_issues

        _forced_pre, _preference_issues = build_forced_preassigned(rng)
        _forced_counts: dict[str, int] = {p: 0 for p in names}
        _forced_hol:    dict[str, int] = {p: 0 for p in names}
        _forced_fri:    dict[str, int] = {p: 0 for p in names}
        for d, p in _forced_pre.items():
            _forced_counts[p] = _forced_counts.get(p, 0) + 1
            if day_bucket(year, month, d, extra_holidays) == "HOLIDAY":
                _forced_hol[p] = _forced_hol.get(p, 0) + 1
            if dt.date(year, month, d).weekday() == 4:
                _forced_fri[p] = _forced_fri.get(p, 0) + 1

        _qtotal = build_quotas(rng)
        _quotas: dict[str, int] = {}
        for p in names:
            q = int(_qtotal.get(p, 0)) - int(_forced_counts.get(p, 0))
            _quotas[p] = max(0, q)

        _remaining = days_in_month - len(_forced_pre)
        _diff      = _remaining - sum(_quotas.values())
        if _diff != 0:
            _adj = names[:]
            if _diff > 0:
                for _ in range(_diff):
                    rng.shuffle(_adj)
                    _added = False
                    for p in _adj:
                        _cap     = combined_max_caps.get(p)
                        _planned = int(_forced_counts.get(p, 0)) + int(_quotas.get(p, 0))
                        if _cap is None or _planned < int(_cap):
                            _quotas[p] += 1
                            _added = True
                            break
                    if not _added:
                        _quotas[rng.choice(_adj)] += 1
            else:
                _pool = [p for p in _adj if _quotas.get(p, 0) > 0]
                for _ in range(-_diff):
                    if not _pool:
                        break
                    p = rng.choice(_pool)
                    _quotas[p] -= 1
                    if _quotas[p] <= 0:
                        _pool = [x for x in _pool if x != p]

        _hol_q = build_holiday_quotas(rng, _quotas, _forced_hol, _forced_pre)
        _fri_q = build_friday_quotas(rng, _quotas, _forced_fri)

        if attempt_num == 0:
            log_cb(f"📊 Συνολικά quota: {_quotas}")

        try:
            if attempt_num == 0:
                log_cb("📌 Προσπάθεια: Ενιαίος solver για όλες τις μέρες...")
            _sched, _si, _meth = solve_with_two_phase_backtracking(
                names=names, year=year, month=month,
                extra_holidays=extra_holidays, leaves=leaves,
                quotas=_quotas, holiday_quotas=_hol_q, friday_quotas=_fri_q,
                preferences=preferences, min_gap=MIN_GAP_STRICT,
                custom_min_gap=custom_min_gap, pre_assigned=_forced_pre,
                log_cb=log_cb if attempt_num == 0 else (lambda m: None),
                tab_key=tab_key,
                max_time=override_max_time,
                max_recursion_mult=override_max_recursion_mult,
            )
            _meta    = compute_schedule_metadata(_sched, year, month, extra_holidays)
            _scores  = [m["score"] for m in _meta.values()]
            _spread  = max(_scores) - min(_scores) if _scores else 0.0
            forced_pre            = _forced_pre
            forced_holiday_counts = _forced_hol
            forced_friday_counts  = _forced_fri
            preference_issues     = list(_preference_issues)
            _si["preference_issues"] = list(_preference_issues)
            return _spread, _sched, _quotas, _meta, _si, _forced_pre
        except ScheduleError as e:
            last_error = e
            return None

    log_cb(f"🔍 Αναζήτηση spread <= 1.0 ({TRIES_A} προσπάθειες)...")
    for _att in range(TRIES_A):
        _rng = _make_rng("strict", _att)
        _res  = run_attempt(_att, _rng)
        if _res is None:
            continue
        _sp, _sc, _qu, _me, _si, _fp = _res
        log_cb(f"  🎯 Προσπάθεια #{_att+1}: spread = {_sp:.2f}")
        if _sp < best_spread:
            best_spread, best_schedule, best_quotas, best_meta, best_solve_info = _sp, _sc, _qu, _me, _si
        if best_spread <= 1.0:
            log_cb("  ✅ Βρέθηκε spread <= 1.0")
            break

    if best_schedule is not None:
        if best_spread <= 1.0:
            log_cb(f"✅ Τελικό score spread: {best_spread:.2f} (<= 1.0)")
        else:
            log_cb(f"⚠️ Τελικό score spread: {best_spread:.2f} (> 1.0, αλλά καλύτερο δυνατό)")
        return best_schedule, best_quotas, best_meta, best_solve_info

    # ── Fallback 1: GAP=1 για πολύ περιορισμένους ────────────────
    log_cb("📌 Fallback 1: GAP=1 για πολύ περιορισμένους...")
    highly_constrained = {
        name: 1
        for name in names
        if len([d for d in range(1, days_in_month + 1) if d not in leaves.get(name, set())]) < days_in_month / 3
    }
    if highly_constrained:
        rng = _make_rng("fallback1")
        qfb = build_quotas(rng)
        hqfb = build_holiday_quotas(rng, qfb, forced_holiday_counts, forced_pre)
        fqfb = build_friday_quotas(rng, qfb, forced_friday_counts)
        try:
            schedule, solve_info, _ = solve_with_two_phase_backtracking(
                names=names, year=year, month=month,
                extra_holidays=extra_holidays, leaves=leaves,
                quotas=qfb, holiday_quotas=hqfb, friday_quotas=fqfb,
                preferences=preferences, min_gap=2,
                custom_min_gap=highly_constrained, pre_assigned=forced_pre,
                log_cb=lambda m: None, tab_key=tab_key,
            )
            meta = compute_schedule_metadata(schedule, year, month, extra_holidays)
            solve_info["preference_issues"] = list(preference_issues)
            log_cb(f"✅ Βρέθηκε λύση με GAP=1 για {len(highly_constrained)} άτομα")
            return schedule, qfb, meta, solve_info
        except ScheduleError as e:
            last_error = e

    # ── Fallback 2: GAP=1 για μέτρια περιορισμένους ──────────────
    log_cb("📌 Fallback 2: GAP=1 για μέτρια περιορισμένους...")
    moderately_constrained = {
        name: 1
        for name in names
        if len([d for d in range(1, days_in_month + 1) if d not in leaves.get(name, set())]) < days_in_month / 2
    }
    if moderately_constrained:
        rng = _make_rng("fallback2")
        qfb = build_quotas(rng)
        hqfb = build_holiday_quotas(rng, qfb, forced_holiday_counts, forced_pre)
        fqfb = build_friday_quotas(rng, qfb, forced_friday_counts)
        try:
            schedule, solve_info, _ = solve_with_two_phase_backtracking(
                names=names, year=year, month=month,
                extra_holidays=extra_holidays, leaves=leaves,
                quotas=qfb, holiday_quotas=hqfb, friday_quotas=fqfb,
                preferences=preferences, min_gap=2,
                custom_min_gap=moderately_constrained, pre_assigned=forced_pre,
                log_cb=lambda m: None, tab_key=tab_key,
            )
            meta = compute_schedule_metadata(schedule, year, month, extra_holidays)
            solve_info["preference_issues"] = list(preference_issues)
            log_cb(f"✅ Βρέθηκε λύση με GAP=1 για {len(moderately_constrained)} άτομα")
            return schedule, qfb, meta, solve_info
        except ScheduleError as e:
            last_error = e

    # ── Fallback 3: GAP=1 για όλους ──────────────────────────────
    log_cb("📌 Fallback 3: GAP=1 για όλους...")
    rng = _make_rng("fallback3")
    qfb  = build_quotas(rng)
    hqfb = build_holiday_quotas(rng, qfb, forced_holiday_counts, forced_pre)
    fqfb = build_friday_quotas(rng, qfb, forced_friday_counts)
    try:
        schedule, solve_info, _ = solve_with_two_phase_backtracking(
            names=names, year=year, month=month,
            extra_holidays=extra_holidays, leaves=leaves,
            quotas=qfb, holiday_quotas=hqfb, friday_quotas=fqfb,
            preferences=preferences, min_gap=1,
            custom_min_gap=None, pre_assigned=forced_pre,
            log_cb=lambda m: None, tab_key=tab_key,
        )
        meta = compute_schedule_metadata(schedule, year, month, extra_holidays)
        solve_info["preference_issues"] = list(preference_issues)
        log_cb("✅ Βρέθηκε λύση με GAP=1 για όλους")
        return schedule, qfb, meta, solve_info
    except ScheduleError as e:
        last_error = e

    # ── Φάση 4: Αφαίρεση κανόνα Παρ/Σαβ ──────────────────────────
    log_cb("📌 Φάση 4: Αφαίρεση κανόνα Παρ/Σαβ...")
    all_days_relaxed = set(range(1, days_in_month + 1))
    rng = _make_rng("fallback4")
    qfb  = build_quotas(rng)
    hqfb = build_holiday_quotas(rng, qfb, forced_holiday_counts, forced_pre)
    fqfb = build_friday_quotas(rng, qfb, forced_friday_counts)
    try:
        schedule, solve_info, _ = solve_with_two_phase_backtracking(
            names=names, year=year, month=month,
            extra_holidays=extra_holidays, leaves=leaves,
            quotas=qfb, holiday_quotas=hqfb, friday_quotas=fqfb,
            preferences=preferences, min_gap=1,
            custom_min_gap=None, pre_assigned=forced_pre,
            ignore_weekend_pair_days=all_days_relaxed,
            log_cb=lambda m: None, tab_key=tab_key,
        )
        meta = compute_schedule_metadata(schedule, year, month, extra_holidays)
        solve_info["preference_issues"] = list(preference_issues)
        solve_info["relaxed_weekend_pair_all_days"] = True
        solve_info["relaxed_weekend_pair_days"] = []
        log_cb("✅ Βρέθηκε λύση χωρίς κανόνα Παρ/Σαβ")
        return schedule, qfb, meta, solve_info
    except ScheduleError as e:
        last_error = e

    # ── Τελική ενισχυμένη αναζήτηση: GAP=1 και χωρίς Παρ/Σαβ ──
    log_cb("🔧 Τελική ενισχυμένη αναζήτηση με GAP=1 και χωρίς Παρ/Σαβ...")

    def try_final_search(attempts=40, max_time=60.0, max_recursion_mult=8):
        _best_sp = float("inf")
        _best_res = None
        for _xi in range(attempts):
            _xrng = _make_rng("final", _xi)
            _xq = build_quotas(_xrng)
            _xdummy_hq = {p: int(_xq.get(p, 0)) for p in names}
            _xdummy_fq = {p: 0 for p in names}
            try:
                _sc, _si, _ = solve_with_two_phase_backtracking(
                    names=names, year=year, month=month, extra_holidays=extra_holidays,
                    leaves=leaves, quotas=_xq, holiday_quotas=_xdummy_hq, friday_quotas=_xdummy_fq,
                    preferences=preferences, min_gap=1,
                    custom_min_gap=None, pre_assigned=forced_pre,
                    ignore_weekend_pair_days=all_days_relaxed,
                    log_cb=lambda m: None, tab_key=tab_key,
                    max_time=max_time, max_recursion_mult=max_recursion_mult,
                )
                _meta = compute_schedule_metadata(_sc, year, month, extra_holidays)
                _scores = [m["score"] for m in _meta.values()]
                _sp = max(_scores) - min(_scores) if _scores else 0.0
                if _sp < _best_sp:
                    _best_sp = _sp
                    _best_res = (_sc, _xq, _meta, _si)
                if _best_sp <= 1.0:
                    break
            except ScheduleError:
                continue
        return _best_res, _best_sp

    _final_res, _final_sp = try_final_search()
    if _final_res is not None:
        _fsc, _fqu, _fme, _fsi = _final_res
        _fsi["preference_issues"] = list(preference_issues)
        _fsi["final_gap_only_search"] = True
        _fsi["relaxed_weekend_pair_all_days"] = True
        _fsi["relaxed_weekend_pair_days"] = []
        log_cb(f"✅ Βρέθηκε λύση με τελική ενισχυμένη αναζήτηση (spread={_final_sp:.2f})")
        return _fsc, _fqu, _fme, _fsi

    if last_error is not None:
        raise last_error
    raise ScheduleError(
        "Αδύνατο πρόγραμμα",
        details="Δεν βρέθηκε λύση. Έλεγξε άδειες και constraints."
    )


# ──────────────────────────────────────────────────────────────────
# UNIFIED Multi-Tab Scheduling
# ──────────────────────────────────────────────────────────────────

def solve_all_tabs_unified(
    all_tabs_data: dict[str, dict],
    year: int,
    month: int,
    extra_holidays: set[int],
    log_cb=None,
) -> dict[str, tuple]:
    """
    Επιλύει όλα τα tabs ΔΙΑΔΟΧΙΚΑ ώστε το ίδιο άτομο να μην πέφτει
    την ίδια μέρα σε διαφορετικά tabs.

    Επιστρέφει: { tab_key: (schedule, quotas, meta, solve_info) }
    """
    if log_cb is None:
        log_cb = lambda *args, **kwargs: None

    def _emit(tab_key, message: str):
        try:
            log_cb(tab_key, message)
        except TypeError:
            log_cb(message)

    _emit(None, "=" * 60)
    _emit(None, "🌐 Ενιαίο scheduling - διαδοχική επεξεργασία")
    _emit(None, "=" * 60)

    results            = {}
    global_assignments = {}   # {person: {source_tab: set_of_days}}

    for tab_key in TAB_KEYS:
        if tab_key not in all_tabs_data:
            continue

        tab_data    = all_tabs_data[tab_key]
        names       = tab_data["names"]
        leaves      = tab_data["leaves"]
        ranks       = tab_data["ranks"]
        preferences = tab_data.get("preferences", {})

        if not names:
            continue

        _emit(tab_key, f"\n{TAB_TITLES[tab_key]}...")

        # Cross-tab blocking
        extended_leaves = {}
        for person in names:
            person_leaves = set(leaves.get(person, set()))
            if person in global_assignments:
                for src_tab, src_days in global_assignments[person].items():
                    blocked = cross_tab_blocked_days(src_days, src_tab, year, month)
                    person_leaves.update(blocked)
                _emit(tab_key, f"  Προειδοποίηση: {person}: cross-tab blocked {sorted(person_leaves - leaves.get(person, set()))}")
            extended_leaves[person] = person_leaves

        # Cross-tab αργίες / Παρ για quota balancing
        _other_scheds: dict[str, dict[str, str]] = {}
        for person, tab_days in global_assignments.items():
            for src_tab, days in tab_days.items():
                if src_tab not in _other_scheds:
                    _other_scheds[src_tab] = {}
                for d in days:
                    _other_scheds[src_tab][str(d)] = person

        cross_hol, cross_fri = compute_cross_tab_counts(
            names, _other_scheds, year, month, extra_holidays
        )
        if any(v > 0 for v in cross_hol.values()):
            _emit(tab_key, f"  Cross-tab αργίες: { {p: v for p, v in cross_hol.items() if v > 0} }")

        try:
            schedule, quotas, meta, solve_info = solve_schedule_best_effort(
                names=names, year=year, month=month,
                extra_holidays=extra_holidays,
                leaves=extended_leaves,
                preferences=preferences,
                ranks=ranks,
                tab_key=tab_key,
                log_cb=lambda m, tk=tab_key: _emit(tk, f"    {m}"),
                cross_tab_holidays=cross_hol,
                cross_tab_fridays=cross_fri,
            )

            for day, person in schedule.items():
                if person not in global_assignments:
                    global_assignments[person] = {}
                if tab_key not in global_assignments[person]:
                    global_assignments[person][tab_key] = set()
                global_assignments[person][tab_key].add(day)

            results[tab_key] = (schedule, quotas, meta, solve_info)
            _emit(tab_key, f"  Το {TAB_TITLES[tab_key]} ολοκληρώθηκε")

        except ScheduleError as e:
            _emit(tab_key, f"  Αποτυχία στο {TAB_TITLES[tab_key]}: {e}")
            raise ScheduleError(
                f"Αποτυχία στο {TAB_TITLES[tab_key]}",
                details=e.details
            )

    _emit(None, "\n" + "=" * 60)
    _emit(None, "Όλα τα προγράμματα ολοκληρώθηκαν")
    _emit(None, "=" * 60)
    return results
