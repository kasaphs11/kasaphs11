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

Input file:
