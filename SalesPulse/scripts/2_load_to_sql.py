"""
SalesPulse - Step 2: Load cleaned data into SQLite
-----------------------------------------------------
Creates sales_data.db with two tables: sales (the fact table) and
customers (dimension table), so that queries.sql can run against a real
SQL database rather than just an in-memory dataframe.
"""
import pandas as pd
import sqlite3

DB_PATH = "sales_data.db"

sales = pd.read_csv("data/processed/sales_cleaned.csv", parse_dates=["order_date"])
customers = pd.read_csv("data/processed/customers_cleaned.csv", parse_dates=["signup_date"])
returns = pd.read_csv("data/processed/returns_log.csv")

conn = sqlite3.connect(DB_PATH)
sales.to_sql("sales", conn, if_exists="replace", index=False)
customers.to_sql("customers", conn, if_exists="replace", index=False)
returns.to_sql("returns", conn, if_exists="replace", index=False)

# Helpful indexes for the aggregation queries we'll run repeatedly
cur = conn.cursor()
cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(order_date)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_region ON sales(region)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales(customer_id)")
conn.commit()

tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
print(f"Database created: {DB_PATH}")
print(f"Tables: {tables['name'].tolist()}")
print(f"  sales      : {len(sales):,} rows")
print(f"  customers  : {len(customers):,} rows")
print(f"  returns    : {len(returns):,} rows")

conn.close()
