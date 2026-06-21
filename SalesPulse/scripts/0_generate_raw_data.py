"""
Generates the 3 messy raw source files that simulate what a fresher Data Analyst
would actually receive: an e-commerce export, a POS/store export, and a customer
master list -- each with realistic real-world messiness (inconsistent date formats,
mixed casing, currency symbols, missing values, duplicates, stray whitespace).
This script is for dataset generation only; it is NOT part of the analysis pipeline.
"""
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

CITIES = {
    "North": ["Delhi", "Lucknow", "Jaipur", "Chandigarh"],
    "South": ["Bengaluru", "Chennai", "Hyderabad", "Kochi"],
    "West":  ["Mumbai", "Pune", "Ahmedabad", "Surat"],
    "East":  ["Kolkata", "Bhubaneswar", "Patna", "Guwahati"],
}
CITY_TO_REGION = {c: r for r, cs in CITIES.items() for c in cs}

PRODUCTS = {
    "Electronics": [("Wireless Earbuds", 1799), ("Smartwatch", 3499), ("Bluetooth Speaker", 1499), ("Power Bank 10000mAh", 999)],
    "Apparel": [("Cotton T-Shirt", 599), ("Denim Jacket", 2199), ("Running Shoes", 2799), ("Formal Shirt", 899)],
    "Home & Kitchen": [("Non-Stick Pan Set", 1299), ("Electric Kettle", 799), ("LED Desk Lamp", 649), ("Storage Organizer", 449)],
    "Beauty": [("Face Serum", 699), ("Sunscreen SPF50", 449), ("Hair Dryer", 1199), ("Lip Care Kit", 349)],
    "Sports & Fitness": [("Yoga Mat", 799), ("Resistance Bands Set", 599), ("Skipping Rope", 249), ("Dumbbell 5kg Pair", 1599)],
}
ALL_PRODUCTS = [(cat, name, price) for cat, items in PRODUCTS.items() for name, price in items]

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash on Delivery"]

START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 6, 30)


def random_date(start, end):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def messy_date_str(d):
    """Simulate inconsistent date formats across export batches."""
    fmt = random.choice([
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%b %d, %Y", "%d %B %Y",
    ])
    return d.strftime(fmt)


def messy_price_str(price):
    """Simulate currency formatting inconsistencies."""
    style = random.choice(["plain", "rupee_symbol", "comma", "rupee_comma", "decimal"])
    if style == "plain":
        return str(price)
    if style == "rupee_symbol":
        return f"Rs.{price}"
    if style == "comma":
        return f"{price:,}"
    if style == "rupee_comma":
        return f"\u20b9{price:,}"
    return f"{price:.2f}"


def maybe_messy_case(s):
    style = random.choice(["title", "upper", "lower", "title_space"])
    if style == "title":
        return s
    if style == "upper":
        return s.upper()
    if style == "lower":
        return s.lower()
    return f"  {s} "  # stray whitespace


# ---------------------------------------------------------------------------
# SOURCE 1: ONLINE SALES (e-commerce export) -- online_sales_raw.csv
# ---------------------------------------------------------------------------
n_online = 1400
online_rows = []
customer_pool_online = [f"CUST{str(i).zfill(4)}" for i in range(1, 421)]

for i in range(1, n_online + 1):
    order_id = f"ON{str(i).zfill(5)}"
    d = random_date(START_DATE, END_DATE)
    cat, name, price = random.choice(ALL_PRODUCTS)
    qty = random.choices([1, 2, 3, -1], weights=[70, 20, 7, 3])[0]  # -1 simulates a return row
    region = random.choice(list(CITIES.keys()))
    cust = random.choice(customer_pool_online)
    payment = random.choice(PAYMENT_METHODS)

    row = {
        "order_id": order_id,
        "order_date": messy_date_str(d),
        "customer_id": cust,
        "product_category": maybe_messy_case(cat),
        "product_name": name,
        "quantity": qty,
        "unit_price": messy_price_str(price) if random.random() > 0.04 else "",  # ~4% missing price
        "region": region if random.random() > 0.05 else "",  # ~5% missing region
        "payment_method": payment,
    }
    online_rows.append(row)

