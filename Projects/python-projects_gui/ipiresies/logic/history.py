# history.py
# Διαχείριση ιστορικού υπηρεσιών (load, save, add, cumulative stats)

import calendar
import datetime as dt
import json
import os
import random

from logic.constants import F_SCORE, H_SCORE, W_SCORE
from logic.date_helpers import day_bucket
from logic.persistence import get_json_dir


HISTORY_FILE = os.path.join(get_json_dir(), "ipiresies_history.json")


def get_person_group(rank: str) -> str:
    """
    Group A (OFFICERS): βαθμοί που τελειώνουν σε "ΛΓΟΣ"
    (π.χ. ΛΓΟΣ, ΥΠΛΓΟΣ, ΑΝΘΛΓΟΣ).
    Group B (OTHERS): όλοι οι υπόλοιποι βαθμοί.
    """
    rank_upper = rank.upper().strip()
    return "OFFICERS" if rank_upper.endswith("ΛΓΟΣ") else "OTHERS"


def load_history() -> dict:
    """Load history from JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load history: {e}")
        return {}


def save_history(history: dict):
    """Save history to JSON file."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")


def add_to_history(
    year: int,
    month: int,
    tab_key: str,
    schedule: dict[int, str],
    ranks: dict[str, str],
    extra_holidays: set[int],
):
    """
    Προσθέτει οριστικό πρόγραμμα στο ιστορικό.
    Δομή: { year: { month: { person: {rank, weekday, friday, holiday} } } }
    Αν το tab έχει ήδη αποθηκευτεί για τον μήνα, τα δεδομένα αντικαθίστανται.
    """
    history = load_history()

    year_str = str(year)
    month_str = str(month)

    if year_str not in history:
        history[year_str] = {}
    if month_str not in history[year_str]:
        history[year_str][month_str] = {}

    saved_tabs = history[year_str][month_str].get("_saved_tabs", [])
    if tab_key in saved_tabs:
        people_in_schedule = set(schedule.values())
        for person in people_in_schedule:
            if person in history[year_str][month_str]:
                del history[year_str][month_str][person]

    for day, person in schedule.items():
        if person not in history[year_str][month_str]:
            history[year_str][month_str][person] = {
                "rank": ranks.get(person, ""),
                "weekday": 0,
                "friday": 0,
                "holiday": 0,
            }

        date_obj = dt.date(year, month, day)
        weekday_num = date_obj.weekday()
        bucket = day_bucket(year, month, day, extra_holidays)

        if bucket == "HOLIDAY":
            history[year_str][month_str][person]["holiday"] += 1
        elif weekday_num == 4:
            history[year_str][month_str][person]["friday"] += 1
        else:
            history[year_str][month_str][person]["weekday"] += 1

    if "_saved_tabs" not in history[year_str][month_str]:
        history[year_str][month_str]["_saved_tabs"] = []
    if tab_key not in history[year_str][month_str]["_saved_tabs"]:
        history[year_str][month_str]["_saved_tabs"].append(tab_key)

    save_history(history)


def calculate_cumulative_stats(
    year: int,
    month: int,
    tab_key: str,  # kept for compatibility, not used
    names: list[str],
) -> dict[str, dict]:
    """
    Αθροιστικά στατιστικά από αρχή έτους έως τον προηγούμενο μήνα.
    Returns: { name: {months, total_weekdays, total_fridays, total_holidays, cumulative_score} }
    """
    history = load_history()
    year_str = str(year)

    cumulative = {
        name: {
            "months": 0,
            "total_weekdays": 0,
            "total_fridays": 0,
            "total_holidays": 0,
            "cumulative_score": 0.0,
        }
        for name in names
    }

    if year_str not in history:
        return cumulative

    for past_month in range(1, month):
        month_str = str(past_month)
        if month_str not in history[year_str]:
            continue
        month_data = history[year_str][month_str]
        for name in names:
            if name in month_data:
                data = month_data[name]
                cumulative[name]["months"] += 1
                cumulative[name]["total_weekdays"] += data.get("weekday", 0)
                cumulative[name]["total_fridays"] += data.get("friday", 0)
                cumulative[name]["total_holidays"] += data.get("holiday", 0)
                cumulative[name]["cumulative_score"] += (
                    data.get("weekday", 0) * W_SCORE
                    + data.get("friday", 0) * F_SCORE
                    + data.get("holiday", 0) * H_SCORE
                )

    return cumulative


def merge_global_people(all_tabs_data: dict) -> dict[str, dict]:
    """Φτιάχνει global registry ανά άτομο από όλα τα tabs."""
    people = {}
    for tab_key, tab_data in all_tabs_data.items():
        names = tab_data.get("names", [])
        ranks = tab_data.get("ranks", {})
        leaves = tab_data.get("leaves", {})
        preferences = tab_data.get("preferences", {})
        for name in names:
            if name not in people:
                people[name] = {
                    "name": name,
                    "rank": ranks.get(name, ""),
                    "group": get_person_group(ranks.get(name, "")),
                    "tabs": [],
                    "leaves_by_tab": {},
                    "preferences_by_tab": {},
                }
            people[name]["tabs"].append(tab_key)
            people[name]["leaves_by_tab"][tab_key] = set(leaves.get(name, set()))
            people[name]["preferences_by_tab"][tab_key] = set(preferences.get(name, set()))
            if not people[name]["rank"] and ranks.get(name, ""):
                people[name]["rank"] = ranks.get(name, "")
                people[name]["group"] = get_person_group(ranks.get(name, ""))
    return people


def build_global_cumulative_stats(
    year: int,
    month: int,
    global_people: dict[str, dict],
) -> dict[str, dict]:
    """Για κάθε άτομο μαζεύει cumulative stats από όλα τα tabs στα οποία ανήκει."""
    out = {}
    for name, pdata in global_people.items():
        total_weekdays = total_fridays = total_holidays = 0
        for tab_key in pdata["tabs"]:
            hist = calculate_cumulative_stats(year, month, tab_key, [name]).get(name, {})
            total_weekdays += hist.get("total_weekdays", 0)
            total_fridays += hist.get("total_fridays", 0)
            total_holidays += hist.get("total_holidays", 0)
        out[name] = {
            "total_weekdays": total_weekdays,
            "total_fridays": total_fridays,
            "total_holidays": total_holidays,
        }
    return out


def add_current_month_stats(
    cumulative: dict[str, dict],
    schedules: dict[str, dict[int, str]],
    year: int,
    month: int,
    extra_holidays: set[int],
) -> dict[str, dict]:
    """Προσθέτει αναθέσεις τρέχοντος μήνα από πολλά tabs στα αθροιστικά stats."""
    result = {name: stats.copy() for name, stats in cumulative.items()}

    for _tab_key, schedule in schedules.items():
        for day, person in schedule.items():
            if person not in result:
                result[person] = {
                    "months": 0,
                    "total_weekdays": 0,
                    "total_fridays": 0,
                    "total_holidays": 0,
                    "cumulative_score": 0.0,
                }
            date_obj = dt.date(year, month, day)
            weekday_num = date_obj.weekday()
            bucket = day_bucket(year, month, day, extra_holidays)
            if bucket == "HOLIDAY":
                result[person]["total_holidays"] += 1
            elif weekday_num == 4:
                result[person]["total_fridays"] += 1
            else:
                result[person]["total_weekdays"] += 1

    return result
