# Ipiresies – Advanced Military Duty Scheduler

A powerful, constraint-based monthly duty scheduling system with GUI, designed for military unit service planning.

The system automatically generates fair and optimized monthly duty schedules while respecting:

- Leave periods
- Service caps (MAX limits)
- Personal day preferences
- Weekend & holiday balancing
- Rank-based fairness groups
- Cross-tab assignment conflicts
- Historical workload balancing

It uses a **Two-Phase Backtracking Solver with intelligent constraint relaxation and score balancing**.

---

## 🚀 Key Features

### 🔹 Intelligent Two-Phase Solver
The scheduler works in two phases:

1. **Holiday Assignment Phase**
   - Assigns weekends and official holidays first
   - Hardest constraint solved first
   - History-aware distribution

2. **Weekday Assignment Phase**
   - Balances remaining services
   - Uses scoring system for fairness
   - Backtracking with fail-fast pruning

---

### 🔹 Fairness & Balancing

The system ensures fairness using:

- Historical workload tracking (JSON persistence)
- Score-based balancing
- Rank-based grouping:
  - Officers (ranks ending in "ΛΓΟΣ")
  - Others
- Randomized tie-breaking to avoid deterministic bias

Scoring system:
- Weekday service → 1.0
- Friday → 1.0
- Holiday → 1.5

Goal:
> Minimize score spread between personnel.

---

### 🔹 Advanced Constraint Handling

The scheduler respects:

- Minimum gap between services
- Automatic MAX service calculation for constrained personnel
- Strict MAX caps (exact assignment if defined)
- Leave days (hard constraint)
- Preference days (soft constraint)
- Cross-tab collision prevention
- Special forbidden weekend patterns (e.g., Friday → Wednesday)

If no valid schedule exists:
- Progressive constraint relaxation
- GAP=1 fallback
- Multiple randomized attempts
- Detailed error diagnostics

---

## 🧠 Algorithmic Design

The core solver:

- Constraint-based backtracking
- Fail-fast pruning
- Feasibility checks per recursion level
- Per-person dynamic min-gap
- Recursive depth limiting
- Timeout protection
- Multi-attempt optimization with random seeds

This is NOT a naive random generator — it is a structured combinatorial solver.

---

## 🖥️ Graphical Interface (Tkinter)

The GUI allows:

- Adding personnel per tab
- Entering leave periods
- Setting MAX caps
- Defining personal preferences
- Adding extra holidays
- Selecting month/year
- Generating schedules
- Exporting Word documents
- Saving history automatically

Tabs supported:
- AYDM
- BAYDM
- FKX
- PYLI

All tabs are solved sequentially to prevent assigning the same person on the same day across tabs.

---

## 📊 Historical Tracking

The system stores monthly statistics in:
