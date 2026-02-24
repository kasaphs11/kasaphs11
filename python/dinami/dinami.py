import pandas as pd
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime

# >>> Άλλαξε εδώ αν οι στήλες στο Excel έχουν άλλα ονόματα
START_COL = "ΗΜ/ΝΙΑ ΕΝΑΡΞΗΣ"
END_COL   = "ΗΜ/ΝΙΑ ΛΗΞΗΣ"

df = None

def load_file():
    global df
    path = filedialog.askopenfilename(filetypes=[("Excel files","*.xlsx *.xls")])
    if not path:
        return
    try:
        df = pd.read_excel(path)

        # πάρε τα ονόματα στηλών από GUI (fallback στα defaults)
        start_col = startcol_entry.get().strip() or START_COL
        end_col   = endcol_entry.get().strip() or END_COL

        # έλεγχος ότι υπάρχουν στο Excel
        missing = [c for c in (start_col, end_col) if c not in df.columns]
        if missing:
            messagebox.showerror(
                "Σφάλμα",
                "Δεν βρέθηκαν στο Excel οι στήλες:\n- " + "\n- ".join(missing)
            )
            df = None
            return

        # σε datetime (δέχεται dd/mm/yyyy)
        df[start_col] = pd.to_datetime(df[start_col], dayfirst=True, errors="coerce")
        df[end_col]   = pd.to_datetime(df[end_col],   dayfirst=True, errors="coerce")

        messagebox.showinfo("OK", "Το αρχείο φορτώθηκε.")
    except Exception as e:
        messagebox.showerror("Σφάλμα", f"Αποτυχία φόρτωσης:\n{e}")


def parse_int(entry, default=0, label=""):
    txt = entry.get().strip()
    if txt == "":
        return default
    try:
        return int(txt)
    except ValueError:
        messagebox.showerror("Σφάλμα", f"Το πεδίο «{label}» πρέπει να είναι ακέραιος αριθμός.")
        raise

def count_per_day():
    if df is None:
        messagebox.showerror("Σφάλμα", "Φόρτωσε πρώτα Excel.")
        return
    try:
        start = datetime.strptime(start_entry.get().strip(), "%d/%m/%Y")
        end   = datetime.strptime(end_entry.get().strip(),   "%d/%m/%Y")
    except:
        messagebox.showerror("Σφάλμα", "Δώσε ημερομηνίες σε μορφή dd/mm/yyyy.")
        return
    if end < start:
        messagebox.showerror("Σφάλμα", "Η ημερομηνία λήξης είναι πριν την αρχή.")
        return

    try:
        dynami  = parse_int(dynami_entry, 0, "Δύναμη")
        apontes = parse_int(apontes_entry, 0, "Απόντες")
    except:
        return  # ήδη εμφανίστηκε μήνυμα λάθους

    # όλες οι μέρες του διαστήματος
    days = pd.date_range(start, end, freq="D")

    # Υπολογισμοί ανά ημέρα
    leave_counts = []
    present_counts = []
    start_col = startcol_entry.get().strip() or START_COL
    end_col   = endcol_entry.get().strip() or END_COL

    if start_col not in df.columns or end_col not in df.columns:
        messagebox.showerror("Σφάλμα", "Οι στήλες που έβαλες δεν υπάρχουν στο Excel. Φόρτωσε ξανά το αρχείο.")
        return


    for d in days:
        # Αδειούχοι: πόσες άδειες τέμνουν τη μέρα d (start<=d<=end)
        mask = (df[start_col] <= d) & (df[end_col] >= d)
        adeioychoi = int(mask.sum())
        leave_counts.append(adeioychoi)

        # Παρόντες = Δύναμη - Απόντες - Αδειούχοι
        parontes = dynami - apontes - adeioychoi
        present_counts.append(parontes)

    # Καθαρισμός λιστών και γέμισμα με νέα δεδομένα
    for i in tree_adeioychoi.get_children():
        tree_adeioychoi.delete(i)
    for i in tree_parontes.get_children():
        tree_parontes.delete(i)

    for d, leave_c, pres_c in zip(days, leave_counts, present_counts):
        date_str = d.strftime("%d/%m/%Y")
        tree_adeioychoi.insert("", "end", values=(date_str, leave_c))
        tree_parontes.insert("", "end", values=(date_str, pres_c))

