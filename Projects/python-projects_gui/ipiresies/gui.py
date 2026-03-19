# ipiresies_gui.py
# GUI για τον Scheduler - tkinter interface
# Εξαρτάται από scheduler_core.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from logic.constants    import *
from logic.persistence  import *
from logic.date_helpers import *
from logic.history      import *
from logic.cross_tab    import *
from logic.quotas       import *
from logic.solver       import *
from logic.scheduler    import *
from word_export import export_all_schedules_to_word

# -----------------------------
# GUI: PeopleTab
# -----------------------------
class PeopleTab(ttk.Frame):
    def __init__(self, parent, tab_key: str, app_ref):
        super().__init__(parent)
        self.tab_key = tab_key
        self.app_ref = app_ref
        
        self.current_schedule: dict[int, str] = {}
        self.current_ranks: dict[str, str] = {}
        self.saved_schedule_locked = False
        
        # Quotas από Preview — χρησιμοποιούνται αυτούσια στο Generate
        self.preset_quotas = None
        self.preset_holiday_quotas = None
        self.preset_friday_quotas = None
        
        self._build_ui()
    
    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="both", expand=True, padx=10, pady=10)
        
        left = ttk.LabelFrame(top, text="Προσωπικό", padding=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        count_frame = ttk.Frame(left)
        count_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(count_frame, text="Πλήθος ατόμων:").pack(side="left")
        
        self.count_var = tk.StringVar(value="1")
        self.active_count = tk.IntVar(value=1)
        
        count_entry = ttk.Entry(count_frame, textvariable=self.count_var, width=6)
        count_entry.pack(side="left", padx=6)
        
        ttk.Button(count_frame, text="Εφαρμογή", command=self.apply_count).pack(side="left")
        ttk.Button(count_frame, text="💾 Αποθήκευση State", command=lambda: self.app_ref.on_manual_save_state()).pack(side="left", padx=(12, 0))
        
        canvas_frame = ttk.Frame(left)
        canvas_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(canvas_frame, height=300)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.scrollable = ttk.Frame(canvas)
        
        self.scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        hdr = ttk.Frame(self.scrollable)
        hdr.pack(fill="x", pady=(0, 5))
        ttk.Label(hdr, text="Βαθμός", width=12).grid(row=0, column=0, padx=2)
        ttk.Label(hdr, text="Ονοματεπώνυμο", width=20).grid(row=0, column=1, padx=2)
        ttk.Label(hdr, text="Άδειες (π.χ. 6,25)", width=18).grid(row=0, column=2, padx=2)
        
        # Button to clear all leaves
        clear_leaves_btn = ttk.Button(hdr, text="🗑️", width=3, 
                                     command=self.clear_all_leaves)
        clear_leaves_btn.grid(row=1, column=2, padx=2)
        
        ttk.Label(hdr, text="Επιθυμία (π.χ. 5,12)", width=18).grid(row=0, column=4, padx=2)
        
        # Button to clear all preferences
        clear_pref_btn = ttk.Button(hdr, text="🗑️", width=3,
                                    command=self.clear_all_preferences)
        clear_pref_btn.grid(row=1, column=4, padx=2)
        
        self.people_rows: list[dict] = []
        self._add_row("", "", "", "")
        
        # Right panel: Program / Stats
        right = ttk.LabelFrame(top, text="Πρόγραμμα / Στατιστικά", padding=10)
        right.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # Toolbar (buttons live inside the Program/Stats panel)
        toolbar = ttk.Frame(right)
        toolbar.pack(fill="x", pady=(0, 8))

        self.generate_btn = ttk.Button(
            toolbar,
            text="▶ Δημιουργία",
            command=lambda: self.app_ref.on_generate_current(),
            state="disabled",
        )
        self.generate_btn.pack(side="left", padx=(0, 6))

        self.export_btn = ttk.Button(
            toolbar,
            text="💾 Αποθήκευση",
            command=lambda: self.app_ref.on_save_current_schedule(),
            state="disabled",
        )
        self.export_btn.pack(side="left")
        
        self.stats = tk.Text(right, height=35, width=60, wrap="word", state="disabled")
        self.stats.tag_configure("warning", foreground="darkorange", font=("Consolas", 9, "bold"))
        self.stats.pack(fill="both", expand=True)
        
        self.stats.tag_config("warn_total", background="yellow")
        self.stats.tag_config("info", foreground="blue")
        self.stats.tag_config("error", foreground="red")
    
    def clear_all_leaves(self):
        """Clear all leave entries."""
        for row in self.people_rows:
            row["leave_var"].set("")

    def _lock_generate(self):
        """Κλείδωμα Δημιουργία — χρειάζεται νέο Quota πρώτα."""
        if hasattr(self, "generate_btn"):
            self.generate_btn.config(state="disabled")
        self.preset_quotas = None
        self.preset_holiday_quotas = None
        self.preset_friday_quotas = None
        self.saved_schedule_locked = False
        self._refresh_save_button()

    def _unlock_generate(self):
        """Ξεκλείδωμα Δημιουργία μετά από επιτυχές Quota."""
        if hasattr(self, "generate_btn"):
            self.generate_btn.config(state="normal")
        self._refresh_save_button()

    def _freeze_saved_schedule(self):
        """Κλειδώνει ένα αποθηκευμένο πρόγραμμα ώστε να μην ξαναπειραχτεί από το Quota."""
        self.saved_schedule_locked = True
        if hasattr(self, "generate_btn"):
            self.generate_btn.config(state="disabled")
        self._refresh_save_button()

    def _refresh_save_button(self):
        if not hasattr(self, "export_btn"):
            return
        if self.saved_schedule_locked and self.current_schedule:
            self.export_btn.config(
                text="🗑️ Διαγραφή",
                command=lambda: self.app_ref.on_delete_current_saved_schedule(),
                state="normal",
            )
        elif self.current_schedule:
            self.export_btn.config(
                text="💾 Αποθήκευση",
                command=lambda: self.app_ref.on_save_current_schedule(),
                state="normal",
            )
        else:
            self.export_btn.config(
                text="💾 Αποθήκευση",
                command=lambda: self.app_ref.on_save_current_schedule(),
                state="disabled",
            )

    def has_active_schedule_for_planning(self) -> bool:
        """Αν το tab έχει πρόγραμμα που πρέπει να λαμβάνεται υπόψη στους υπολογισμούς."""
        if not self.current_schedule:
            return False
        return self.saved_schedule_locked or self.preset_quotas is not None
    
    def clear_all_preferences(self):
        """Clear all preference entries."""
        for row in self.people_rows:
            row["preference_var"].set("")
    
    
    def _add_row(self, rank: str, name: str, leave: str, preference: str = ""):
        row_frame = ttk.Frame(self.scrollable)
        row_frame.pack(fill="x", pady=2)
        
        rank_var = tk.StringVar(value=rank)
        name_var = tk.StringVar(value=name)
        leave_var = tk.StringVar(value=leave)
        preference_var = tk.StringVar(value=preference)

        def _on_change(*_):
            self._lock_generate()
        for _v in (rank_var, name_var, leave_var, preference_var):
            _v.trace_add("write", _on_change)
        
        ttk.Entry(row_frame, textvariable=rank_var, width=12).grid(row=0, column=0, padx=2)
        ttk.Entry(row_frame, textvariable=name_var, width=20).grid(row=0, column=1, padx=2)
        ttk.Entry(row_frame, textvariable=leave_var, width=18).grid(row=0, column=2, padx=2)
        ttk.Entry(row_frame, textvariable=preference_var, width=18).grid(row=0, column=3, padx=2)
        
        self.people_rows.append({
            "frame": row_frame,
            "rank_var": rank_var,
            "name_var": name_var,
            "leave_var": leave_var,
            "preference_var": preference_var,
        })

    def apply_count(self):
        """Apply the desired number of visible rows.

        - Increasing: adds empty rows.
        - Decreasing: removes ONLY empty rows (anywhere in the list). If there aren't
          enough empty rows to reach the requested count, we reject the change.
        """
        try:
            desired = safe_int(self.count_var.get(), 1)
            if desired < 1:
                desired = 1

            current = len(self.people_rows)

            # If decreasing, remove empty rows only (any position)
            if desired < current:
                need_remove = current - desired

                def is_row_empty(row: dict) -> bool:
                    return (
                        not row["name_var"].get().strip()
                        and not row["rank_var"].get().strip()
                        and not row["leave_var"].get().strip()
                        and not row["preference_var"].get().strip()
                    )

                empty_indices = [i for i, r in enumerate(self.people_rows) if is_row_empty(r)]

                if len(empty_indices) < need_remove:
                    # Reject: user is trying to remove non-empty rows
                    self.count_var.set(str(current))
                    self.active_count.set(current)
                    messagebox.showwarning(
                        "Προσοχή",
                        "Δεν μπορώ να μειώσω το πλήθος γιατί δεν υπάρχουν αρκετές κενές γραμμές."
                        "Άδειασε πρώτα όποιες γραμμές δεν χρειάζεσαι και ξαναδοκίμασε."
                    )
                    return

                # Remove empty rows starting from the bottom-most indices to keep indices stable
                for idx in sorted(empty_indices, reverse=True)[:need_remove]:
                    try:
                        self.people_rows[idx]["frame"].destroy()
                    except Exception:
                        pass
                    del self.people_rows[idx]

                self.active_count.set(desired)
                self.count_var.set(str(desired))
                return

            # If increasing, add rows
            if desired > current:
                while len(self.people_rows) < desired:
                    self._add_row("", "", "", "")
                self.active_count.set(desired)
                self.count_var.set(str(desired))
                return

            # Same number: just sync vars
            self.active_count.set(current)
            self.count_var.set(str(current))

        except Exception as e:
            messagebox.showerror("Σφάλμα", str(e))

    
    
    def parse_people(self, days_in_month: int) -> tuple[list[str], dict[str, set[int]], dict[str, str], dict[str, set[int]]]:
        n = self.active_count.get()
        names = []
        leaves = {}
        ranks = {}
        preferences = {}
        
        for i in range(min(n, len(self.people_rows))):
            row = self.people_rows[i]
            name = row["name_var"].get().strip()
            if not name:
                raise ValueError(f"Το άτομο #{i+1} δεν έχει όνομα.")
            
            names.append(name)
            ranks[name] = row["rank_var"].get().strip()
            
            leave_str = row["leave_var"].get().strip()
            if leave_str:
                leaves[name] = parse_days_list(leave_str, days_in_month)
            
            preference_str = row["preference_var"].get().strip()
            if preference_str:
                preferences[name] = parse_days_list(preference_str, days_in_month)
        
        return names, leaves, ranks, preferences
    
    def collect_data(self):
        """Alias for parse_people - used by unified scheduling."""
        try:
            year = safe_int(self.app_ref.year_var.get(), 2026)
            month = safe_int(self.app_ref.month_var.get(), 3)
            _, days_in_month = calendar.monthrange(year, month)
            return self.parse_people(days_in_month)
        except Exception as e:
            raise ValueError(f"Σφάλμα στο {TAB_TITLES.get(self.tab_key, self.tab_key)}: {str(e)}")
    
    def clear_program_view(self):
        self.stats.config(state="normal")
        self.stats.delete("1.0", "end")
        self.stats.config(state="disabled")
        self.current_schedule = {}
        self.current_ranks = {}
        self.saved_schedule_locked = False
        self._refresh_save_button()
    
    def log(self, message: str, kind: str = "info"):
        self.stats.config(state="normal")
        start = self.stats.index("end-1c")
        self.stats.insert("end", message + "\n")
        end = self.stats.index("end-1c")
        
        if kind == "error":
            self.stats.tag_add("error", start, end)
        elif kind == "info":
            self.stats.tag_add("info", start, end)
        
        self.stats.see("end")
        self.stats.config(state="disabled")
        self.stats.update()
    
    def render_program(self, year, month, extra, sched, ranks, quotas, meta, solve_info):
        self.current_schedule = sched
        self.current_ranks = ranks
        self.saved_schedule_locked = False
        self._refresh_save_button()
        
        self.stats.config(state="normal")
        self.stats.delete("1.0", "end")

        # Compact summary dashboard
        relaxed_rules = []
        summary_items = []
        if "time" in solve_info:
            summary_items.append(f"Χρόνος: {solve_info['time']}")
        if "status" in solve_info:
            summary_items.append(f"Κατάσταση: {solve_info['status']}")

        gap_info = solve_info.get("min_gap_used", {})
        gap_1_users = [name for name, gap in gap_info.items() if gap == 1]
        if gap_1_users:
            relaxed_rules.append(
                f"MIN_GAP=1 (χαλαρό) για: {', '.join(gap_1_users)}"
            )

        if solve_info.get('relaxed_weekend_pair_all_days'):
            relaxed_rules.append("Αγνοήθηκε ο κανόνας Σαβ/Παρ για όλο τον μήνα")
            self.stats.insert("end", "⚠️ ΠΡΟΣΟΧΗ: Αγνοήθηκε ο κανόνας Σαβ/Παρ για όλο τον μήνα\n", "warning")
            self.stats.insert("end", "    (Το πρόγραμμα δεν έβγαινε χωρίς αυτή τη χαλάρωση)\n", "warning")
        elif solve_info.get('relaxed_weekend_pair_days'):
            _rdays = solve_info['relaxed_weekend_pair_days']
            _rstr  = ", ".join(f"{d}/{month}" for d in _rdays)
            relaxed_rules.append(f"Αγνοήθηκε ο κανόνας Σαβ/Παρ για: {_rstr}")
            self.stats.insert("end", f"⚠️ ΠΡΟΣΟΧΗ: Αγνοήθηκε ο κανόνας Σαβ/Παρ για: {_rstr}\n", "warning")
            self.stats.insert("end", "    (Το πρόγραμμα δεν έβγαινε χωρίς αυτή τη χαλάρωση)\n", "warning")
        if solve_info.get('relaxed_holiday_balance'):
            _rdays = solve_info.get('relaxed_constraint_days', [])
            if _rdays:
                _rstr = ", ".join(f"{d}/{month}" for d in _rdays)
                relaxed_rules.append(f"Στις μέρες εμπλοκής ({_rstr}) ίσχυσε μόνο GAP=1")
                self.stats.insert("end", f"⚠️ ΠΡΟΣΟΧΗ: Στις μέρες εμπλοκής ({_rstr}) ίσχυσε μόνο GAP=1\n", "warning")
                self.stats.insert("end", "    (Τοπική χαλάρωση μόνο στις προβληματικές μέρες)\n", "warning")
            relaxed_rules.append("Αγνοήθηκε ο κανόνας ισορροπίας αργιών")
            self.stats.insert("end", "⚠️ ΠΡΟΣΟΧΗ: Αγνοήθηκε ο κανόνας ισορροπίας αργιών\n", "warning")
            self.stats.insert("end", "    (Το πρόγραμμα δεν έβγαινε χωρίς αυτή τη χαλάρωση)\n", "warning")

        holiday_counts = [m.get("HOLIDAY", 0) for m in meta.values()]
        if holiday_counts and (max(holiday_counts) - min(holiday_counts) > 1):
            if "Δεν τηρήθηκε πλήρως η ισορροπία αργιών" not in relaxed_rules:
                relaxed_rules.append("Δεν τηρήθηκε πλήρως η ισορροπία αργιών")
            self.stats.insert("end", "⚠️ Δεν τηρήθηκε πλήρως η ισορροπία αργιών\n", "warning")
            self.stats.insert(
                "end",
                f"    (Ελάχιστες αργίες: {min(holiday_counts)}, μέγιστες αργίες: {max(holiday_counts)})\n",
                "warning",
            )

        friday_counts = [m.get("FRIDAY", 0) for m in meta.values()]
        if friday_counts and (max(friday_counts) - min(friday_counts) > 1):
            if "Δεν τηρήθηκε πλήρως η ισορροπία Παρασκευών" not in relaxed_rules:
                relaxed_rules.append("Δεν τηρήθηκε πλήρως η ισορροπία Παρασκευών")
            self.stats.insert("end", "⚠️ Δεν τηρήθηκε πλήρως η ισορροπία Παρασκευών\n", "warning")
            self.stats.insert(
                "end",
                f"    (Ελάχιστες Παρασκευές: {min(friday_counts)}, μέγιστες Παρασκευές: {max(friday_counts)})\n",
                "warning",
            )

        displayed_total_quotas = dict(self.preset_quotas) if self.preset_quotas else dict(quotas or {})

        quota_deltas = {}
        if displayed_total_quotas:
            for person in meta.keys():
                actual_total = int(meta.get(person, {}).get("total", 0))
                target_total = int(displayed_total_quotas.get(person, quotas.get(person, 0) if quotas else 0))
                if actual_total != target_total:
                    quota_deltas[person] = actual_total - target_total

        if quota_deltas:
            if "Δεν τηρήθηκε πλήρως το TOTAL quota" not in relaxed_rules:
                relaxed_rules.append("Δεν τηρήθηκε πλήρως το TOTAL quota")
            self.stats.insert("end", "⚠️ Δεν τηρήθηκε πλήρως το TOTAL quota\n", "warning")
            for person, delta in sorted(quota_deltas.items(), key=lambda item: (-abs(item[1]), item[0])):
                actual_total = int(meta.get(person, {}).get("total", 0))
                target_total = int(displayed_total_quotas.get(person, quotas.get(person, 0) if quotas else 0))
                sign = "+" if delta > 0 else ""
                self.stats.insert(
                    "end",
                    f"    - {person}: στόχος {target_total}, τελικό {actual_total} ({sign}{delta})\n",
                    "warning",
                )

        preference_issues = solve_info.get("preference_issues", [])
        if preference_issues:
            relaxed_rules.append("Αγνοήθηκαν κάποιες επιθυμίες")
            self.stats.insert("end", "⚠️ Αγνοήθηκαν κάποιες επιθυμίες\n", "warning")
            for issue in preference_issues:
                self.stats.insert("end", f"    - {issue}\n", "warning")

        summary_items.append("Χαλαρώσεις: " + (", ".join(relaxed_rules) if relaxed_rules else "Καμία"))
        summary_items.append(f"Αγνοημένες επιθυμίες: {len(preference_issues)}")
        if displayed_total_quotas:
            summary_items.append(f"TOTAL quota: {'ΟΚ' if not quota_deltas else 'Όχι πλήρως'}")
        if holiday_counts:
            summary_items.append(
                f"Ισορροπία αργιών: {'ΟΚ' if max(holiday_counts) - min(holiday_counts) <= 1 else 'Όχι πλήρως'}"
            )
        if friday_counts:
            summary_items.append(
                f"Ισορροπία Παρασκευών: {'ΟΚ' if max(friday_counts) - min(friday_counts) <= 1 else 'Όχι πλήρως'}"
            )

        self.stats.insert("end", "="*80 + "\n")
        self.stats.insert("end", "ΣΥΝΟΨΗ\n")
        self.stats.insert("end", "="*80 + "\n")
        for item in summary_items:
            self.stats.insert("end", f"{item}\n")
        self.stats.insert("end", "\n")

        if relaxed_rules:
            self.stats.insert("end", "\n" + "-"*50 + "\n")
            self.stats.insert("end", "ΚΑΝΟΝΕΣ ΠΟΥ ΧΑΛΑΡΩΣΑΝ / ΑΓΝΟΗΘΗΚΑΝ\n")
            self.stats.insert("end", "-"*50 + "\n")
            for rule in relaxed_rules:
                self.stats.insert("end", f"- {rule}\n")

        self.stats.insert("end", "\n")
        
        _, days_in_month = calendar.monthrange(year, month)
        for day in range(1, days_in_month + 1):
            person = sched.get(day, "---")
            rank = ranks.get(person, "")
            
            # Show actual weekday instead of ΑΡΓΙΑ/ΚΑΘΗΜΕΡΙΝΗ
            date_obj = dt.date(year, month, day)
            weekday = date_obj.strftime("%A")
            weekday_gr = {
                "Monday": "ΔΕΥΤΕΡΑ", "Tuesday": "ΤΡΙΤΗ", "Wednesday": "ΤΕΤΑΡΤΗ",
                "Thursday": "ΠΕΜΠΤΗ", "Friday": "ΠΑΡΑΣΚΕΥΗ",
                "Saturday": "ΣΑΒΒΑΤΟ", "Sunday": "ΚΥΡΙΑΚΗ"
            }.get(weekday, weekday)
            
            date_str = f"{day:2d}-{GREEK_MONTH_ABBR[month]}"
            line = f"{date_str} ({weekday_gr:12s}): {rank} {person}\n"
            self.stats.insert("end", line)
        
        self.stats.insert("end", "\n" + "="*145 + "\n")
        self.stats.insert("end", "ΣΤΑΤΙΣΤΙΚΑ\n")
        self.stats.insert("end", "="*145 + "\n\n")
        
        # Table header with proper alignment
        header = f"{'Βαθμός':<15} {'Όνομα':<20} {'Καθημ.':<10} {'Παρ.':<10} {'Αργίες':<10} {'TOTAL':<10} {'POINTS':<10}\n"
        header = header[:-1] + f" {'Ημερομηνίες':<30}\n"
        self.stats.insert("end", header)
        self.stats.insert("end", "-"*145 + "\n")
        
        scores = []
        for person in sorted(meta.keys()):
            m = meta[person]
            total = m["total"]
            weekday = m["WEEKDAY"]  # Mon-Thu
            friday = m["FRIDAY"]    # Friday
            holiday = m["HOLIDAY"]  # Sat/Sun/Holidays
            score = m["score"]
            scores.append(score)
            
            rank = ranks.get(person, "")
            service_dates = sorted(
                m.get("weekday_dates", []) + m.get("friday_dates", []) + m.get("holiday_dates", [])
            )
            service_dates_str = ",".join(str(day) for day in service_dates)
            
            # Format as table row with aligned columns
            row = f"{rank:<15} {person:<20} {weekday:<10} {friday:<10} {holiday:<10} {total:<10} {score:<10.1f} {service_dates_str:<30}\n"
            
            start = self.stats.index("end-1c")
            self.stats.insert("end", row)
            end = self.stats.index("end-1c")
            
            if total >= 5:
                self.stats.tag_add("warn_total", start, end)
        
        if scores:
            self.stats.insert("end", f"\nScore spread (max-min) = {max(scores) - min(scores):.2f}\n")
            # Spread only for people with 3+ total services
            _scores_3plus = [meta[p]["score"] for p in meta if meta[p]["total"] >= 3]
            if _scores_3plus and len(_scores_3plus) < len(scores):
                self.stats.insert("end", f"Score spread (≥3 υπηρεσίες) = {max(_scores_3plus) - min(_scores_3plus):.2f}\n")
        
        # Summary of MIN_GAP usage
        gap_info = solve_info.get('min_gap_used', {})
        if gap_info:
            gap_1_users = [name for name, gap in gap_info.items() if gap == 1]
            gap_2_users = [name for name, gap in gap_info.items() if gap == 2]
            
            self.stats.insert("end", "\n" + "-"*50 + "\n")
            self.stats.insert("end", "MIN_GAP ΧΡΗΣΗ\n")
            self.stats.insert("end", "-"*50 + "\n")
            
            if gap_2_users:
                self.stats.insert("end", f"GAP=2 (κανονικό): {', '.join(gap_2_users)}\n")
            
            if gap_1_users:
                self.stats.insert("end", f"GAP=1 (χαλαρό): {', '.join(gap_1_users)}\n")
                self.stats.insert("end", f"  {len(gap_1_users)} άτομ{'ο' if len(gap_1_users) == 1 else 'α'} με περιορισμένη διαθεσιμότητα\n")
        
        self.stats.config(state="disabled")
        self.export_btn.config(state="normal")
    
    def set_tab_state(self, tab_state: dict):
        count = safe_int(str(tab_state.get("count", 0)), 0)
        people = tab_state.get("people", [])
        if not isinstance(people, list):
            people = []
        
        while len(self.people_rows) < max(1, count):
           self._add_row("", "", "", "")
        
        for i in range(max(0, count)):
            if i < len(people):
                p = people[i] if isinstance(people[i], dict) else {}
                self.people_rows[i]["rank_var"].set(str(p.get("rank", "")).strip())
                self.people_rows[i]["name_var"].set(str(p.get("name", "")).strip())
                self.people_rows[i]["leave_var"].set(str(p.get("leave", "")).strip())
                self.people_rows[i]["preference_var"].set(str(p.get("preference", "")).strip())
            else:
                self.people_rows[i]["rank_var"].set("")
                self.people_rows[i]["name_var"].set("")
                self.people_rows[i]["leave_var"].set("")
                self.people_rows[i]["preference_var"].set("")
        
        if count <= 0:
            count = 1
        self.count_var.set(str(count))
        self.active_count.set(count)
        self.apply_count()
        
        self.clear_program_view()
        
        # Restore saved schedule/ranks/display text if present
        if "saved_schedule" in tab_state and tab_state["saved_schedule"]:
            self.current_schedule = {int(k): v for k, v in tab_state["saved_schedule"].items()}
            self.current_ranks = tab_state.get("saved_ranks", {})
            self.saved_schedule_locked = True
            saved_text = tab_state.get("saved_stats_text", "")
            if saved_text:
                try:
                    self.stats.config(state="normal")
                    self.stats.delete("1.0", "end")
                    self.stats.insert("end", saved_text)
                    self.stats.config(state="disabled")
                    self._refresh_save_button()
                except Exception:
                    self._refresh_save_button()
    
    

    def get_tab_state(self) -> dict:
        n = self.active_count.get()
        if n < 1:
            n = 1
        self.count_var.set(str(n))
        people = []
        for i in range(min(n, len(self.people_rows))):
            row = self.people_rows[i]
            people.append({
                "rank": row["rank_var"].get().strip(),
                "name": row["name_var"].get().strip(),
                "leave": row["leave_var"].get().strip(),
                "preference": row["preference_var"].get().strip(),
            })
        state = {"count": n, "people": people}
        # Also save the current schedule/ranks/display text if exists
        if self.current_schedule:
            state["saved_schedule"] = {str(k): v for k, v in self.current_schedule.items()}
            state["saved_ranks"] = self.current_ranks
            # Save the stats text for display on reload
            try:
                self.stats.config(state="normal")
                state["saved_stats_text"] = self.stats.get("1.0", "end")
                self.stats.config(state="disabled")
            except Exception:
                pass
        return state


# -----------------------------
# History Viewer + Editor Dialog (AGGREGATED VIEW)
# -----------------------------
class SchedulerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Scheduler")
        self.geometry("1250x820")
        
        self.year_var = tk.StringVar(value="2026")
        self.month_var = tk.StringVar(value="3")
        self.extra_var = tk.StringVar(value="")

        def _on_shared_change(*_):
            if hasattr(self, "tabs"):
                for tab in self.tabs.values():
                    tab._lock_generate()
        self.year_var.trace_add("write", _on_shared_change)
        self.month_var.trace_add("write", _on_shared_change)
        self.extra_var.trace_add("write", _on_shared_change)

        # Οποιαδήποτε αλλαγή στις κοινές ρυθμίσεις κλειδώνει όλα τα tabs
        def _on_shared_change(*_):
            if hasattr(self, "tabs"):
                for tab in self.tabs.values():
                    tab._lock_generate()
        self.year_var.trace_add("write", _on_shared_change)
        self.month_var.trace_add("write", _on_shared_change)
        self.extra_var.trace_add("write", _on_shared_change)
        
        self._build_menu()
        self._build_ui()
        self.load_state()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def _build_menu(self):
        """Build menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        menubar.add_command(label="Ιστορικό", command=self.on_edit_history)
    
    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        
        top = ttk.LabelFrame(root, text="Κοινές Ρυθμίσεις (για ΟΛΑ τα φύλλα)", padding=10)
        top.pack(fill="x", pady=(0, 10))
        
        ttk.Label(top, text="Έτος:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.year_var, width=10).grid(row=0, column=1, sticky="w", padx=(6, 12))
        
        ttk.Label(top, text="Μήνας (1-12):").grid(row=0, column=2, sticky="w")
        ttk.Entry(top, textvariable=self.month_var, width=10).grid(row=0, column=3, sticky="w", padx=(6, 12))
        
        ttk.Label(top, text="Extra αργίες (πχ 25 ή 6,25 ή 6-10):").grid(row=0, column=4, sticky="w")
        ttk.Entry(top, textvariable=self.extra_var, width=18).grid(row=0, column=5, sticky="w", padx=(6, 12))
        
        # Unified "Generate All" button
        ttk.Button(top, text="📊 Quota ΟΛΩΝ", command=self.on_preview_quotas_all).grid(
            row=0, column=6, sticky="w", padx=(12, 6)
        )
    
        # Export All button
        ttk.Button(top, text="📄 Export ΟΛΩΝ", command=self.on_export_all_word).grid(
            row=0, column=7, sticky="w", padx=(0, 12)
        )
        
        solver_status = "ΜΟΝΟ Π@@@ L&G"
        ttk.Label(top, text=solver_status, foreground="blue").grid(
            row=0, column=8, sticky="w", padx=(12, 0)
        )

        
        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True)
        
        self.tabs: dict[str, PeopleTab] = {}
        for key in TAB_KEYS:
            tab = PeopleTab(self.nb, tab_key=key, app_ref=self)
            self.nb.add(tab, text=TAB_TITLES.get(key, key))
            self.tabs[key] = tab
    
    def current_tab_key(self) -> str:
        idx = self.nb.index(self.nb.select())
        return TAB_KEYS[idx]
    
    def get_shared_settings(self):
        year = safe_int(self.year_var.get(), 2026)
        month = safe_int(self.month_var.get(), 3)
        if month < 1 or month > 12:
            raise ValueError("Ο μήνας πρέπει να είναι 1-12.")
        _, dim = calendar.monthrange(year, month)
        extra = parse_days_list(self.extra_var.get(), dim)
        return year, month, extra

    def _predict_unsolved_tab_reservations(
        self,
        current_key: str,
        current_names: list[str],
        year: int,
        month: int,
    ) -> tuple[dict[str, set[int]], list[str]]:
        """
        Κρατάει κοινά άτομα ελεύθερα για άλλα tabs που δεν έχουν ακόμα πρόγραμμα,
        όταν εκεί υπάρχουν πολύ κρίσιμες μέρες με ελάχιστους υποψηφίους.

        Η ιδέα είναι απλή:
        - αν σε άλλο tab μια μέρα έχει <=3 υποψηφίους,
        - και ένα κοινό άτομο είναι μέσα σε αυτούς,
        - τότε στο τρέχον tab μπλοκάρουμε όλες τις μέρες που θα του έκαιγαν αυτή
          τη μέρα μέσω cross-tab blocking.
        """
        _, dim = calendar.monthrange(year, month)
        reservations = {person: set() for person in current_names}
        notes: list[str] = []

        current_name_set = set(current_names)
        critical_threshold = 3

        for other_key in TAB_KEYS:
            if other_key == current_key:
                continue

            other_tab = self.tabs[other_key]
            if other_tab.current_schedule:
                # Αν υπάρχει ήδη πρόγραμμα στο άλλο tab, θα ληφθεί υπόψη από το
                # κανονικό cross-tab blocking πιο κάτω.
                continue

            try:
                other_names, other_leaves, _, _ = other_tab.parse_people(dim)
            except Exception:
                continue

            if not other_names:
                continue

            shared_people = current_name_set.intersection(other_names)
            if not shared_people:
                continue

            per_person_critical_days: dict[str, set[int]] = {p: set() for p in shared_people}

            for day in range(1, dim + 1):
                candidates = [
                    person for person in other_names
                    if day not in other_leaves.get(person, set())
                ]
                if len(candidates) > critical_threshold:
                    continue

                for person in shared_people.intersection(candidates):
                    per_person_critical_days[person].add(day)

            for person, critical_days in per_person_critical_days.items():
                if not critical_days:
                    continue
                reserve_days = cross_tab_blocked_days(critical_days, current_key, year, month)
                reservations[person].update(reserve_days)
                notes.append(
                    f"{person}: κρατήθηκε για κρίσιμες μέρες του {TAB_TITLES.get(other_key, other_key)} "
                    f"{sorted(critical_days)}"
                )

        return reservations, notes

    def on_preview_quotas_all(self):
        """Υπολογισμός GLOBAL quotas για όλες τις υπηρεσίες."""
        try:
            year, month, extra = self.get_shared_settings()
            _, dim = calendar.monthrange(year, month)
        except Exception as e:
            messagebox.showerror("Σφάλμα", str(e))
            return

        import time as _t

        total_holidays = sum(1 for d in range(1, dim + 1) if day_bucket(year, month, d, extra) == "HOLIDAY")
        total_fridays  = sum(1 for d in range(1, dim + 1) if dt.date(year, month, d).weekday() == 4)
        total_weekdays = dim - total_holidays - total_fridays

        # 1) μάζεψε όλα τα tabs
        all_tabs_data = {}
        unlocked_tabs_data = {}
        locked_tabs = []
        for key in TAB_KEYS:
            tab = self.tabs[key]
            if not tab.saved_schedule_locked:
                tab.clear_program_view()
            else:
                locked_tabs.append(TAB_TITLES.get(key, key))
            try:
                names, leaves, ranks, preferences = tab.parse_people(dim)
                if names:
                    tab_payload = {
                        "names": names,
                        "leaves": leaves,
                        "ranks": ranks,
                        "preferences": preferences,
                    }
                    all_tabs_data[key] = tab_payload
                    if not tab.saved_schedule_locked:
                        unlocked_tabs_data[key] = tab_payload
            except Exception as e:
                self.tabs[key].log(f"Σφάλμα parse: {e}", kind="error")

        if not all_tabs_data:
            if locked_tabs:
                messagebox.showinfo(
                    "Quota ΟΛΩΝ",
                    "Όλα τα διαθέσιμα tabs είναι ήδη αποθηκευμένα και κλειδωμένα.\n"
                    "Άλλαξε κάποια παράμετρο αν θέλεις να ξαναϋπολογιστούν."
                )
            else:
                messagebox.showwarning("Προσοχή", "Δεν υπάρχουν δεδομένα.")
            return

        if not unlocked_tabs_data:
            messagebox.showinfo(
                "Quota ΟΛΩΝ",
                "Δεν υπάρχουν ξεκλείδωτα tabs για νέο υπολογισμό.\n"
                "Τα αποθηκευμένα tabs παραμένουν όπως είναι."
            )
            return

        try:
            import hashlib

            _seed_payload = (
                year,
                month,
                tuple(sorted(extra)),
                tuple(
                    (
                        key,
                        tuple(all_tabs_data[key]["names"]),
                        tuple(
                            (name, tuple(sorted(all_tabs_data[key]["leaves"].get(name, set()))))
                            for name in sorted(all_tabs_data[key]["names"])
                        ),
                        tuple(
                            (name, all_tabs_data[key]["ranks"].get(name, ""))
                            for name in sorted(all_tabs_data[key]["names"])
                        ),
                    )
                    for key in sorted(all_tabs_data)
                ),
                tuple(sorted(locked_tabs)),
            )
            _seed = int(hashlib.sha256(repr(_seed_payload).encode("utf-8")).hexdigest()[:16], 16)
            _rng = random.Random(_seed)

            # 2) global totals
            global_total_quotas = compute_global_total_quotas(year, month, all_tabs_data, _rng)

            locked_assigned_totals = {}
            for key in TAB_KEYS:
                tab = self.tabs[key]
                if not tab.saved_schedule_locked or not tab.current_schedule:
                    continue
                for _day, _person in tab.current_schedule.items():
                    locked_assigned_totals[_person] = locked_assigned_totals.get(_person, 0) + 1

            remaining_global_quotas = {
                name: max(0, int(global_total_quotas.get(name, 0)) - int(locked_assigned_totals.get(name, 0)))
                for name in global_total_quotas
            }

            # 3) split στα tabs
            per_tab_total_quotas = split_global_quotas_to_tabs(
                year=year,
                month=month,
                all_tabs_data=unlocked_tabs_data,
                global_total_quotas=remaining_global_quotas,
            )

            success_count = 0

            for key in TAB_KEYS:
                tab = self.tabs[key]
                if tab.saved_schedule_locked:
                    continue
                if key not in all_tabs_data:
                    tab.log("Δεν υπάρχουν άτομα - παράλειψη.", kind="info")
                    continue

                names = all_tabs_data[key]["names"]
                leaves = all_tabs_data[key]["leaves"]
                ranks = all_tabs_data[key]["ranks"]

                cumulative = calculate_cumulative_stats(year, month, key, names)

                q_total = dict(per_tab_total_quotas.get(key, {}))
                auto_max, _ = compute_auto_max_from_leaves(
                    names, dim, leaves, MIN_GAP_STRICT, log_cb=lambda m: None
                )
                q_total = repair_total_quotas_for_availability(
                    names=names,
                    quotas_total=q_total,
                    days_in_month=dim,
                    leaves=leaves,
                    max_caps=auto_max,
                    log_cb=lambda m: tab.log(m, kind="info"),
                )

                q_hol = compute_holiday_quotas_with_history(
                    names, total_holidays, cumulative, ranks or {}, _rng,
                    leaves=leaves, year=year, month=month, extra_holidays=extra,
                )

                q_fri = compute_friday_quotas_with_history(
                    names, total_fridays, cumulative, ranks or {}, _rng,
                    leaves=leaves, year=year, month=month,
                )

                # clamp ώστε να μην ξεφεύγουν πάνω από το TOTAL
                for name in names:
                    qt = q_total.get(name, 0)
                    q_hol[name] = min(q_hol.get(name, 0), qt)
                    q_fri[name] = min(q_fri.get(name, 0), max(0, qt - q_hol[name]))

                tab.log(f"📊 GLOBAL Quotas {TAB_TITLES.get(key, key)} - {GREEK_MONTHS_GEN[month]} {year}", kind="info")
                tab.log(f"   Μέρες: {dim}  |  Αργίες: {total_holidays}  |  Παρ: {total_fridays}  |  Καθημ.: {total_weekdays}", kind="info")
                tab.log("", kind="info")
                tab.log(f"{'Όνομα':<22} {'TOTAL':>6} {'Ιστ.':>6}", kind="info")
                tab.log("-" * 40, kind="info")

                for name in names:
                    qt = q_total.get(name, 0)
                    hist = cumulative.get(name, {})
                    ht = hist.get("total_weekdays", 0) + hist.get("total_fridays", 0) + hist.get("total_holidays", 0)
                    tab.log(f"{name:<22} {qt:>6}   {ht:>5}", kind="info")

                tab.log("", kind="info")
                tab.log(f"{'ΣΥΝΟΛΑ':<22} {sum(q_total.values()):>6}", kind="info")
                tab.log("", kind="info")
                tab.log("✅ Έτοιμο - πάτα Δημιουργία.", kind="info")

                tab.preset_quotas = q_total
                tab.preset_holiday_quotas = q_hol
                tab.preset_friday_quotas = q_fri
                tab._unlock_generate()
                success_count += 1

            messagebox.showinfo(
                "Quota ΟΛΩΝ",
                f"Τα global quotas υπολογίστηκαν για {success_count} υπηρεσίες.\n"
                + (f"Παραλείφθηκαν αποθηκευμένα tabs: {', '.join(locked_tabs)}.\n" if locked_tabs else "")
                + "Μπορείς να πατήσεις Δημιουργία στα tabs που ξεκλείδωσαν."
            )

        except Exception as e:
            import traceback
            messagebox.showerror("Σφάλμα Global Quota", f"{e}\n\n{traceback.format_exc()}")

    def on_generate_all_unified(self):
        """Generate all tabs together (unified scheduling to avoid conflicts)."""
        year, month, extra = self.get_shared_settings()
        _, days_in_month = calendar.monthrange(year, month)

        # Collect data from all tabs
        all_tabs_data = {}
        for key in TAB_KEYS:
            try:
                # Call parse_people directly with days_in_month
                names, leaves, ranks, preferences = self.tabs[key].parse_people(days_in_month)
                if names:  # Only include non-empty tabs
                    all_tabs_data[key] = {
                        "names": names,
                        "leaves": leaves,
                        "ranks": ranks,
                        "preferences": preferences,
                    }
            except Exception as e:
                messagebox.showerror("Σφάλμα", f"Σφάλμα στο {TAB_TITLES[key]}: {str(e)}")
                return
        
        if not all_tabs_data:
            messagebox.showwarning("Προσοχή", "Δεν υπάρχουν δεδομένα σε κανένα tab!")
            return
        
        # Clear all tabs first and start a fresh debug session per tab
        for key, tab in self.tabs.items():
            tab.clear_program_view()
            tab.log("----- Νέα εκτέλεση (ΔΗΜΙΟΥΡΓΙΑ ΟΛΩΝ) -----")
        
        # Run unified scheduling (route debug logs into each tab's right panel)
        try:
            start_key = self.current_tab_key()

            def gui_log(tab_key, message: str):
                target = tab_key or start_key
                if target not in self.tabs:
                    target = start_key
                kind = "error" if str(message).lstrip().startswith("Σφάλμα") else "info"
                self.tabs[target].log(message, kind=kind)

            results = solve_all_tabs_unified(
                all_tabs_data=all_tabs_data,
                year=year,
                month=month,
                extra_holidays=extra,
                log_cb=gui_log,
            )
            
            # Display results in each tab
            for key, (schedule, quotas, meta, solve_info) in results.items():
                self.tabs[key].render_program(year, month, extra, schedule, 
                                              all_tabs_data[key]["ranks"], quotas, meta, solve_info)
            
            messagebox.showinfo("Επιτυχία", 
                              f"Δημιουργήθηκαν {len(results)} προγράμματα χωρίς συγκρούσεις!")
            
        except ScheduleError as e:
            messagebox.showerror("Αδύνατο πρόγραμμα", f"{str(e)}\n\n{e.details}")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Απρόσμενο σφάλμα:\n{str(e)}")
    
    def on_export_all_word(self):
        """Export all tabs to a single Word file (4 pages) και ενημερώνει το history."""
        year, month, extra = self.get_shared_settings()
        
        # Collect data from all tabs that have schedules
        export_data = []
        for key in TAB_KEYS:
            if self.tabs[key].current_schedule:
                export_data.append({
                    "tab_key": key,
                    "schedule": self.tabs[key].current_schedule,
                    "ranks": self.tabs[key].current_ranks,
                })
        
        if not export_data:
            messagebox.showwarning("Προσοχή", "Δεν υπάρχουν προγράμματα για export!")
            return
        
        # Ask for filename
        default_name = f"Προγραμματα_{GREEK_MONTHS_GEN[month]}_{year}.docx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Documents", "*.docx")],
            initialfile=default_name
        )
        
        if not filepath:
            return
        
        try:
            export_all_schedules_to_word(
                filepath=filepath,
                export_data=export_data,
                year=year,
                month=month,
                extra_holidays=extra,
            )

            for data in export_data:
                add_to_history(
                    year=year,
                    month=month,
                    tab_key=data["tab_key"],
                    schedule=data["schedule"],
                    ranks=data["ranks"],
                    extra_holidays=extra,
                )

            self.save_schedule_state()
            messagebox.showinfo(
                "Επιτυχία", 
                f"Εξαγωγή σε:\n{filepath}\n\nΗ εξαγωγή ολοκληρώθηκε και ενημερώθηκε το ιστορικό."
            )
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία εξαγωγής:\n{str(e)}")
    
    def on_generate_current(self):
        key = self.current_tab_key()
        tab = self.tabs[key]
        try:
            year, month, extra = self.get_shared_settings()
            _, dim = calendar.monthrange(year, month)

            tab.clear_program_view()
            tab.log("----- Νέα εκτέλεση -----")

            names, leaves, ranks, preferences = tab.parse_people(dim)

            # Cross-tab blocking από schedules άλλων tabs
            extended_leaves = {}
            predicted_reservations, reservation_notes = self._predict_unsolved_tab_reservations(
                key, names, year, month
            )
            for note in reservation_notes:
                tab.log(f"  Προτεραιότητα άλλου tab: {note}", kind="info")

            for person in names:
                person_leaves = set(leaves.get(person, set()))
                person_leaves.update(predicted_reservations.get(person, set()))
                for other_key in TAB_KEYS:
                    if other_key == key:
                        continue
                    if not self.tabs[other_key].has_active_schedule_for_planning():
                        continue
                    other_sched = self.tabs[other_key].current_schedule
                    if not other_sched:
                        continue
                    # Βρες τις μέρες που ο person δουλεύει στο άλλο tab
                    other_days = {d for d, p in other_sched.items() if p == person}
                    if not other_days:
                        continue
                    blocked = cross_tab_blocked_days(other_days, other_key, year, month)
                    extra_blocked = blocked - other_days
                    person_leaves.update(blocked)
                    tab.log(f"  Προειδοποίηση: {person}: cross-tab {other_key} μέρες {sorted(other_days)}, blocked +{sorted(extra_blocked)}", kind="info")
                extended_leaves[person] = person_leaves

            # Υπολογισμός cross-tab αργιών/Παρασκευών από saved schedules άλλων tabs
            _other_scheds = {}
            for other_key in TAB_KEYS:
                if other_key == key:
                    continue
                if not self.tabs[other_key].has_active_schedule_for_planning():
                    continue
                other_sched = self.tabs[other_key].current_schedule
                if not other_sched:
                    continue
                _other_scheds[other_key] = {str(d): p for d, p in other_sched.items()}
            cross_hol, cross_fri = compute_cross_tab_counts(
                names, _other_scheds, year, month, extra
            )
            if any(v > 0 for v in cross_hol.values()):
                tab.log(f"  Cross-tab αργίες: { {p:v for p,v in cross_hol.items() if v>0} }", kind="info")

            sched, quotas, meta, solve_info = solve_schedule_best_effort(
                names=names,
                year=year,
                month=month,
                extra_holidays=extra,
                leaves=extended_leaves,
                preferences=preferences,
                ranks=ranks,
                tab_key=key,
                log_cb=lambda m: tab.log(m, kind="info"),
                cross_tab_holidays=cross_hol,
                cross_tab_fridays=cross_fri,
                preset_quotas=tab.preset_quotas,
                preset_holiday_quotas=tab.preset_holiday_quotas,
                preset_friday_quotas=tab.preset_friday_quotas,
            )
            
            tab.render_program(year, month, extra, sched, ranks, quotas, meta, solve_info)
            messagebox.showinfo("OK", "Βγήκε νέο πρόγραμμα.")
        
        except ScheduleError as e:
            tab.log(e.details, kind="error")
            messagebox.showerror("Σφάλμα", e.details)
        except Exception as e:
            import traceback
            full = traceback.format_exc()
            tab.log(f"ΕΣΩΤΕΡΙΚΟ ΣΦΑΛΜΑ:\n{full}", kind="error")
            messagebox.showerror("Σφάλμα", f"Εσωτερικό σφάλμα:\n{str(e)}\n\nΔείτε το log για λεπτομέρειες.")

    def on_save_current_schedule(self):
        """Αποθηκεύει το πρόγραμμα του tab χωρίς ενημέρωση history."""
        try:
            key = self.current_tab_key()
            tab = self.tabs[key]
            if not tab.current_schedule:
                raise RuntimeError("Δεν υπάρχει πρόγραμμα.")

            self.save_state()
            self.save_schedule_state(tab_keys=[key])
            tab._freeze_saved_schedule()
            messagebox.showinfo("Αποθήκευση", f"Αποθηκεύτηκε το πρόγραμμα {TAB_TITLES.get(key, key)}.\nΤο ιστορικό ενημερώνεται μόνο με Export.")
        except Exception as e:
            messagebox.showerror("Σφάλμα", str(e))

    def on_delete_current_saved_schedule(self):
        """Διαγράφει το αποθηκευμένο πρόγραμμα μόνο του τρέχοντος tab."""
        try:
            key = self.current_tab_key()
            tab = self.tabs[key]

            if not tab.current_schedule:
                raise RuntimeError("Δεν υπάρχει αποθηκευμένο πρόγραμμα.")

            tab.saved_schedule_locked = False
            tab.current_schedule = {}
            tab.current_ranks = {}
            self.save_schedule_state(tab_keys=[key])
            tab._lock_generate()
            tab.clear_program_view()

            messagebox.showinfo("Διαγραφή", f"Διαγράφηκε το αποθηκευμένο πρόγραμμα {TAB_TITLES.get(key, key)}.")
        except Exception as e:
            messagebox.showerror("Σφάλμα", str(e))


    def on_manual_save_state(self):
        """Manually save the current application state to JSON."""
        self.save_state()
        self.save_schedule_state()
        messagebox.showinfo("Αποθήκευση", "Το state αποθηκεύτηκε.")
        
    def save_state(self):
        """Αποθηκεύει ΜΟΝΟ τα inputs (άτομα, ρυθμίσεις) - καλείται στο κλείσιμο και αυτόματα."""
        try:
            people_state = {
                "year": safe_int(self.year_var.get(), 2026),
                "month": safe_int(self.month_var.get(), 3),
                "extra": self.extra_var.get().strip(),
                "active_tab": self.current_tab_key(),
                "tabs": {},
            }
            for key in TAB_KEYS:
                tab_state = self.tabs[key].get_tab_state()
                # Αποθήκευσε ΜΟΝΟ τα people inputs, όχι το schedule
                people_state["tabs"][key] = {
                    "count": tab_state.get("count", 1),
                    "people": tab_state.get("people", []),
                }
            
            with open(get_state_path(), "w", encoding="utf-8") as f:
                json.dump(people_state, f, ensure_ascii=False, indent=2)
        except Exception:
            return

    def save_schedule_state(self, tab_keys=None):
        """Αποθηκεύει τα παραγόμενα προγράμματα.

        Αν δοθούν `tab_keys`, ενημερώνει μόνο αυτά τα tabs και κρατά τα υπόλοιπα
        ήδη αποθηκευμένα όπως είναι.
        """
        try:
            schedule_path = get_schedule_path()
            schedule_state = {"tabs": {}}

            if os.path.exists(schedule_path):
                try:
                    with open(schedule_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    if isinstance(loaded, dict) and isinstance(loaded.get("tabs"), dict):
                        schedule_state["tabs"] = dict(loaded["tabs"])
                except Exception:
                    schedule_state = {"tabs": {}}

            target_keys = list(tab_keys) if tab_keys is not None else list(TAB_KEYS)

            for key in target_keys:
                tab_state = self.tabs[key].get_tab_state()
                sched_data = {}
                if "saved_schedule" in tab_state:
                    sched_data["saved_schedule"] = tab_state["saved_schedule"]
                if "saved_ranks" in tab_state:
                    sched_data["saved_ranks"] = tab_state["saved_ranks"]
                if "saved_stats_text" in tab_state:
                    sched_data["saved_stats_text"] = tab_state["saved_stats_text"]

                if sched_data:
                    schedule_state["tabs"][key] = sched_data
                elif key in schedule_state["tabs"]:
                    del schedule_state["tabs"][key]
            
            with open(schedule_path, "w", encoding="utf-8") as f:
                json.dump(schedule_state, f, ensure_ascii=False, indent=2)
        except Exception:
            return
    
    def load_state(self):
        """Φορτώνει inputs από scheduler_people.json και προγράμματα από scheduler_schedule.json."""
        # --- Φόρτωση inputs (people) ---
        people_path = get_state_path()
        if os.path.exists(people_path):
            try:
                with open(people_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                
                if "year" in state:
                    self.year_var.set(str(state["year"]))
                if "month" in state:
                    self.month_var.set(str(state["month"]))
                if "extra" in state:
                    self.extra_var.set(state["extra"])
                
                if "tabs" in state:
                    for key in TAB_KEYS:
                        if key in state["tabs"]:
                            self.tabs[key].set_tab_state(state["tabs"][key])
                
                if "active_tab" in state and state["active_tab"] in TAB_KEYS:
                    self.nb.select(TAB_KEYS.index(state["active_tab"]))
            except Exception:
                pass
        
        # --- Φόρτωση προγραμμάτων (schedule) ---
        schedule_path = get_schedule_path()
        if os.path.exists(schedule_path):
            try:
                with open(schedule_path, "r", encoding="utf-8") as f:
                    sched_state = json.load(f)
                
                if "tabs" in sched_state:
                    for key in TAB_KEYS:
                        if key in sched_state["tabs"]:
                            # Φόρτωσε μόνο το schedule, χωρίς να πειράξεις τα people inputs
                            sched_data = sched_state["tabs"][key]
                            tab = self.tabs[key]
                            if "saved_schedule" in sched_data and sched_data["saved_schedule"]:
                                tab.current_schedule = {int(k): v for k, v in sched_data["saved_schedule"].items()}
                                tab.current_ranks = sched_data.get("saved_ranks", {})
                                tab.saved_schedule_locked = True
                                saved_text = sched_data.get("saved_stats_text", "")
                                if saved_text:
                                    try:
                                        tab.stats.config(state="normal")
                                        tab.stats.delete("1.0", "end")
                                        tab.stats.insert("end", saved_text)
                                        tab.stats.config(state="disabled")
                                        tab._refresh_save_button()
                                    except Exception:
                                        tab._refresh_save_button()
            except Exception:
                return
    
    # History Management Methods
    def on_edit_history(self):
        """Open comprehensive history viewer/editor dialog."""
        HistoryViewerEditorDialog(self)
    
    def on_reload_history(self):
        """Reload history from JSON file."""
        try:
            history = load_history()
            messagebox.showinfo("Επιτυχία", "Το ιστορικό φορτώθηκε από το αρχείο!")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία φόρτωσης:\n{str(e)}")
    
    def on_open_history_file(self):
        """Open history JSON file in default editor."""
        import subprocess
        import platform
        
        if not os.path.exists(HISTORY_FILE):
            # Create empty history file
            save_history({})
        
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', HISTORY_FILE))
            elif platform.system() == 'Windows':
                os.startfile(HISTORY_FILE)
            else:  # Linux
                subprocess.call(('xdg-open', HISTORY_FILE))
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Δεν μπόρεσε να ανοίξει το αρχείο:\n{str(e)}")
    
    def on_clear_history(self):
        """Clear all history after confirmation."""
        if messagebox.askyesno("Επιβεβαίωση", "Σίγουρα θέλεις να διαγράψεις ΟΛΟ το ιστορικό;"):
            save_history({})
            messagebox.showinfo("Επιτυχία", "Το ιστορικό διαγράφηκε!")
    
    def on_close(self):
        self.save_state()
        self.destroy()


# -----------------------------
# History Viewer + Editor Dialog (TABBED BY MONTH)
# -----------------------------
class HistoryViewerEditorDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Ιστορικό - Προβολή & Επεξεργασία")
        self.geometry("900x750")

        actions_frame = ttk.Frame(self, padding=(10, 10, 10, 0))
        actions_frame.pack(fill="x")

        ttk.Button(
            actions_frame,
            text="Ανανέωση από αρχείο",
            command=self._reload_and_refresh,
        ).pack(side="left", padx=5)

        ttk.Button(
            actions_frame,
            text="📂 Άνοιγμα αρχείου JSON",
            command=self.parent.on_open_history_file,
        ).pack(side="left", padx=5)

        ttk.Button(
            actions_frame,
            text="Καθαρισμός Ιστορικού",
            command=self._clear_and_refresh,
        ).pack(side="left", padx=5)
        
        # Top: Year selection
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill="x")
        
        ttk.Label(top_frame, text="Έτος:").pack(side="left", padx=5)
        self.year_var = tk.StringVar(value="2026")
        ttk.Entry(top_frame, textvariable=self.year_var, width=8).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Φόρτωση Έτους", command=self.load_year).pack(side="left", padx=5)
        
        # Create Notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Month tabs (13 tabs: ΤΟΤΑΛ + 12 μήνες)
        self.month_frames = {}
        month_names = ["ΤΟΤΑΛ ΕΤΟΥΣ"] + [GREEK_MONTHS_GEN[i].capitalize() for i in range(1, 13)]
        
        for i, month_name in enumerate(month_names):
            month_key = 0 if i == 0 else i
            
            # Create frame for this month
            month_frame = ttk.Frame(self.notebook)
            self.notebook.add(month_frame, text=month_name)
            
            # Stats label
            stats_label = ttk.Label(month_frame, text="", foreground="blue", font=('', 10, 'bold'))
            stats_label.pack(fill="x", padx=10, pady=5)
            
            # Container for table
            table_container = ttk.Frame(month_frame)
            table_container.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Headers (με monospace font για τέλεια ευθυγράμμιση)
            headers_frame = ttk.Frame(table_container)
            headers_frame.pack(fill="x")
            
            header_font = ('Courier', 9, 'bold')  # Monospace font!
            ttk.Label(headers_frame, text="Όνομα", width=20, font=header_font, anchor="w").grid(row=0, column=0, padx=2)
            ttk.Label(headers_frame, text="Καθημερινές", width=15, font=header_font, anchor="center").grid(row=0, column=1, padx=2)
            ttk.Label(headers_frame, text="Παρασκευές", width=15, font=header_font, anchor="center").grid(row=0, column=2, padx=2)
            ttk.Label(headers_frame, text="Αργίες", width=15, font=header_font, anchor="center").grid(row=0, column=3, padx=2)
            ttk.Label(headers_frame, text="TOTAL", width=10, font=header_font, foreground="darkgreen", anchor="center").grid(row=0, column=4, padx=2)
            
            # Scrollable table
            canvas = tk.Canvas(table_container, height=500)
            scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Store references
            self.month_frames[month_key] = {
                "frame": month_frame,
                "stats_label": stats_label,
                "scrollable_frame": scrollable_frame,
                "rows": []
            }
        
        # Bottom: Buttons
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="Αποθήκευση Όλων", command=self.save_all_data).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Κλείσιμο", command=self.destroy).pack(side="right", padx=5)
        
        self.load_year()
    
    def _reload_and_refresh(self):
        self.parent.on_reload_history()
        self.load_year()

    def _clear_and_refresh(self):
        self.parent.on_clear_history()
        self.load_year()

    def load_year(self):
        """Load all months for the selected year."""
        year = self.year_var.get()
        history = load_history()
        
        if year not in history:
            # Empty year
            for month_key, month_data in self.month_frames.items():
                self.clear_month(month_key)
                if month_key == 0:
                    month_data["stats_label"].config(text=f"ΤΟΤΑΛ ΕΤΟΥΣ {year}: Κενό")
                else:
                    month_name = GREEK_MONTHS_GEN[month_key].capitalize()
                    month_data["stats_label"].config(text=f"{month_name} {year}: Κενό")
            return
        
        year_data = history[year]
        
        # Load ΤΟΤΑΛ (month_key=0)
        self.load_total_year(year_data, year)
        
        # Load each month (month_key=1-12)
        for month_key in range(1, 13):
            self.load_single_month(year_data, year, month_key)
    
    def clear_month(self, month_key):
        """Clear all rows from a month."""
        month_data = self.month_frames[month_key]
        for row_frame, _, _, _, _ in month_data["rows"]:
            row_frame.destroy()
        month_data["rows"] = []
    
    def load_total_year(self, year_data, year):
        """Load TOTAL year view (month_key=0)."""
        month_data = self.month_frames[0]
        self.clear_month(0)
        
        # Aggregate all months
        totals = {}
        for month_str in year_data.keys():
            if not month_str.isdigit():
                continue
            
            for person, data in year_data[month_str].items():
                if person.startswith("_"):  # παράλειψε internal keys όπως _saved_tabs
                    continue
                if person not in totals:
                    totals[person] = {
                        "weekday": 0,
                        "friday": 0,
                        "holiday": 0,
                        "rank": data.get("rank", "")  # Store rank from first occurrence
                    }
                
                totals[person]["weekday"] += data.get("weekday", 0)
                totals[person]["friday"] += data.get("friday", 0)
                totals[person]["holiday"] += data.get("holiday", 0)
        
        # Group by rank
        officers = []
        others = []
        
        for person, data in totals.items():
            rank = data.get("rank", "")
            # Check if rank contains officer title
            if any(suffix in rank.upper() for suffix in ["ΛΓΟΣ", "ΥΠΛΓΟΣ", "ΑΝΘΛΓΟΣ"]):
                officers.append((person, data))
            else:
                others.append((person, data))
        
        month_data["stats_label"].config(
            text=f"ΤΟΤΑΛ ΕΤΟΥΣ {year}: {len(totals)} άτομα (Αξιωματικοί: {len(officers)}, Λοιποί: {len(others)})"
        )
        
        # Display Officers
        if officers:
            sep_frame = ttk.Frame(month_data["scrollable_frame"])
            sep_frame.pack(fill="x", pady=5)
            ttk.Label(sep_frame, text="▼ ΑΞΙΩΜΑΤΙΚΟΙ (ΛΓΟΣ, ΥΠΛΓΟΣ, ΑΝΘΛΓΟΣ) ▼", 
                     font=('', 10, 'bold'), foreground="darkblue").pack()
            
            for person, data in sorted(officers):
                self.add_row_to_month(0, person, data["weekday"], data["friday"], data["holiday"], editable=False)
        
        # Display Others
        if others:
            sep_frame = ttk.Frame(month_data["scrollable_frame"])
            sep_frame.pack(fill="x", pady=5)
            ttk.Label(sep_frame, text="▼ ΛΟΙΠΟΙ ▼", 
                     font=('', 10, 'bold'), foreground="darkgreen").pack()
            
            for person, data in sorted(others):
                self.add_row_to_month(0, person, data["weekday"], data["friday"], data["holiday"], editable=False)
    
    def load_single_month(self, year_data, year, month_key):
        """Load single month view."""
        month_data = self.month_frames[month_key]
        self.clear_month(month_key)
        
        month_str = str(month_key)
        month_name = GREEK_MONTHS_GEN[month_key].capitalize()
        
        if month_str not in year_data:
            month_data["stats_label"].config(text=f"{month_name} {year}: Κενό")
            return
        
        people_data = year_data[month_str]
        
        # Group people by rank
        officers = []
        others = []
        
        for person, data in people_data.items():
            if person.startswith("_"):  # παράλειψε internal keys όπως _saved_tabs
                continue
            rank = data.get("rank", "")
            # Check if rank contains officer title
            if any(suffix in rank.upper() for suffix in ["ΛΓΟΣ", "ΥΠΛΓΟΣ", "ΑΝΘΛΓΟΣ"]):
                officers.append((person, data))
            else:
                others.append((person, data))
        
        month_data["stats_label"].config(
            text=f"{month_name} {year}: {len(officers)+len(others)} άτομα (Αξ: {len(officers)}, Λοιποί: {len(others)})"
        )
        
        # Display Officers
        if officers:
            sep_frame = ttk.Frame(month_data["scrollable_frame"])
            sep_frame.pack(fill="x", pady=5)
            ttk.Label(sep_frame, text="▼ ΑΞΙΩΜΑΤΙΚΟΙ ▼", 
                     font=('', 9, 'bold'), foreground="darkblue").pack()
            
            for person, data in sorted(officers):
                self.add_row_to_month(month_key, person, data.get("weekday", 0), data.get("friday", 0), data.get("holiday", 0), editable=True)
        
        # Display Others
        if others:
            sep_frame = ttk.Frame(month_data["scrollable_frame"])
            sep_frame.pack(fill="x", pady=5)
            ttk.Label(sep_frame, text="▼ ΛΟΙΠΟΙ ▼", 
                     font=('', 9, 'bold'), foreground="darkgreen").pack()
            
            for person, data in sorted(others):
                self.add_row_to_month(month_key, person, data.get("weekday", 0), data.get("friday", 0), data.get("holiday", 0), editable=True)
    
    def add_row_to_month(self, month_key, name="", weekday=0, friday=0, holiday=0, editable=True):
        """Add a row to specific month."""
        month_data = self.month_frames[month_key]
        
        row_frame = ttk.Frame(month_data["scrollable_frame"])
        row_frame.pack(fill="x", pady=1)
        
        name_var = tk.StringVar(value=name)
        weekday_var = tk.StringVar(value=str(weekday))
        friday_var = tk.StringVar(value=str(friday))
        holiday_var = tk.StringVar(value=str(holiday))
        
        # Monospace font για τέλεια ευθυγράμμιση!
        data_font = ('Courier', 9)
        
        # Name
        if editable:
            tk.Entry(row_frame, textvariable=name_var, width=20, font=data_font).grid(row=0, column=0, padx=2)
        else:
            ttk.Label(row_frame, text=name, width=20, font=data_font, anchor="w").grid(row=0, column=0, padx=2)
        
        # Weekday (centered με monospace)
        if editable:
            tk.Entry(row_frame, textvariable=weekday_var, width=15, justify="center", font=data_font).grid(row=0, column=1, padx=2)
        else:
            ttk.Label(row_frame, text=str(weekday), width=15, font=data_font, anchor="center").grid(row=0, column=1, padx=2)
        
        # Friday (centered με monospace)
        if editable:
            tk.Entry(row_frame, textvariable=friday_var, width=15, justify="center", font=data_font).grid(row=0, column=2, padx=2)
        else:
            ttk.Label(row_frame, text=str(friday), width=15, font=data_font, anchor="center").grid(row=0, column=2, padx=2)
        
        # Holiday (centered με monospace)
        if editable:
            tk.Entry(row_frame, textvariable=holiday_var, width=15, justify="center", font=data_font).grid(row=0, column=3, padx=2)
        else:
            ttk.Label(row_frame, text=str(holiday), width=15, font=data_font, anchor="center").grid(row=0, column=3, padx=2)
        
        # Total (always read-only, centered με monospace)
        total = weekday + friday + holiday
        ttk.Label(row_frame, text=str(total), width=10, foreground="darkgreen", 
                 font=('Courier', 9, 'bold'), anchor="center").grid(row=0, column=4, padx=2)
        
        if editable:
            month_data["rows"].append((row_frame, name_var, weekday_var, friday_var, holiday_var))
    
    def save_all_data(self):
        """Save all modified months."""
        history = load_history()
        year = self.year_var.get()
        
        if year not in history:
            history[year] = {}
        
        # Save each month (skip TOTAL which is month_key=0)
        for month_key in range(1, 13):
            month_data = self.month_frames[month_key]
            month_str = str(month_key)
            
            if month_str not in history[year]:
                history[year][month_str] = {}
            
            # Clear and rebuild
            history[year][month_str] = {}
            
            for _, name_var, weekday_var, friday_var, holiday_var in month_data["rows"]:
                name = name_var.get().strip()
                if not name:
                    continue
                
                try:
                    weekday = int(weekday_var.get())
                    friday = int(friday_var.get())
                    holiday = int(holiday_var.get())
                    
                    if weekday > 0 or friday > 0 or holiday > 0:
                        history[year][month_str][name] = {
                            "weekday": weekday,
                            "friday": friday,
                            "holiday": holiday,
                        }
                except ValueError:
                    messagebox.showerror("Σφάλμα", f"Μη έγκυρος αριθμός για {name}")
                    return
        
        save_history(history)
        messagebox.showinfo("Επιτυχία", f"Όλα τα δεδομένα αποθηκεύτηκαν!")

