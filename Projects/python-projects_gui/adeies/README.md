# Report Adeies — Leave Report Generator (GUI)

Python GUI application that reads an Excel file with leave records and generates a filtered report per person.

It allows searching by **ΑΣΜ** or **Full Name** and creates a new Excel file with detailed leave analysis.

---

## 🚀 Features

- 📂 Load Excel file with personnel leave data
- 🔍 Search by:
  - ΑΣΜ (multiple values supported)
  - Full Name (Surname + Name)
- 🧮 Automatic calculation of:
  - Totals
  - Remaining leave balance (based on service duration)
- 📊 Generates structured Excel report with:
  - Separate blocks per person
  - Headers
  - Totals
  - Balance
  - Borders for readability
- 🖥️ Simple and user-friendly GUI

---

## 🖼️ Interface

The application provides a graphical interface for:

- Selecting the input Excel file
- Choosing search mode
- Entering ASMs or names
- Selecting service duration
- Exporting the final report

*(You can add screenshots here later)*

---

## 📁 Input Format

The input Excel file must contain columns such as:

- ΕΠΩΝΥΜΟ
- ΟΝΟΜΑ
- ΑΣΜ
- ΗΜ/ΝΙΑ ΕΝΑΡΞΗΣ
- ΗΜ/ΝΙΑ ΛΗΞΗΣ
- ΚΑ, ΤΑΠ, ΕΛΔΥΚ, ΤΙΜ, ΑΙΜ, ΑΓΡ, ΦΟΙΤ, ΑΝΑΡ, ΗΜΕΡΕΣ

Only supported columns are kept in the output.

---

## ⚙️ Installation

### 1️⃣ Install dependencies

```bash
pip install openpyxl
