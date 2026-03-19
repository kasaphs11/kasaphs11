# constants.py
# Σταθερές, βαθμοί, tab keys και τίτλοι

MIN_GAP_STRICT = 2
W_SCORE = 1.0    # Καθημερινή (Δευ-Πεμ)
F_SCORE = 1.25   # Παρασκευή
H_SCORE = 1.5    # Σαββατοκύριακο / Αργία

# Debug / tuning
DEBUG = False
SOLVER_MAX_TIME = 25.0            # seconds
SOLVER_MAX_RECURSION_MULT = 2     # recursion depth multiplier for weekdays phase

TAB_KEYS = ["AYDM", "BAYDM", "FKX", "PYLI"]
TAB_TITLES = {
    "AYDM": "ΑΥΔΜ",
    "BAYDM": "ΒΑΥΔΜ",
    "FKX": "ΦΚΧ",
    "PYLI": "ΠΥΛΗ",
}

GREEK_MONTHS_GEN = {
    1: "ΙΑΝΟΥΑΡΙΟΥ",
    2: "ΦΕΒΡΟΥΑΡΙΟΥ",
    3: "ΜΑΡΤΙΟΥ",
    4: "ΑΠΡΙΛΙΟΥ",
    5: "ΜΑΪΟΥ",
    6: "ΙΟΥΝΙΟΥ",
    7: "ΙΟΥΛΙΟΥ",
    8: "ΑΥΓΟΥΣΤΟΥ",
    9: "ΣΕΠΤΕΜΒΡΙΟΥ",
    10: "ΟΚΤΩΒΡΙΟΥ",
    11: "ΝΟΕΜΒΡΙΟΥ",
    12: "ΔΕΚΕΜΒΡΙΟΥ",
}

GREEK_MONTH_ABBR = {
    1: "ΙΑΝ",
    2: "ΦΕΒ",
    3: "ΜΑΡ",
    4: "ΑΠΡ",
    5: "ΜΑΪ",
    6: "ΙΟΥΝ",
    7: "ΙΟΥΛ",
    8: "ΑΥΓ",
    9: "ΣΕΠ",
    10: "ΟΚΤ",
    11: "ΝΟΕ",
    12: "ΔΕΚ",
}
