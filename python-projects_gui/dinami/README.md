# Dinami — Daily Leave & Presence Counter (GUI)

Python GUI application that analyzes personnel leave data from Excel and calculates the number of **leave holders** and **present personnel** per day.

It provides a simple interface for selecting a date range and generating daily statistics automatically.

---

## 🚀 Features

- 📂 Load Excel file with leave records
- 📅 Select custom date range
- 🔢 Enter total personnel strength and absences
- ⚙️ Supports custom column names for start/end dates
- 📊 Calculates per day:
  - Number of personnel on leave
  - Number of personnel present
- 🖥️ Displays results in organized tables (TreeView)
- ❗ Built-in validation and error handling

---

## 🖼️ Interface

The application provides a graphical interface for:

- Loading Excel files
- Selecting date ranges
- Defining personnel strength and absences
- Setting custom column names
- Viewing daily results

*(Screenshots can be added here later)*

---

## 📁 Input Format

The Excel file must contain at least the following columns:

- ΗΜ/ΝΙΑ ΕΝΑΡΞΗΣ (Start Date)
- ΗΜ/ΝΙΑ ΛΗΞΗΣ (End Date)

Custom column names can be defined in the interface.

Dates must be in `dd/mm/yyyy` format.

---

## ⚙️ Installation

### 1️⃣ Install dependencies

```bash
pip install pandas
