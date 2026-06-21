# SalesPulse — Sales & Performance Analytics Dashboard

> **Stack:** Python · Pandas · SQL (SQLite) · Power BI · Excel (openpyxl) · HTML/JS · Chart.js

A complete, end-to-end data analytics project that walks the full analyst workflow — from raw, messy, multi-source data all the way to an interactive dashboard and automated reporting.

---

## The Problem

A business receives sales exports from two separate systems every week — an e-commerce platform (CSV) and an in-store POS system (Excel) — each with different column names, inconsistent date formats, messy currency strings, duplicate rows, and missing values. A data analyst's job is to turn that into something decision-makers can actually act on.

This project builds that entire pipeline from scratch.

---

## Project Structure

```
SalesPulse/
├── data/
│   ├── raw/                        # Messy multi-source input files
│   │   ├── online_sales_raw.csv    # E-commerce export (1,400+ rows, 5 date formats, missing values)
│   │   ├── store_sales_raw.xlsx    # POS export (2 junk header rows, Excel serial dates, different schema)
│   │   └── customers_raw.csv       # Customer master (near-duplicate IDs, inconsistent casing)
│   └── processed/
│       ├── sales_cleaned.csv       # 2,311-row consolidated fact table
│       ├── customers_cleaned.csv   # 420 deduplicated customer records
│       └── returns_log.csv         # 39 return rows separated out for audit
├── scripts/
│   ├── 0_generate_raw_data.py      # Generates the realistic messy raw files
│   ├── 1_clean_data.py             # Pandas cleaning & consolidation pipeline
│   ├── 2_load_to_sql.py            # Loads clean data into SQLite (sales_data.db)
│   ├── 3_generate_report.py        # Automated weekly/monthly Excel report generator
│   └── queries.sql                 # 10 SQL aggregation queries (revenue, region, customers)
├── dashboard/
│   ├── dashboard.html              # Interactive HTML dashboard (open in any browser)
│   ├── dashboard.js                # Filtering, KPI logic, Chart.js charts
│   └── _data_inline.js             # Sales data embedded for standalone/offline use
├── reports/
│   ├── Monthly_Sales_Report_*.xlsx # Auto-generated monthly summary
│   └── Weekly_Sales_Report_*.xlsx  # Auto-generated weekly summary
├── powerbi/
│   └── POWERBI_GUIDE.md            # Step-by-step guide + DAX measures to build in Power BI Desktop
├── sales_data.db                   # SQLite database (run queries.sql against this)
└── requirements.txt
```

---

## What Each Step Does

### Step 1 — Data Cleaning (`scripts/1_clean_data.py`)

The two raw sources arrive with completely different schemas and formats. This script:

- Parses **5 different date formats** (ISO, DD/MM/YYYY, "Jan 15, 2024", Excel serial numbers, etc.)
- Strips currency symbols (₹, Rs., commas) and casts price fields to `float64`
- Normalises all categorical text (Title Case, whitespace trimming)
- Drops 44 blank/exact-duplicate rows (29 online + 15 in-store export duplicates)
- Reconciles two different column schemas into one unified 13-column fact table
- Fills missing `unit_price` values with per-product median (business-justified imputation)
- Tags ~5% of rows with missing `region` as `"Unknown"` rather than silently dropping
- **Separates 39 return rows** into an audit log instead of deleting them
- Outputs: `sales_cleaned.csv` (2,311 rows), `customers_cleaned.csv` (420 rows), `returns_log.csv`

**Before → After:**
| Metric | Raw | Cleaned |
|---|---|---|
| Total rows (online + store) | 2,394 | 2,311 |
| Removed (blanks/dupes) | — | 83 |
| `unit_price` dtype | mixed str/float | `float64`, 0 NaN |
| Date formats | 5+ inconsistent | `datetime64`, 0 NaT |
| Category casing | inconsistent | normalised Title Case |

---

### Step 2 — SQL Analysis (`scripts/queries.sql`)

10 queries against `sales_data.db` (SQLite, fully portable):

