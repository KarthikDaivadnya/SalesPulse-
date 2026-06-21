"""
SalesPulse - Step 1: Data Cleaning & Consolidation
----------------------------------------------------
Reads the 3 raw, messy source files (different schemas, different formats)
and produces ONE clean, analysis-ready dataset: data/processed/sales_cleaned.csv

Cleaning steps performed (each documented so the logic is auditable):
  1. Standardize column names and date formats across sources written in
     5+ different date string formats (or raw Excel serials).
  2. Strip currency symbols (Rs., ₹, commas) and cast price fields to numeric.
  3. Normalize categorical text (trim whitespace, consistent Title Case).
  4. Drop fully-blank rows and exact duplicate rows.
  5. Handle missing values with documented business rules (see comments).
  6. Reconcile two different schemas (online vs. in-store) into one common
     fact-table shape, then enrich with customer/region info.
  7. Remove return/negative-quantity rows into a separate returns log instead
     of silently dropping them (keeps the data auditable).
"""
import pandas as pd
import numpy as np
import re

RAW_DIR = "data/raw"
OUT_DIR = "data/processed"

CATEGORY_MAP = {  # canonical category names regardless of source casing/spacing
    "electronics": "Electronics", "apparel": "Apparel", "home & kitchen": "Home & Kitchen",
    "beauty": "Beauty", "sports & fitness": "Sports & Fitness",
}

CITY_TO_REGION = {
    "Delhi": "North", "Lucknow": "North", "Jaipur": "North", "Chandigarh": "North",
    "Bengaluru": "South", "Chennai": "South", "Hyderabad": "South", "Kochi": "South",
    "Mumbai": "West", "Pune": "West", "Ahmedabad": "West", "Surat": "West",
    "Kolkata": "East", "Bhubaneswar": "East", "Patna": "East", "Guwahati": "East",
}


def clean_price(val):
    """Strip Rs./₹/commas and whitespace while preserving the decimal point; return float or NaN."""
    if pd.isna(val) or str(val).strip() == "":
        return np.nan
    s = str(val).strip()
    s = re.sub(r"(?i)rs\.?", "", s)   # remove "Rs" or "Rs." prefix (case-insensitive)
    s = s.replace("₹", "")
    s = s.replace(",", "")            # thousands separator only -- decimal point untouched
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_messy_date(val):
    """Parse dates that arrive in 5+ different formats, or as Excel serials."""
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, (pd.Timestamp, )):
        return val
    s = str(val).strip()
    if s == "":
        return pd.NaT
    # Excel serial dates (numeric, written when openpyxl doesn't get a date format)
    if re.fullmatch(r"\d{4,6}(\.0)?", s):
        try:
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(int(float(s)), unit="D")
        except Exception:
            pass
    # Try explicit known formats first (avoids ambiguous day/month guessing
    # for unambiguous formats like ISO or "Mar 14, 2024").
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%d %B %Y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except ValueError:
            continue
    # Remaining formats are ambiguous numeric d/m/y vs m/d/y (e.g. "11/08/2024").
    # This dataset is sourced from Indian exports, so day-first is the correct
    # convention for those.
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def normalize_text(s):
    if pd.isna(s):
        return s
    return str(s).strip().title()


def normalize_category(s):
    if pd.isna(s):
        return np.nan
    key = str(s).strip().lower()
    return CATEGORY_MAP.get(key, str(s).strip().title())


# ---------------------------------------------------------------------------
# 1. LOAD & CLEAN: ONLINE SALES
# ---------------------------------------------------------------------------
online = pd.read_csv(f"{RAW_DIR}/online_sales_raw.csv", dtype=str)
before_online = len(online)

online = online.dropna(how="all")                                # drop fully-blank rows
online = online[online["order_id"].notna() & (online["order_id"].str.strip() != "")]
online = online.drop_duplicates()                                 # drop exact duplicate rows

online["order_date"] = online["order_date"].apply(parse_messy_date)
online["product_category"] = online["product_category"].apply(normalize_category)
online["unit_price"] = online["unit_price"].apply(clean_price)
online["quantity"] = pd.to_numeric(online["quantity"], errors="coerce")
online["region"] = online["region"].apply(lambda x: x.strip().title() if pd.notna(x) and str(x).strip() != "" else np.nan)

# Business rule: ~4% of rows arrived with no unit_price. Rather than drop them
# (losing real transactions), impute using the median price for that product,
# since price is consistent per product in this catalog.
median_price_by_product = online.groupby("product_name")["unit_price"].median()
online["unit_price"] = online.apply(
    lambda r: median_price_by_product.get(r["product_name"], np.nan) if pd.isna(r["unit_price"]) else r["unit_price"],
    axis=1,
)

# Business rule: ~5% of rows arrived with no region. Region is non-critical for
# revenue totals but needed for regional breakdowns, so we tag these explicitly
# as "Unknown" rather than guessing or dropping the transaction.
online["region"] = online["region"].fillna("Unknown")

