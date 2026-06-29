# Nigerian Retail Competitive Pricing Intelligence Pipeline

> An end-to-end data pipeline that extracts Nigerian retail competitor pricing data from HuggingFace, transforms it through a dbt-powered dimensional star schema in Snowflake, and surfaces actionable competitive intelligence through Power BI dashboards.

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/)
[![dbt](https://img.shields.io/badge/dbt-1.11-orange)](https://www.getdbt.com/)
[![Snowflake](https://img.shields.io/badge/snowflake-latest-blue)](https://www.snowflake.com/)
[![Power BI](https://img.shields.io/badge/power%20bi-ready-yellow)](https://powerbi.microsoft.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

# TL;DR

```bash
cp .env.example .env        # edit with Snowflake credentials
python src/main.py           # extract → transform → load raw data
cd pricing_difference
dbt deps && dbt run          # build star schema
dbt test --fail-fast         # validate data quality
dbt snapshot                 # capture SCD Type 2 history
dbt docs serve               # view lineage & docs at :8000
```

Then connect Power BI to Snowflake → `PRICING_DIFF.MARTS.*` → dashboard ready.

---

---

## The Business Problem

Pricing in Nigerian retail is fast, fragmented, and unforgiving. Competitors adjust prices with little warning. Products go in and out of stock constantly. Most businesses make pricing decisions based on gut feel and manual observation.

This pipeline answers one question systematically: **How are we positioned relative to the market?** Not "how did we perform last quarter" — but right now, product by product, competitor by competitor, who is winning on price?

### What This Pipeline Delivers

| Business Question | How the Pipeline Answers It |
|---|---|
| "Are we competitive on price?" | **Win Rate** — % of comparisons where we're cheaper |
| "Who is undercutting us most?" | **Undercut Rate** by competitor, with average gap magnitude |
| "Is a cheaper competitor actually a threat?" | **Threat Index** — combines price gap + stock availability |
| "How is our position changing?" | **SCD Type 2 snapshots** — track every price change over time |
| "Where are we most exposed?" | **Product Edge Analysis** — products sorted by combined risk score |

---

## Key Business Metrics

### Price Position (Categorical)

Every comparison row is classified into one of three states:

| Position | Meaning | Signal |
|---|---|---|
| **Cheaper** | Our price < competitor price | We are winning on this product |
| **Expensive** | Our price > competitor price | Competitor is undercutting us |
| **Matched** | Our price = competitor price | Tied — potential to differentiate |

This single column (`price_position`) drives all downstream aggregation. DAX measures or SQL queries slice by it without needing inline CASE logic.

### Win Rate

The headline metric: what percentage of comparisons are we winning?

```
Win Rate = (count where position = "Cheaper") / (total comparisons) × 100
```

A Win Rate of 60% means you beat the competition on price in 6 out of 10 comparisons. Trends over time reveal whether pricing strategy is working or eroding.

### Undercut Rate

The flip side: how often is the competitor cheaper?

```
Undercut Rate = (count where position = "Expensive") / (total comparisons) × 100
```

High Undercut Rate + high competitor stock availability = genuine competitive risk.

### Average Price Gap (when undercut)

It's not enough to know *that* you're being undercut — you need to know *by how much*:

```
Avg Price Gap = AVG(ABS(price_difference)) WHERE position = "Expensive"
```

A ₦500 gap on a ₦5,000 item (10%) is very different from a ₦500 gap on a ₦15,000 item (3.3%). Contextualize gap by product category.

### Competitive Threat Index

A composite score that surfaces genuine risk — not just theoretical pricing disadvantage. It combines three signals:

1. **Competitor is cheaper** (`position = "Expensive"`)
2. **Competitor is in stock** (`in_stock_competitor = TRUE`)
3. **Magnitude of the gap** (`ABS(price_difference)`)

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

A cheaper competitor who is consistently out of stock is not the same threat as one who is cheaper and always available. The Threat Index accounts for both.

### Out-of-Stock Rate by Competitor

```dax
OOS Rate =
DIVIDE(
    COUNTROWS(FILTER(fct_price, fct_price[in_stock_competitor] = FALSE)),
    COUNTROWS(fct_price)
) * 100
```

If a competitor undercuts you on price but has a 40% OOS rate, their pricing is less of a threat — customers can't act on it consistently.

### Price Volatility Index

Using the snapshot table, you can measure how frequently a competitor changes prices:

```sql
select
    competitor_name,
    product_name,
    count(distinct dbt_valid_from) as price_changes,
    datediff('day', min(dbt_valid_from), max(dbt_valid_from)) as observation_days,
    round(count(distinct dbt_valid_from) / nullif(datediff('day', min(dbt_valid_from), max(dbt_valid_from)), 0), 3) as changes_per_day
from snap_competitor_pricing
group by competitor_name, product_name
order by changes_per_day desc;
```

Competitors who change prices daily require different monitoring than those who adjust monthly.

---

## Project Structure

```
competitive-pricing-etl/
│
├── src/                              # PYTHON INGESTION LAYER
│   ├── extract.py                    # Reads Parquet from HuggingFace Datasets API
│   ├── transform.py                  # Cleaning, validation, feature engineering
│   ├── load.py                       # write_pandas → Snowflake
│   ├── connection.py                 # Snowflake connector helper
│   └── main.py                       # Orchestrator: extract() → transform() → load()
│
├── pricing_difference/               # dbt TRANSFORMATION LAYER
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_competitor_pricing.sql   # Type casting, percent normalization
│   │   │   ├── sources.yml                  # Source definitions + freshness checks
│   │   │   └── schema.yml                   # Column-level tests & documentation
│   │   │
│   │   ├── marts/
│   │   │   ├── dimensions/
│   │   │   │   ├── dim_product.sql          # Surrogate keys via dbt_utils
│   │   │   │   ├── dim_competitor.sql       # Identical pattern to dim_product
│   │   │   │   └── dim_date.sql             # Snowflake generator() calendar
│   │   │   ├── facts/
│   │   │   │   └── fct_price.sql            # Star schema fact table
│   │   │   └── schema.yml
│   │   └── exposures.yml
│   │
│   ├── snapshots/
│   │   └── snap_competitor_pricing.sql      # SCD Type 2 (timestamp strategy)
│   │
│   ├── macros/
│   │   └── generate_schema.sql
│   ├── tests/                               # Singular tests
│   ├── analyses/
│   ├── seeds/
│   ├── dbt_packages/
│   │   └── dbt_utils/                       # v1.4.0
│   ├── packages.yml
│   ├── dbt_project.yml
│   └── .gitignore
│
├── data/
│   ├── raw/                                 # Original Parquet from HuggingFace
│   └── processed/                           # Cleaned Parquet (before Snowflake load)
│
├── bi_report/                               # Power BI assets
│   ├── Competitive Pricing Report.pbix
│   ├── Competitive Pricing Report.pdf
│   └── Competitive Pricing Report.jpg
│
├── image/                                   # Architecture diagrams
├── .env.example                             # Template for credentials
├── requirements.txt
└── readme.md
```

---

## Architecture: Two Layers, One Goal

```
┌─────────────────────────────────────────────────────────────────────┐
│                  LAYER 1: PYTHON INGESTION                           │
│                                                                      │
│  HuggingFace API                                                     │
│       │                                                              │
│       ▼                                                              │
│  extract.py  ──►  data/raw/  ──►  transform.py  ──►  data/processed/│
│       │                  .parquet              │       .parquet      │
│       └────────────────────────────────────────┘                     │
│                                                    │                 │
│                                                    ▼                 │
│                                             load.py                  │
│                                          (write_pandas)              │
│                                                    │                 │
└──────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
                                      ┌─────────────────────┐
                                      │  Snowflake           │
                                      │  PRICING_DIFF.RAW    │
                                      │  .COMPETITOR_PRICING │
                                      └─────────────────────┘
                                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                  LAYER 2: dbt TRANSFORMATION                         │
│                                                                      │
│               [sources.yml — freshness checks]                       │
│                        │                                             │
│                        ▼                                             │
│         stg_competitor_pricing (VIEW — type casting)                 │
│                        │                                             │
│              ┌─────────┼──────────────┐                              │
│              ▼         ▼              ▼                              │
│      dim_product  dim_competitor  dim_date  (TABLES)                 │
│              │         │              │                              │
│              └─────────┼──────────────┘                              │
│                        ▼                                             │
│                fct_price (TABLE — star schema)                       │
│                        │                                             │
│                        ▼                                             │
│       snap_competitor_pricing (SCD Type 2 snapshot)                 │
│                        │                                             │
│                        ▼                                             │
│              Power BI / Analytics Tools                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Why Two Layers?

This separation is deliberate:

- **Python handles** what Python is good at: HTTP requests, DataFrame manipulation, Parquet I/O, library ecosystem.
- **dbt handles** what dbt is good at: SQL transformations, lineage tracking, documentation generation, data testing, SCD management.
- The boundary — Parquet files → Snowflake tables — is filesystem-stable and tool-agnostic. Each layer is independently testable, deployable, and replaceable.

---

## Layer 1: Python Ingestion Deep-Dive

The ingestion pipeline lives in `src/` — four modules with one dependency direction.

### Extract (`src/extract.py:7`)

Reads the parquet dataset directly from HuggingFace using `pd.read_parquet` with an `hf://` URI. No HuggingFace Datasets library dependency — the Parquet protocol handles this.

```python
def extract() -> pd.DataFrame:
    raw_path: Path = BASE_DIR / "data" / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)
    df: pd.DataFrame = pd.read_parquet(
        "hf://datasets/electricsheepafrica/..."
        "nigerian_retail_and_ecommerce_competitor_pricing_datasets.parquet"
    )
    return df
```

The function returns the DataFrame without persisting it — `main.py` sequences persistence. This keeps `extract()` independently testable.

### Transform (`src/transform.py:40`)

Three phases of data processing:

**1. Cleaning.** Lowercase all columns, drop nulls, deduplicate — before any derived computation.

**2. Time features.** Eight columns from `date_checked`: `year`, `month`, `month_name`, `week_number`, `day_of_week`, `is_weekend`. These exist in both the raw Parquet and the Snowflake raw table, so downstream queries are immediately useful without joining to `dim_date`.

**3. Price recalculation.** The source data ships with unreliable `price_difference_ngn` and `price_difference_percent`. The pipeline drops both and recomputes:

```python
# Positive → we are cheaper; Negative → competitor is cheaper
price_gap = df["competitor_price_ngn"] - df["our_price_ngn"]
df["price_difference_ngn"] = price_gap.round(2)
df["price_difference_percent"] = (price_gap / df["competitor_price_ngn"] * 100).round(2)
```

The sign convention is deliberate: `competitor_price - our_price` means a positive value = we win. This is more intuitive for business consumers than a negative "our price minus their price."

Output columns are pinned to an explicit list (`OUTPUT_COLUMNS`), making the interface contract explicit.

### Load (`src/load.py:40`)

Uses Snowflake's native `write_pandas()` instead of SQLAlchemy:

```python
with snowflake.connector.connect(**config) as conn:
    success, _, rows, _ = write_pandas(
        conn, df, TABLE_NAME, auto_create_table=True, overwrite=True
    )
```

| Decision | Why |
|---|---|
| `write_pandas` vs `to_sql` | 10x-50x faster batch INSERT with automatic chunking |
| `auto_create_table=True` | Infers Snowflake types from pandas dtypes — no manual DDL |
| `overwrite=True` | Full refresh — appropriate for V1; future iterations should use incremental |

### .env Configuration

```
SNOWFLAKE_USER       │ SNOWFLAKE_PASSWORD       │ SNOWFLAKE_ACCOUNT
SNOWFLAKE_WAREHOUSE  │ SNOWFLAKE_DATABASE       │ SNOWFLAKE_SCHEMA
SNOWFLAKE_ROLE       (optional)
```

---

## Layer 2: dbt Transformation Deep-Dive

Once raw data lands in `PRICING_DIFF.RAW.COMPETITOR_PRICING`, dbt takes over.

### Source Configuration (`sources.yml`)

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

24-hour warning tells you the Python pipeline hasn't run. 48-hour error blocks downstream models from stale data.

### Staging Model (`stg_competitor_pricing.sql`)

Every column is explicitly cast — no implicit type inheritance from Snowflake's auto-created table:

```sql
select
    "comparison_id"::varchar as comparison_id,
    "competitor_price_ngn"::numeric(10,2) as competitor_price,
    "our_price_ngn"::numeric(10,2) as our_price,
    "date_checked"::date as date_checked,
    "in_stock_competitor"::boolean as in_stock_competitor,
```

The critical piece: **percent_difference normalization**:

```sql
case
    when "price_difference_percent" > 1 then "price_difference_percent" / 100.0
    else "price_difference_percent"
end as percent_difference,
```

The source data stores percentages inconsistently — sometimes as `12.5` (12.5%), sometimes as `0.125`. This case statement normalizes everything to the decimal form. Without it, charts showing "15% average price gap" would be silently wrong.

### Materialization Strategy

| Layer | Materialization | Rationale |
|---|---|---|
| `stg_competitor_pricing` | **View** | No storage cost; always reflects latest raw data |
| `dim_product` | **Table** | Deterministic surrogate key; rarely changes |
| `dim_competitor` | **Table** | Same pattern as dim_product |
| `dim_date` | **Table** | Static calendar — build once, query many times |
| `fct_price` | **Table** | Join performance for BI queries |

### Dimension Models

**dim_product** generates a deterministic surrogate key:

```sql
select
    {{ dbt_utils.generate_surrogate_key(['product_name']) }} as product_key,
    product_name,
    current_timestamp() as dbt_created_at,
    current_timestamp() as dbt_updated_at
from (select distinct product_name from {{ ref('stg_competitor_pricing') }})
where product_name is not null
```

**dim_date** uses Snowflake's virtual table generator:

```sql
with date_spine as (
    select dateadd(day, row_number() over (order by 1) - 1, '2024-01-01'::date) as date_day
    from table(generator(rowcount => 366))
)
```

`table(generator(rowcount => 366))` creates rows without a physical table. 366 covers leap year. The `date_key` is stored as a `YYYYMMDD` integer for fast joins — Power BI handles this natively.

### Fact Table (`fct_price.sql`)

```sql
select
    s.comparison_id,
    p.product_key,
    c.competitor_key,
    s.product_name,        -- denormalized for BI convenience
    s.competitor_name,     -- denormalized for BI convenience
    s.competitor_price, s.our_price,
    s.price_difference, s.percent_difference,
    s.price_position, s.in_stock_competitor,
    s.date_checked, s.loaded_at
from {{ ref('stg_competitor_pricing') }} s
left join {{ ref('dim_product') }} p on s.product_name = p.product_name
left join {{ ref('dim_competitor') }} c on s.competitor_name = c.competitor_name
```

The fact table retains denormalized `product_name` and `competitor_name`. This lets Power BI build visuals from the fact table alone without joining dimensions for simple queries — saving a join per visual for the ~50K row dataset.

### Snapshots: SCD Type 2 (`snap_competitor_pricing.sql`)

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
select * from {{ ref('stg_competitor_pricing') }}
{% endsnapshot %}
```

Every re-run compares each `comparison_id`'s `loaded_at`. Changed rows get `dbt_valid_to` set; new rows appear with `dbt_valid_from`. This enables point-in-time queries:

```sql
-- What was the competitor's price on August 15?
select * from snap_competitor_pricing
where date_checked <= '2024-08-15'
  and (dbt_valid_to >= '2024-08-15' or dbt_valid_to is null);
```

### Data Quality Tests

Enforced at schema level via `schema.yml`:

- **`unique`** — `comparison_id`, `product_key`, `competitor_key`, `date_day`
- **`not_null`** — 13 critical columns
- **`accepted_values`** — `price_position` restricted to `["Cheaper", "Expensive", "Matched"]`
- **`relationships`** — FK validation between `fct_price` and both dimensions

```bash
dbt test --fail-fast
```

---

## Data Model (Star Schema)

```
┌─────────────────────┐     ┌───────────────────────────────────┐     ┌─────────────────────┐
│     dim_product     │     │          fct_price                │     │   dim_competitor    │
├─────────────────────┤     ├───────────────────────────────────┤     ├─────────────────────┤
│ product_key (PK)    │◄───►│ comparison_id (PK)               │◄───►│ competitor_key (PK) │
│ product_name        │     │ product_key (FK)                 │     │ competitor_name     │
│ dbt_created_at      │     │ competitor_key (FK)              │     │ dbt_created_at      │
│ dbt_updated_at      │     │ product_name (denormalized)      │     │ dbt_updated_at      │
└─────────────────────┘     │ competitor_name (denormalized)   │     └─────────────────────┘
                            │ our_price (NUMERIC 10,2)         │
┌─────────────────────┐     │ competitor_price (NUMERIC 10,2)  │
│     dim_date        │     │ price_difference (NUMERIC 10,2)  │
├─────────────────────┤     │ percent_difference (FLOAT)       │
│ date_day (PK)       │◄───►│ price_position (VARCHAR)         │
│ year                │     │ in_stock_competitor (BOOLEAN)    │
│ month               │     │ date_checked (DATE)              │
│ quarter             │     │ loaded_at (TIMESTAMP)            │
│ month_name          │     └───────────────────────────────────┘
│ day_name            │
│ day_of_week         │     ┌───────────────────────────────────────┐
│ week_of_year        │     │      snap_competitor_pricing         │
│ is_weekend          │     ├───────────────────────────────────────┤
│ first_day_of_month  │     │ comparison_id                        │
│ last_day_of_month   │     │ competitor_price, our_price          │
│ first_day_of_year   │     │ price_difference, percent_difference │
│ first_day_of_quarter│     │ price_position, date_checked         │
│ date_key (INT)      │     │ dbt_scd_id                           │
└─────────────────────┘     │ dbt_valid_from, dbt_valid_to         │
                            │ dbt_is_deleted                       │
                            └───────────────────────────────────────┘
```

---

## Power BI Dashboard

### Connecting

1. Power BI Desktop → **Get Data** → **Snowflake**
2. Enter account, warehouse, database (`PRICING_DIFF`), schema (`MARTS`)
3. Import `dim_product`, `dim_competitor`, `dim_date`, `fct_price`
4. Create relationships:
   - `fct_price.product_key` → `dim_product.product_key`
   - `fct_price.competitor_key` → `dim_competitor.competitor_key`
   - `fct_price.date_checked` → `dim_date.date_day`

### DAX Measures

```dax
Win Rate =
DIVIDE(
    COUNTROWS(FILTER(fct_price, fct_price[price_position] = "Cheaper")),
    COUNTROWS(fct_price)
) * 100

Undercut Rate =
DIVIDE(
    COUNTROWS(FILTER(fct_price, fct_price[price_position] = "Expensive")),
    COUNTROWS(fct_price)
) * 100

Avg Price Gap (Undercut) =
CALCULATE(
    AVERAGEX(fct_price, ABS(fct_price[price_difference])),
    fct_price[price_position] = "Expensive"
)

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

### Dashboard Preview

![Competitive Pricing Dashboard](bi_report/Competitive%20Pricing%20Report.jpg)

### Dashboard Views

1. **Executive Summary** — Win Rate, Undercut Rate, Avg Price Gap as KPI cards with trend lines
2. **Competitor Deep-Dive** — Per-competitor average gap, OOS rate, price position distribution
3. **Product Edge Analysis** — Products ranked by Threat Index; highlights most exposed SKUs

---

## Full Pipeline Run

```bash
# 1. Configure Snowflake credentials
cp .env.example .env
# Edit .env with your Snowflake details

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run Python ingestion layer
python src/main.py
#   ├── extract.py   → downloads Parquet from HuggingFace
#   ├── transform.py → cleans, validates, engineers features
#   └── load.py      → write_pandas into Snowflake

# 4. Run dbt transformation layer
cd pricing_difference
dbt deps                     # install dbt_utils
dbt debug                    # verify Snowflake connection
dbt run                      # build staging view + dimensions + fact
dbt test --fail-fast         # validate data quality
dbt snapshot                 # capture SCD Type 2 history
dbt docs generate            # generate lineage docs
dbt docs serve               # view at http://localhost:8000
```

dbt resolves the DAG automatically. Execution order:
1. `stg_competitor_pricing` (view)
2. `dim_product`, `dim_competitor`, `dim_date` (parallel)
3. `fct_price` (depends on all three dimensions)
4. `snap_competitor_pricing` (captures final state)

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Data Source** | HuggingFace Datasets | Nigerian retail competitor pricing dataset |
| **Ingestion** | Python 3.13, Pandas, PyArrow | Parquet download, cleaning, feature engineering |
| **Storage** | Snowflake | Cloud data warehouse |
| **Transformation** | dbt Core 1.11 | SQL-based modeling, lineage, testing, snapshots |
| **Orchestration** | dbt run / Python main.py | Manual sequencing |
| **BI** | Power BI | Dashboards, DAX measures, competitive analysis |
| **Packages** | dbt_utils 1.4.0 | Surrogate key generation |

---

## Known Limitations & Roadmap

| Limitation | Impact | Future Fix |
|---|---|---|
| Full refresh (`overwrite=True`) | All rows re-inserted on each run; snapshots capture every row as "changed" | Incremental with `loaded_at` high-watermark |
| `product_name` as natural key | Renaming a product breaks dimension linkage | Add stable `product_id` or use hash of `product_name` |
| 366-day date dimension | Breaks after 2024 | Parameterize with `date_trunc('year', current_date)` |
| No dedup in dbt staging | Python handles dedup; dbt doesn't re-enforce | Add `row_number() over (partition by comparison_id order by loaded_at desc) = 1` |
| Single source table | Can't cross-analyze with stock levels or promotions | Follow same pattern: new Python module + new source + new staging model |
| Manual orchestration | No scheduling or alerting on failures | Apache Airflow / Prefect / dbt Cloud |
| No price prediction | Descriptive only — doesn't forecast competitor moves | Add ML layer using snapshot time series |
| No real-time ingestion | Data freshness = pipeline run cadence | Switch to streaming (Kafka / Snowpipe) for near-real-time pricing |

---

## Key Technical Lessons

1. **Never trust derived fields in source data.** The pre-calculated `price_difference_ngn` and `price_difference_percent` columns were incorrect. Always validate derived fields against their source components. If they don't match, recompute.

2. **Normalize ambiguous formats at the staging boundary.** The `percent_difference > 1` case handles a real inconsistency in the source data. Catch these at ingestion, not in BI.

3. **Redundancy is OK when it solves a real problem.** The fact table includes denormalized product/competitor names. Time features exist in both Python output and the dbt date dimension. Both choices trade storage for query simplicity — a good trade at this scale.

4. **Design the sign convention for the business user.** `competitor_price - our_price` with "positive = we win" is more intuitive than a negative gap. Small UX decisions in the data model determine whether business users trust the dashboard.

---

## Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [Snowflake dbt Adapter](https://docs.getdbt.com/reference/warehouse-setups/snowflake-setup)
- [dbt_utils Package](https://hub.getdbt.com/dbt-labs/dbt_utils/latest/)
- [HuggingFace Dataset](https://huggingface.co/datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets)
- [Dimensional Modeling (Kimball)](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Power BI Snowflake Connector](https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-connect-snowflake)
