# Competitive Pricing Intelligence Pipeline: From Python ETL to dbt Star Schema

> A technical deep-dive into an end-to-end competitive pricing intelligence system — Python-based extraction from HuggingFace, Snowflake staging, dbt-powered dimensional modeling with SCD Type 2 snapshots, and a Power BI layer — built against real Nigerian retail pricing data.

---

## The Pipeline: Two Layers, One Goal

The system is split into two distinct layers, each with a clear responsibility:

```
Layer 1: Data Ingestion (Python)
  HuggingFace API → raw Parquet → Snowflake raw table

Layer 2: Transformation (dbt)
  Snowflake raw → staging view → dimensions + facts → snapshots → Power BI
```

This separation means the ingestion layer doesn't need to know about dimensional modeling, and the transformation layer doesn't care where the data came from.

---

## Layer 1: Ingestion Architecture

The Python pipeline lives entirely in `src/`. Four modules, one dependency direction:

```
connection.py    ← Snowflake connector helper (credentials, session)
extract.py       ← pulls parquet from HuggingFace Datasets API
transform.py     ← cleans, validates, engineers features → writes to local Parquet
load.py          ← reads cleaned Parquet → write_pandas into Snowflake
main.py          ← orchestrates extract() → transform() → load() in sequence
```

### Extract: Minimal and Deliberate

`src/extract.py:7` reads directly from HuggingFace's parquet endpoint using `pd.read_parquet` with an `hf://` URI. The key insight here: no HuggingFace Datasets library dependency needed. The parquet protocol handles column projection and row filtering server-side if you need it later.

```python
def extract() -> pd.DataFrame:
    raw_path: Path = BASE_DIR / "data" / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)

    df: pd.DataFrame = pd.read_parquet(
        "hf://datasets/electricsheepafrica/nigerian_retail_and_ecommerce_"
        "competitor_pricing_datasets/data/nigerian_retail_and_ecommerce_"
        "competitor_pricing_datasets.parquet"
    )
    print(f"Extracted {len(df)} rows")
    return df
```

The function returns the DataFrame but doesn't persist it — `main.py` is responsible for sequencing. This keeps `extract()` testable in isolation.

### Transform: Feature Engineering and the Percent-Difference Bug

`src/transform.py:40` does the heavy lifting. Three phases:

**1. Cleaning.** Lowercase columns, drop nulls, deduplicate. This happens before any derived computation so you don't propagate garbage.

**2. Time features.** Eight derived columns from `date_checked`: `year`, `month`, `month_name`, `week_number`, `day_of_week`, `is_weekend`. These are computed in Pandas so they exist in the raw Parquet — which means the dbt staging model doesn't need to regenerate them from SQL date functions (though it easily could).

**3. Price position and the recalculated difference.** The source data ships with `price_difference_ngn` and `price_difference_percent`, but they were unreliable. The pipeline drops them and recomputes:

```python
# Positive means WE are cheaper than the competitor
price_gap = df["competitor_price_ngn"] - df["our_price_ngn"]
df["price_difference_ngn"] = price_gap.round(2)
df["price_difference_percent"] = (price_gap / df["competitor_price_ngn"] * 100).round(2)

df["price_position"] = np.where(
    df["our_price_ngn"] < df["competitor_price_ngn"], "Cheaper",
    np.where(df["our_price_ngn"] > df["competitor_price_ngn"], "Expensive", "Matched"),
)
```

**Sign convention choice:**
- `competitor_price_ngn - our_price_ngn > 0` → we are cheaper → `price_position = "Cheaper"`
- `competitor_price_ngn - our_price_ngn < 0` → they are cheaper → `price_position = "Expensive"`

This is the opposite of what a naive `our_price - competitor_price` would give. The convention is chosen so that a *positive* `price_difference_ngn` intuitively means *we are winning on price*.

**Output columns** are pinned to an explicit list (`OUTPUT_COLUMNS` in `src/transform.py:18`), ensuring the downstream never receives unexpected columns even if the source schema changes.

### Load: Snowflake via write_pandas

`src/load.py:40` replaces the PostgreSQL/SQLAlchemy approach from earlier iterations with Snowflake's native `write_pandas()`. Key details:

```python
config = {
    var.split("_", 1)[1].lower(): os.getenv(var)
    for var in REQUIRED_ENV_VARS
}
# "SNOWFLAKE_WAREHOUSE" → "warehouse" — matching connect() parameter names

with snowflake.connector.connect(**config) as conn:
    success, _, rows, _ = write_pandas(
        conn, df, TABLE_NAME, auto_create_table=True, overwrite=True
    )
```

