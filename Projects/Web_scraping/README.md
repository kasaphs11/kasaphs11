# BestPrice Price Automation – Pota Scraper

A production-ready Python automation tool that reads product names from Excel and automatically fetches prices from BestPrice.gr (Drinks category).

The script performs intelligent search, similarity validation, retry handling, and continuous Excel updating.

---

## 🚀 What This Project Does

The system:

1. Reads product names from an Excel file
2. Searches BestPrice.gr automatically using Playwright
3. Extracts:
   - Best price (€)
   - Product link
   - Product volume (ml)
4. Validates match similarity
5. Writes results back into Excel
6. Auto-saves progress
7. Handles timeouts and retries automatically

---

## 🧠 Smart Search Strategy

The scraper uses a 2-pass intelligent search:

### Pass 1 – Full Query
Uses normalized product name.

### Pass 2 – Short Query
If similarity is low or result not found, retries using first 2 words.

Similarity is calculated using token-based comparison.

If similarity is below threshold → marked as `LOW_SIM`.

---

## 📊 Excel Integration

### 📥 Input File

The input file (`ΤΙΜΕΣ.xlsx`) is an Excel spreadsheet containing product names of alcoholic beverages (e.g. whisky, vodka, rum, etc.).

The required column is:

- **Ονομασία Εμπορεύματος** → The product name to be searched.

Each row represents a product.

The script automatically reads all rows and processes only products that do not already have a price filled.

---
### 📤 Output File

The output file (`ΤΙΜΕΣ_ΕΛΛΑΔΑ_bestprice.xlsx`) is continuously updated in-place.

If the file already exists, the script resumes from it safely.

The system automatically creates (if missing) and updates the following columns:

| Column | Description |
|--------|-------------|
| **ΕΛΛΑΔΑ** | The detected best price (€) from BestPrice.gr |
| **GR_link** | Direct URL link to the matched product page on BestPrice |
| **Σημειώσεις** | Processing status, extracted product volume normalized to milliliters (e.g. 700ml, 1000ml), similarity score, and diagnostic notes |

---
### 📝 Notes Column Details

The **Σημειώσεις** column contains structured status messages such as:

- `OK` → Valid match with sufficient similarity
- `OK(short)` → Match found using short query fallback
- `LOW_SIM` → Price found but similarity below threshold
- `NONE` → No product match found
- `TIMEOUT` → Network timeout occurred
- `ERROR` → Unexpected error during processing

This allows manual review of uncertain matches.

---

### 🔄 Smart Processing Logic

- Rows that already contain a valid price are automatically skipped.
- The file is auto-saved every 50 processed products.
- If the script stops unexpectedly, it can safely resume.
### 🔗 Product Link (GR_link)

For every matched product, the script stores the **exact product page URL**.

This allows:

- Manual verification of price
- Quick access to the source listing
- Audit trail for data validation
- Easy re-checking if prices change