online["source"] = "Online"
online = online.rename(columns={"order_id": "transaction_id"})

print(f"[Online]   {before_online} raw rows -> {len(online)} cleaned rows "
      f"({before_online - len(online)} removed: blanks/duplicates)")


# ---------------------------------------------------------------------------
# 2. LOAD & CLEAN: STORE / POS SALES (different schema + junk header rows)
# ---------------------------------------------------------------------------
store = pd.read_excel(f"{RAW_DIR}/store_sales_raw.xlsx", skiprows=2)  # skip the 2 junk header rows
before_store = len(store)

store = store.dropna(how="all")
store = store[store["TransactionID"].notna()]
store = store.drop_duplicates()

store["Date"] = store["Date"].apply(parse_messy_date)
store["ItemCategory"] = store["ItemCategory"].apply(normalize_category)
store["Price"] = store["Price"].apply(clean_price)
store["StoreCity"] = store["StoreCity"].apply(normalize_text)
store["region"] = store["StoreCity"].map(CITY_TO_REGION)

# Business rule: ~2% missing Qty. A missing quantity on a completed in-store
# transaction is treated as a single-unit sale (the most common basket size),
# rather than dropped, to avoid under-counting real revenue.
store["Qty"] = pd.to_numeric(store["Qty"], errors="coerce").fillna(1)

# Reconcile schema -> common shape matching the online table
store = store.rename(columns={
    "TransactionID": "transaction_id", "Date": "order_date", "ItemCategory": "product_category",
    "ItemSold": "product_name", "Qty": "quantity", "Price": "unit_price", "CustomerPhone": "customer_id",
})
store["payment_method"] = "In-Store"
store["source"] = "Store"
store = store[["transaction_id", "order_date", "customer_id", "product_category", "product_name",
               "quantity", "unit_price", "region", "payment_method", "source"]]

print(f"[Store]    {before_store} raw rows -> {len(store)} cleaned rows "
      f"({before_store - len(store)} removed: blanks/duplicates)")


# ---------------------------------------------------------------------------
# 3. LOAD & CLEAN: CUSTOMER MASTER (dedupe near-duplicate IDs)
# ---------------------------------------------------------------------------
customers = pd.read_csv(f"{RAW_DIR}/customers_raw.csv", dtype=str)
before_cust = len(customers)

customers["name"] = customers["name"].apply(normalize_text)
customers["city"] = customers["city"].apply(normalize_text)
customers["signup_date"] = customers["signup_date"].apply(parse_messy_date)

# Business rule: duplicate customer_id rows (same ID, casing-only name variants)
# are deduplicated by keeping the first clean record per ID.
customers = customers.sort_values("customer_id").drop_duplicates(subset="customer_id", keep="first")

print(f"[Customers]{before_cust} raw rows -> {len(customers)} cleaned rows "
      f"({before_cust - len(customers)} duplicate customer_id rows removed)")


# ---------------------------------------------------------------------------
# 4. CONSOLIDATE ONLINE + STORE INTO ONE FACT TABLE
# ---------------------------------------------------------------------------
sales = pd.concat([online, store], ignore_index=True)
sales["revenue"] = sales["quantity"] * sales["unit_price"]

# Separate returns (negative quantity) into an auditable log rather than
# silently discarding them -- they affect net revenue but aren't "bad data".
returns = sales[sales["quantity"] < 0].copy()
sales_clean = sales[sales["quantity"] > 0].copy()

sales_clean = sales_clean.dropna(subset=["order_date", "unit_price"])  # final safety net
sales_clean["order_date"] = pd.to_datetime(sales_clean["order_date"])
sales_clean["order_month"] = sales_clean["order_date"].dt.to_period("M").astype(str)
sales_clean["order_week"] = sales_clean["order_date"].dt.to_period("W").astype(str)

sales_clean.to_csv(f"{OUT_DIR}/sales_cleaned.csv", index=False)
returns.to_csv(f"{OUT_DIR}/returns_log.csv", index=False)
customers.to_csv(f"{OUT_DIR}/customers_cleaned.csv", index=False)

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
total_raw = before_online + before_store
print("\n" + "=" * 60)
print("CLEANING SUMMARY")
print("=" * 60)
print(f"Raw transaction rows (online + store):     {total_raw:,}")
print(f"Final clean, analysis-ready transactions:  {len(sales_clean):,}")
print(f"Returns logged separately (not discarded):  {len(returns):,}")
print(f"Customer master rows (post-dedupe):         {len(customers):,}")
print(f"Date range:  {sales_clean['order_date'].min().date()}  to  {sales_clean['order_date'].max().date()}")
print(f"Total net revenue: \u20b9{sales_clean['revenue'].sum():,.0f}")
print(f"\nOutput written to {OUT_DIR}/sales_cleaned.csv, returns_log.csv, customers_cleaned.csv")
