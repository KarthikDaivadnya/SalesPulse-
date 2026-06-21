# Building the Power BI Dashboard (Step-by-Step)

This guide rebuilds the SalesPulse dashboard inside **real Power BI Desktop**,
using the exact same cleaned dataset (`data/processed/sales_cleaned.csv`)
that powers the SQL queries and the HTML dashboard in this repo. It takes
about 15–20 minutes the first time.

> Why this exists: the resume/portfolio claim is "built in Power BI", and
> Power BI Desktop is Windows-only — it can't be scripted from a Linux
> environment. This guide is the bridge: the data and logic are already
> proven correct (see `scripts/` and `queries.sql`), you're just pointing
> the real BI tool at them.

## Prerequisites
- Power BI Desktop (free) — install from the Microsoft Store or
  `powerbi.microsoft.com/desktop` if not already installed.
- The file `data/processed/sales_cleaned.csv` from this repo.

---

## Step 1 — Import the data
1. Open Power BI Desktop → **Get Data** → **Text/CSV**.
2. Select `sales_cleaned.csv`. Click **Load** (not "Transform Data" — the
   file is already cleaned, so no further transform is needed).
3. In the **Fields** pane on the right, confirm these columns came in with
   the correct type (Power BI usually auto-detects correctly, but check):
   - `order_date` → **Date**
   - `quantity`, `unit_price`, `revenue` → **Decimal Number** or **Whole Number**
   - everything else → **Text**

   If `order_date` imported as Text, right-click the column → **Change Type** → **Date**.

## Step 2 — Create a proper Date table (recommended)
Time-intelligence (month-over-month, week-over-week) works much better with
a dedicated date table rather than relying on the raw `order_date` column directly.

1. **Modeling** tab → **New Table**. Paste:
   ```
   DateTable = CALENDAR(MIN(sales_cleaned[order_date]), MAX(sales_cleaned[order_date]))
   ```
2. With `DateTable` selected, **New Column** a few times to add:
   ```
   Month = FORMAT(DateTable[Date], "MMM YYYY")
   MonthSort = YEAR(DateTable[Date]) * 100 + MONTH(DateTable[Date])
   Week = WEEKNUM(DateTable[Date])
   ```
3. Go to **Model view**, drag a relationship from `DateTable[Date]` to
   `sales_cleaned[order_date]` (one-to-many, single direction).

## Step 3 — Core DAX measures
**Modeling** → **New Measure**, and add each of these one at a time:

```
Total Revenue = SUM(sales_cleaned[revenue])

Total Orders = COUNTROWS(sales_cleaned)

Avg Order Value = DIVIDE([Total Revenue], [Total Orders])

Online Customers = CALCULATE(
    DISTINCTCOUNT(sales_cleaned[customer_id]),
    sales_cleaned[source] = "Online"
)

Revenue (Prior Month) = CALCULATE(
    [Total Revenue],
    DATEADD(DateTable[Date], -1, MONTH)
)

Revenue MoM % = DIVIDE([Total Revenue] - [Revenue (Prior Month)], [Revenue (Prior Month)])

Returns Count = CALCULATE(COUNTROWS(sales_cleaned), sales_cleaned[quantity] < 0)
```

> These map 1:1 to the KPI cards in the HTML dashboard (`dashboard/dashboard.js`,
> see `computeKPIs()`) and to query 1 and query 8 in `scripts/queries.sql` —
> so the three artifacts (SQL / HTML dashboard / Power BI) all agree on the
> same numbers, which is worth mentioning if asked in an interview.

## Step 4 — Build the report page
Recommended layout (matches the HTML dashboard's structure):

1. **KPI cards** (top row): Insert → **Card** visual ×4, one each for
   `Total Revenue`, `Total Orders`, `Avg Order Value`, `Online Customers`.
2. **Revenue trend** (line chart): X-axis = `DateTable[Month]` (sorted by
   `MonthSort`), Y-axis = `Total Revenue`.
3. **Revenue by Region** (bar chart): Axis = `sales_cleaned[region]`,
   Value = `Total Revenue`. Sort descending.
4. **Channel split** (donut chart): Legend = `sales_cleaned[source]`,
   Value = `Total Revenue`.
5. **Top Products** (table or bar chart): `product_name`, `quantity` (sum),
   `Total Revenue`. Use the visual's **Filter** pane → Top N → 5, by `Total Revenue`.
6. **Category Performance** (matrix/table): Rows = `product_category`,
   Values = `Total Orders`, sum of `quantity`, `Total Revenue`, `Avg Order Value`.

## Step 5 — Add the slicers (drill-down filters)
Insert → **Slicer** for each of: `region`, `product_category`, `source`,
`DateTable[Month]`. Arrange them in a row above the visuals. This gives you
the same interactive filter bar as the HTML dashboard — clicking any slicer
value cross-filters every visual on the page automatically (Power BI does
this natively, no extra configuration needed).

## Step 6 — Style pass (optional but recommended)
To visually match the resume's navy/blue branding:
- **View** → **Themes** → **Customize current theme** → set the primary
  color to `#1F3864` (the same navy used in the resume header) and a
  secondary accent of `#2E5FAC`.
- Card visuals: Format pane → set background to a light grey (`#F2F2F2`) with
  a thin border, and increase the data label font size to ~28pt for the KPI numbers.

## Step 7 — Publish / Export
- **File → Export → Export to PDF** for a static copy to attach to
  applications, or
- **File → Publish** (needs a free Power BI account) to get a shareable
  web link you can put directly on your resume/portfolio/LinkedIn.

Either way, save the `.pbix` file itself and push it to the GitHub repo
alongside this guide — that `.pbix` file is the literal artifact that backs
up the "Power BI" line on the resume.

---

### Talking points for an interview
If asked about this project, the honest, accurate description is: *"I built
the full pipeline myself — generated/sourced the raw data, wrote the Python
cleaning scripts, modeled it in SQL, and built both an interactive Power BI
dashboard and a custom HTML/JS dashboard on top of the same cleaned dataset,
so I could compare a code-first and tool-first approach to the same
analysis."* That is a genuinely strong, specific answer, and notice it
doesn't require pretending the dataset came from a real company — being
upfront that it's a self-generated dataset for a portfolio project is
completely normal and expected for a fresher project.