**`auto_create_table=True`** infers Snowflake column types from the DataFrame dtypes. This works well but has implications — the dbt staging model (`stg_competitor_pricing.sql`) must explicitly cast every column to guarantee type safety downstream, because Snowflake's inferred types may differ from what dbt expects.

**`overwrite=True`** performs a full refresh (DROP + CREATE). This is appropriate for V1, but it means the snapshot layer (SCD Type 2) sees every row as "new" on each run. In production, switch to incremental loads with a `loaded_at` high-watermark.

### .env Configuration

The `.env` file controls both the Python layer (Snowflake connection) and implicitly the dbt layer (which uses `profiles.yml`). The Python side requires six variables:

```
SNOWFLAKE_USER
SNOWFLAKE_PASSWORD
SNOWFLAKE_ACCOUNT
SNOWFLAKE_WAREHOUSE
SNOWFLAKE_DATABASE
SNOWFLAKE_SCHEMA
SNOWFLAKE_ROLE         (optional)
```

The `connection.py` helper reads these and establishes a connector for ad-hoc queries. `load.py` duplicates the logic in `get_snowflake_config()` — intentional, keeping each module self-contained and independently callable.

---

## Layer 2: dbt Transformation (Star Schema)

Once raw data lands in Snowflake (`PRICING_DIFF.RAW.COMPETITOR_PRICING`), dbt takes over.

### Source Configuration and Freshness Checks

`pricing_difference/models/staging/sources.yml` defines the raw table and enforces freshness:

```yaml
sources:
  - name: pricing_difference
    database: PRICING_DIFF
    schema: raw
    config:
      freshness:
        warn_after: { count: 24, period: hour }
        error_after: { count: 48, period: hour }
    tables:
      - name: competitor_pricing
        columns:
          - name: comparison_id
            data_tests: [unique, not_null]
```

The 24-hour warning threshold means if the Python ingestion hasn't run in a day, you know. The 48-hour error threshold blocks downstream models from stale data.

### Staging Model: Type Casting and the Percent Edge Case

`stg_competitor_pricing.sql` is the gateway. It casts every column explicitly — no implicit type inheritance:

```sql
select
    "comparison_id"::varchar as comparison_id,
    "competitor_price_ngn"::numeric(10,2) as competitor_price,
    "our_price_ngn"::numeric(10,2) as our_price,
    "date_checked"::date as date_checked,
    "in_stock_competitor"::boolean as in_stock_competitor,
    "loaded_at"::timestamp as loaded_at,
    -- ...
```

The most interesting logic is the `percent_difference` normalization:

```sql
case
    when "price_difference_percent" > 1 then "price_difference_percent" / 100.0
    else "price_difference_percent"
end as percent_difference,
```

This handles a real ambiguity in the source data: some records store the percentage as `12.5` (meaning 12.5%) while others store it as `0.125`. The staging model normalizes everything to the decimal form. Without this check, a chart showing "15% average price gap" would be silently wrong.

### Materialization Strategy

`pricing_difference/dbt_project.yml` defines the strategy:

```yaml
staging:
  +materialized: view
  +schema: staging

marts:
  +materialized: table
  +schema: marts
```

- **Staging (`stg_competitor_pricing`)**: a view — no storage cost, always reflects the latest raw data, reusable across all downstream models.
- **Marts (dimensions + facts)**: tables — materialized for join performance and because the surrogate keys and date dimension are static after first build.

### Dimension Models

**dim_product** (`models/marts/dimensions/dim_product.sql`):

```sql
select
    {{ dbt_utils.generate_surrogate_key(['product_name']) }} as product_key,
    product_name,
    current_timestamp() as dbt_created_at,
    current_timestamp() as dbt_updated_at
from (select distinct product_name from {{ ref('stg_competitor_pricing') }})
where product_name is not null
```

The surrogate key is deterministic — running it again produces the same keys for the same products. `current_timestamp()` for both creation and update timestamps means the initial load stamps both, and you'd add update logic in incremental runs.

**dim_competitor** (`models/marts/dimensions/dim_competitor.sql`) follows the identical pattern with `competitor_name`.

**dim_date** (`models/marts/dimensions/dim_date.sql`) is the most interesting dimension:

```sql
with date_spine as (
    select dateadd(day, row_number() over (order by 1) - 1, '2024-01-01'::date) as date_day
    from table(generator(rowcount => 366))
)
select
    date_day,
    year(date_day)::int          as year,
    month(date_day)::int         as month,
    day(date_day)::int           as day,
    quarter(date_day)::int       as quarter,
    date_trunc('month', date_day) as first_day_of_month,
    last_day(date_day, 'month')  as last_day_of_month,
    to_varchar(date_day, 'YYYYMMDD')::int as date_key,
    -- ...
from date_spine
```

