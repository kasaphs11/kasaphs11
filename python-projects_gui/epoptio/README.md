# Epoptio — Leave Departures & Returns Report Generator (GUI)

Python GUI application that analyzes leave records from Excel and generates **daily reports of departures and returns** in a formatted Excel file.

It supports multiple dates or date ranges and produces a printable, structured report in Greek.

---

## 🚀 Features

- 📂 Load source Excel file with leave data
- 📅 Accept multiple dates or date ranges (e.g. `30/10/2025-02/11/2025`)
- 🔍 Automatic detection of:
  - Departures (start date + 1)
  - Returns (end date)
- 📊 Generates formatted Excel report with:
  - Daily sections
  - Separate tables for departures and returns
  - Automatic numbering
  - Borders and styling
- 🖨️ Print-friendly layout
- 🇬🇷 Greek date formatting (days & months)
- 🖥️ Simple and user-friendly GUI

---

## 🖼️ Interface

The application allows the user to:

- Select the source Excel file
- Enter dates or ranges
- Define column names
- Select output file name
- Generate reports with one click

*(Screenshots can be added here later)*

---

## 📁 Input File Format

The source Excel file must contain at least:

- Start date column (default: `ΗΜ/ΝΙΑ ΕΝΑΡΞΗΣ`)
- End date column (default: `ΗΜ/ΝΙΑ ΛΗΞΗΣ`)

And personnel data columns such as:

- ΕΠΩΝΥΜΟ
- ΟΝΟΜΑ
- ΛΟΧΟΣ
- ΤΟΠΟΣ ΜΕΤΑΒΑΣΗΣ

Column names can be customized in the interface.

Dates can be in Excel date format or text (`dd/mm/yyyy`).

---

## ⚙️ Installation

### 1️⃣ Install dependencies

```bash
pip install pandas openpyxl