# --- GUI ---
root = tk.Tk()
root.title("Μετρητής Αδειούχων & Παρόντων ανά Ημέρα (Excel)")

frm = ttk.Frame(root, padding=10)
frm.pack(fill="both", expand=True)

# επάνω μπάρα
top = ttk.Frame(frm)
top.pack(fill="x", pady=(0,8))
ttk.Button(top, text="Φόρτωσε Excel", command=load_file).pack(side="left")

# γραμμή ημερομηνιών
mid = ttk.Frame(frm)
mid.pack(fill="x", pady=(0,8))
ttk.Label(mid, text="Από (dd/mm/yyyy):").pack(side="left")
start_entry = ttk.Entry(mid, width=12)
start_entry.pack(side="left", padx=(5,15))
ttk.Label(mid, text="Έως (dd/mm/yyyy):").pack(side="left")
end_entry = ttk.Entry(mid, width=12)
end_entry.pack(side="left", padx=(5,15))

# γραμμή με Δύναμη & Απόντες
mid2 = ttk.Frame(frm)
mid2.pack(fill="x", pady=(0,8))
ttk.Label(mid2, text="Δύναμη:").pack(side="left")
dynami_entry = ttk.Entry(mid2, width=8)
dynami_entry.insert(0, "0")
dynami_entry.pack(side="left", padx=(5,15))
ttk.Label(mid2, text="Απόντες:").pack(side="left")
apontes_entry = ttk.Entry(mid2, width=8)
apontes_entry.insert(0, "0")
apontes_entry.pack(side="left", padx=5)

# κουμπί υπολογισμού
buttons = ttk.Frame(frm)
buttons.pack(fill="x", pady=(0,8))
ttk.Button(buttons, text="Υπολόγισε", command=count_per_day).pack(side="left", padx=10)

# γραμμή με ονόματα στηλών (Start/End) - NEW
mid_cols = ttk.Frame(frm)
mid_cols.pack(fill="x", pady=(0,8))

ttk.Label(mid_cols, text="Στήλη Ημερομηνίας Έναρξης:").pack(side="left")
startcol_entry = ttk.Entry(mid_cols, width=25)
startcol_entry.insert(0, START_COL)   # default
startcol_entry.pack(side="left", padx=(5,15))

ttk.Label(mid_cols, text="Στήλη Ημερομηνίας Λήξης:").pack(side="left")
endcol_entry = ttk.Entry(mid_cols, width=25)
endcol_entry.insert(0, END_COL)       # default
endcol_entry.pack(side="left", padx=(5,0))


# λίστα Αδειούχων
lbl1 = ttk.Label(frm, text="Ανά ημέρα: Πλήθος αδειούχων")
lbl1.pack(anchor="w")
tree_adeioychoi = ttk.Treeview(frm, columns=("date","count"), show="headings", height=8)
tree_adeioychoi.heading("date", text="Ημερομηνία")
tree_adeioychoi.heading("count", text="Αδειούχοι")
tree_adeioychoi.column("date", width=120, anchor="center")
tree_adeioychoi.column("count", width=160, anchor="center")
tree_adeioychoi.pack(fill="both", expand=True, pady=(0,10))

# λίστα Παρόντων
lbl2 = ttk.Label(frm, text="Ανά ημέρα: Παρόντες (Δύναμη - Απόντες - Αδειούχοι)")
lbl2.pack(anchor="w")
tree_parontes = ttk.Treeview(frm, columns=("date","present"), show="headings", height=8)
tree_parontes.heading("date", text="Ημερομηνία")
tree_parontes.heading("present", text="Παρόντες")
tree_parontes.column("date", width=120, anchor="center")
tree_parontes.column("present", width=160, anchor="center")
tree_parontes.pack(fill="both", expand=True)

root.mainloop()