Key technical decisions here:

- **`table(generator(rowcount => 366))`** — Snowflake's virtual table generator creates rows without a physical table. 366 covers leap year.
- **`date_key` as `YYYYMMDD` integer** — enables fast integer joins and is a common BI convention (Power BI handles it natively as a join key).
- **`first_day_of_month`, `last_day_of_month`** — pushed into SQL rather than computed in DAX or Power Query, so any consumer of the warehouse gets them automatically.

### Fact Table: Linking Dimensions

`fct_price.sql` joins the staging model to all three dimensions:

```sql
select
    s.comparison_id,
    p.product_key,
    c.competitor_key,
    s.product_name,        -- denormalized for convenience
    s.competitor_name,     -- denormalized for convenience
    s.competitor_price,
    s.our_price,
    s.price_difference,
    s.percent_difference,
    s.price_position,
    s.in_stock_competitor,
    s.date_checked,
    s.loaded_at
from {{ ref('stg_competitor_pricing') }} s
left join {{ ref('dim_product') }} p on s.product_name = p.product_name
left join {{ ref('dim_competitor') }} c on s.competitor_name = c.competitor_name
```

The fact table retains denormalized `product_name` and `competitor_name`. This is intentional — it lets Power BI (or any downstream tool) build visuals from the fact table alone without joining dimensions for simple queries. The dimension keys still exist for star-schema-optimized queries. This hybrid pattern is sometimes called a "drill-through-accommodating" fact table.

### Snapshots: SCD Type 2 for Historical Tracking

`snapshots/snap_competitor_pricing.sql` enables point-in-time price queries:

```sql
{% snapshot snap_competitor_pricing %}
{{
    config(
        target_schema='snapshots',
        unique_key='comparison_id',
        strategy='timestamp',
        updated_at='loaded_at'
    )
}}
select
    comparison_id, product_name, competitor_name,
    competitor_price, our_price,
    price_difference, percent_difference,
    price_position, date_checked, loaded_at
from {{ ref('stg_competitor_pricing') }}
{% endsnapshot %}
```

Every time the Python pipeline re-ingests and dbt re-runs, the snapshot compares each `comparison_id`'s `loaded_at` timestamp. If it changed, the old row gets `dbt_valid_to` set and a new row appears with `dbt_valid_from`. This means you can answer:

```sql
-- What was the competitor's price for each product on August 15?
select * from snap_competitor_pricing
where date_checked <= '2024-08-15'
  and (dbt_valid_to >= '2024-08-15' or dbt_valid_to is null);
```

This only works correctly if the upstream Python layer produces deterministic `comparison_id` values across runs — which it does, since the parquet is a full extract.

### Data Quality Tests

The project enforces several categories of tests:

**Generic tests** in `schema.yml`:
- `unique` on `comparison_id`, `product_key`, `competitor_key`, `date_day`
- `not_null` on 13 critical columns
- `accepted_values` on `price_position` restricting to `["Cheaper", "Expensive", "Matched"]`
- `relationships` foreign key validation between `fct_price` and `dim_product`/`dim_competitor`

Run with:

```bash
dbt test --fail-fast
```

---

## Power BI: Consuming the Star Schema

The Power BI report connects to Snowflake and consumes the marts schema. The relationship model is:

```
dim_product.product_key        ← fct_price.product_key
dim_competitor.competitor_key  ← fct_price.competitor_key
dim_date.date_day              ← fct_price.date_checked
```

### Key DAX Measures

**Competitive Win Rate** — the percentage of comparisons where our price is lower:

```dax
Win Rate =
DIVIDE(
    COUNTROWS(FILTER(fct_price, fct_price[price_position] = "Cheaper")),
    COUNTROWS(fct_price)
) * 100
```

**Undercut Rate** — the percentage where the competitor is cheaper:

```dax
Undercut Rate =
DIVIDE(
    COUNTROWS(FILTER(fct_price, fct_price[price_position] = "Expensive")),
    COUNTROWS(fct_price)
) * 100
```

**Average Price Gap (when undercut)** — the average absolute gap when we're being beaten:

```dax
Avg Price Gap (Undercut) =
CALCULATE(
    AVERAGEX(fct_price, ABS(fct_price[price_difference])),
    fct_price[price_position] = "Expensive"
)
```

**Competitive Threat Index** — a composite combining frequency, magnitude, and availability. This surfaces the competitor-product combinations that represent genuine risk rather than theoretical pricing disadvantage. In DAX:

```dax
Threat Index =
VAR ThreatRows =
    FILTER(
        fct_price,
        fct_price[price_position] = "Expensive"
            && fct_price[in_stock_competitor] = TRUE
    )
RETURN
    AVERAGEX(ThreatRows, fct_price[price_difference] * -1)
```

The `* -1` converts the negative `price_difference` (competitor is cheaper) into a positive threat score.

### Dashboard Structure

The final report has three views:

1. **Executive Summary** — Win Rate, Undercut Rate, Average Price Gap, Total Comparisons as KPI cards. A trend line over time shows whether competitive position is improving.
2. **Competitor Deep-Dive** — each competitor's average gap, stock availability rate, and price position distribution. Filters by product category.
3. **Product Edge Analysis** — products sorted by Threat Index. Highlights which SKUs are most exposed and which competitors pose the biggest risk per product.

---

## Technical Decisions Worth Explaining

### Why Both Pandas Time Features and dbt Date Dimensions?

The Python layer computes `year`, `month`, `week_number`, etc. and stores them in the parquet. The dbt layer also has a `dim_date` dimension. This is redundancy by design:

- The Pandas-computed columns exist in the raw Snowflake table, so queries against raw data are immediately useful without joining to dim_date.
- `dim_date` provides enrichment (quarter boundaries, season flags, fiscal periods) that the Python layer doesn't compute.
- If the Python ingestion changes, dbt can always recompute time features from `date_checked` — the dim_date dimension is the source of truth for calendar logic.

### Why `write_pandas` Over `to_sql`?

Earlier versions used SQLAlchemy's `df.to_sql()`. The switch to `snowflake.connector.pandas_tools.write_pandas()` offers:
- Batch INSERT with automatic chunking — 10x-50x faster than row-by-row
- Native Snowflake type inference from pandas dtypes
- No SQLAlchemy dependency in the load path (though it remains in `requirements.txt` for other uses)

### Why Denormalized Names in the Fact Table?

`fct_price` includes both `product_key` (FK) and `product_name` (denormalized). The reason is BI tool behavior: when a user drags "product_name" into a Power BI visual, a star-schema-optimized query engine pushes a join to dim_product. With the denormalized column, Power BI can satisfy the query from the fact table alone — no join needed. For a fact table of this size (~50K rows), the storage overhead is negligible and the query performance gain is real.

---

## Running the Pipeline

From scratch:

```bash
# 1. Configure credentials
cp .env.example .env
# Edit .env with Snowflake credentials and db config

# 2. Python ingestion layer
python src/main.py

# 3. dbt transformation layer
cd pricing_difference
dbt debug                            # verify connection
dbt deps                             # install dbt_utils package
dbt run                              # build staging → dimensions → fact
dbt test --fail-fast                 # validate data quality
dbt snapshot                         # capture historical state
dbt docs generate && dbt docs serve  # view lineage documentation
```

The `dbt run` executes in this order because dbt resolves the DAG from the ref() calls:

1. `stg_competitor_pricing` (view) — no storage cost
2. `dim_product`, `dim_competitor`, `dim_date` (tables) — can run in parallel
3. `fct_price` (table) — depends on all three dimensions
4. `snap_competitor_pricing` (snapshot) — runs last, captures final state

---

## Known Limitations and Migration Path

| Limitation | Impact | Fix |
|---|---|---|
| Full refresh (`overwrite=True`) | All rows re-inserted on each run; snapshots capture every row as "changed" | Switch to incremental with `loaded_at` high-watermark |
| `product_name` as natural key | Renaming a product breaks the dimension key linkage | Add a stable `product_id` column to the source or use a hash of `product_name` |
| 366-day date dimension | Breaks after 2024 | Parameterize with `date_trunc('year', current_date)` |
| No dedup in staging view | `pd.drop_duplicates()` in Python handles this, but dbt doesn't re-enforce it | Add `row_number() over (partition by comparison_id order by loaded_at desc) = 1` in staging |
| Single source table | Adding a second dataset (e.g., competitor stock levels) requires a new source | Follow the same pattern: new Python module, new source in sources.yml, new staging model |

---

## Conclusion

This pipeline demonstrates a practical pattern: Python handles what Python is good at (HTTP requests, DataFrame manipulation, library ecosystem) and dbt handles what dbt is good at (SQL transformations, lineage tracking, documentation, testing, SCD management). The boundary between them is clear — Parquet files on disk and then Snowflake tables — which makes each layer independently testable, deployable, and replaceable.

The key technical lesson across both layers: **always validate derived fields against their source components**. In the Python layer, that meant dropping and recomputing `price_difference`. In the dbt layer, that meant normalizing `percent_difference` with the `CASE` statement. The validation pattern is the same regardless of tooling — it's a habit, not a feature.