| # | Query | Business Question |
|---|---|---|
| 1 | Monthly revenue trend | How is revenue trending month over month? |
| 2 | Revenue by region | Which regions contribute most — and at what order value? |
| 3 | Top 10 products | What should we stock more of? |
| 4 | Category performance | Where does margin concentrate? |
| 5 | Channel comparison | Online vs. store: which is bigger, which has higher AOV? |
| 6 | Repeat vs. one-time buyers | How healthy is our retention? |
| 7 | Revenue by customer segment | Which segment is most valuable? |
| 8 | Week-over-week trend | What did last week look like vs. the week before? |
| 9 | Payment method mix | What payment methods drive the most volume? |
| 10 | Returns impact by region | Where are returns concentrated? |

Run any query with:
```bash
sqlite3 sales_data.db < scripts/queries.sql
```

---

### Step 3 — Automated Reporting (`scripts/3_generate_report.py`)

Generates a formatted Excel report on demand — or on a schedule. Replaces the
manual "copy numbers into a template every week" workflow.

```bash
python scripts/3_generate_report.py --period monthly
python scripts/3_generate_report.py --period weekly
```

Each report includes:
- **4 KPI cards**: Total Revenue, Orders, Avg Order Value, % change vs. prior period
- Revenue by region, Revenue by category, Top 5 products tables
- A separate **Trend sheet** with a native Excel line chart (last 30 days of daily revenue)
- Auto-dated filename — safe to schedule via cron or Windows Task Scheduler

---

### Step 4 — Interactive Dashboard (`dashboard/dashboard.html`)

Open `dashboard/dashboard.html` in any modern browser — no server, no install.

Features:
- **4 live KPI cards** with month-over-month delta
- **Revenue trend line chart** — updates instantly with every filter change
- **Online vs. Store donut chart**
- **Region, Product, and Category breakdown tables**
- **4 dropdown filters** (Region / Category / Channel / Month) that cross-filter everything
- **Click any region row** to drill down into that region only (click again to toggle off)
- Reset button clears all filters in one click

---

### Step 5 — Power BI Dashboard

See [`powerbi/POWERBI_GUIDE.md`](powerbi/POWERBI_GUIDE.md) for a step-by-step walkthrough to rebuild this dashboard in Power BI Desktop using the same `sales_cleaned.csv`, including copy-paste DAX measures for all KPIs. Takes ~15–20 minutes.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate the raw messy source files (already included in data/raw/)
python scripts/0_generate_raw_data.py

# 3. Run the cleaning pipeline
python scripts/1_clean_data.py

# 4. Load into SQLite
python scripts/2_load_to_sql.py

# 5. Run SQL queries
sqlite3 sales_data.db < scripts/queries.sql

# 6. Generate reports
python scripts/3_generate_report.py --period monthly
python scripts/3_generate_report.py --period weekly

# 7. Open the dashboard
# Just double-click dashboard/dashboard.html in your file manager
```

---

## Dataset

The dataset is **synthetically generated** for this portfolio project (`scripts/0_generate_raw_data.py`). It simulates realistic Indian retail sales data across 18 months (Jan 2024 – Jun 2025), 4 regions, 5 product categories, 20 products, 420 customers, and two sales channels. The raw files are intentionally messy to demonstrate real data cleaning work.

---

## Key Learnings / Talking Points

- **Multi-source consolidation** across completely different schemas is harder than it looks — reconciling column names, date conventions, and currency formatting requires explicit, documented business logic, not just `pd.concat`.
- **Imputation decisions need justification**: filling missing prices with per-product median is defensible; filling missing region with the most common region would not be, so `"Unknown"` is the right choice there.
- **Returns should never be silently deleted** — separating them into `returns_log.csv` keeps the data auditable and the pipeline honest.
- **A single failed dependency shouldn't break unrelated UI** — the `safeRender()` wrapper in `dashboard.js` ensures chart failures never cascade and blank out the data tables.

---

*Built by [Karthik M Daivadnya](https://github.com/KarthikDaivadnya)*