# Inject ~25 exact duplicate rows (common export glitch)
dup_sample = random.sample(online_rows, 25)
online_rows.extend(dup_sample)

# Inject a few fully blank rows (Excel/CSV export artifact)
for _ in range(4):
    online_rows.append({k: "" for k in online_rows[0].keys()})

df_online = pd.DataFrame(online_rows)
df_online.to_csv("data/raw/online_sales_raw.csv", index=False)
print(f"online_sales_raw.csv -> {len(df_online)} rows")


# ---------------------------------------------------------------------------
# SOURCE 2: STORE / POS SALES (different schema entirely) -- store_sales_raw.xlsx
# ---------------------------------------------------------------------------
n_store = 950
store_rows = []
customer_pool_store = [f"+91{random.randint(7000000000, 9999999999)}" for _ in range(310)]

for i in range(1, n_store + 1):
    txn_id = f"STR-{str(i).zfill(5)}"
    d = random_date(START_DATE, END_DATE)
    cat, name, price = random.choice(ALL_PRODUCTS)
    qty = random.choices([1, 2, 3], weights=[75, 20, 5])[0]
    city = random.choice([c for cs in CITIES.values() for c in cs])
    phone = random.choice(customer_pool_store)

    row = {
        "TransactionID": txn_id,
        "Date": d,  # will be written as native Excel date / sometimes serial-like text
        "StoreCity": maybe_messy_case(city),
        "ItemCategory": cat,
        "ItemSold": name,
        "Qty": qty if random.random() > 0.02 else None,  # ~2% missing qty
        "Price": messy_price_str(price),
        "CustomerPhone": phone,
    }
    store_rows.append(row)

# Duplicate ~15 rows
store_rows.extend(random.sample(store_rows, 15))

df_store = pd.DataFrame(store_rows)

# Write with 2 junk header rows above the real header -- common real-world Excel export issue
with pd.ExcelWriter("data/raw/store_sales_raw.xlsx", engine="openpyxl") as writer:
    pd.DataFrame([["Daily Store Export - Confidential"], ["Generated by POS System v2.3"]]).to_excel(
        writer, index=False, header=False, startrow=0
    )
    df_store.to_excel(writer, index=False, startrow=2)

print(f"store_sales_raw.xlsx -> {len(df_store)} rows (+2 junk header rows)")


# ---------------------------------------------------------------------------
# SOURCE 3: CUSTOMER MASTER -- customers_raw.csv
# ---------------------------------------------------------------------------
FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Karan", "Divya", "Arjun", "Meera",
         "Rahul", "Pooja", "Aditya", "Neha", "Sahil", "Isha", "Manish", "Riya", "Suresh", "Kavya"]
LAST = ["Sharma", "Patel", "Reddy", "Iyer", "Singh", "Gupta", "Nair", "Mehta", "Joshi", "Verma"]
SEGMENTS = ["Regular", "Premium", "New", "VIP"]

cust_rows = []
for i in range(1, 421):
    cust_id = f"CUST{str(i).zfill(4)}" 
    name = f"{random.choice(FIRST)} {random.choice(LAST)}"
    city = random.choice([c for cs in CITIES.values() for c in cs])
    region = CITY_TO_REGION[city]
    signup = random_date(datetime(2022, 1, 1), datetime(2025, 5, 1))
    segment = random.choice(SEGMENTS)

    cust_rows.append({
        "customer_id": cust_id,
        "name": maybe_messy_case(name) if random.random() > 0.7 else name,
        "city": city,
        "region": region,
        "signup_date": messy_date_str(signup),
        "segment": segment,
    })

# Inject ~10 duplicate customer_ids with slightly different name spelling (real-world dedup issue)
for r in random.sample(cust_rows, 10):
    dup = r.copy()
    dup["name"] = dup["name"].strip().upper()
    cust_rows.append(dup)

df_cust = pd.DataFrame(cust_rows)
df_cust.to_csv("data/raw/customers_raw.csv", index=False)
print(f"customers_raw.csv -> {len(df_cust)} rows")

print("\nRaw multi-source data generated in data/raw/")
