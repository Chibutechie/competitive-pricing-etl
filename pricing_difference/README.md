# Project Overview

This dbt project processes Nigerian retail competitor pricing data from Snowflake, applying layered transformations:

**Raw Data (Snowflake) → Staging Models → Dimensions → Star Schema → Snapshots → Analytics**

The transformation follows dbt best practices:

- **Source definitions** with freshness checks
- **Staging layer** for cleaning and validation
- **Dimensional models** for analytics-ready structures
- **Snapshot strategy** for historical change tracking
- **Data quality tests** at every layer
- **Version control** for all SQL transformations

---

## Architecture

```
Snowflake RAW Schema
    ↓
COMPETITOR_PRICING (raw source table)
    ↓
[dbt Staging Models]
    ↓
stg_competitor_pricing (cleaned, typed, validated)
    ↓
    ┌──────────────────┬───────────────────┬──────────┐
    ↓                  ↓                   ↓          ↓
dim_product     dim_competitor       dim_date    (other dims)
    ↓                  ↓                   ↓
    └──────────────────┴───────────────────┴──────────┘
                       ↓
            fct_competitor_pricing
            (Star Schema Fact Table)
                       ↓
            snap_competitor_pricing
            (SCD Type 2 Snapshots)
                       ↓
                Power BI / Analytics
```

---

## Project Structure

```
pricing_difference/
│
├── models/
│   ├── staging/
│   │   ├── stg_competitor_pricing.sql
│   │   └── sources.yml
│   │
│   └── marts/
│       ├── dim_product.sql
│       ├── dim_competitor.sql
│       ├── dim_date.sql
│       └── fct_competitor_pricing.sql
│
├── snapshots/
│   └── snap_competitor_pricing.sql
│
├── tests/
│   └── (data quality tests)
│
├── dbt_project.yml
├── profiles.yml
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.8+
- Snowflake account with credentials
- dbt CLI

### Installation

#### 1. Clone Repository

```bash
git clone https://github.com/Chibutechie/competitive-pricing-etl.git
cd competitive-pricing-etl/pricing_difference
```

#### 2. Set Up Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
```

#### 3. Install dbt and Dependencies

```bash
pip install dbt-snowflake dbt-utils
```

#### 4. Configure Snowflake Connection

Create `~/.dbt/profiles.yml`:

```yaml
pricing_difference:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: [your-account-id]
      user: [your-username]
      password: [your-password]
      role: [your-role]
      database: PRICING_DIFF
      schema: dev
      threads: 1
      client_session_keep_alive: False
```

#### 5. Test Connection

```bash
dbt debug
```

Expected output: `✔ Connection test: [OK Connection ok]`

#### 6. Load Raw Data

Upload the competitor pricing dataset to Snowflake:

```sql
CREATE SCHEMA IF NOT EXISTS PRICING_DIFF.RAW;

-- Load data into PRICING_DIFF.RAW.COMPETITOR_PRICING
-- (Use Snowflake UI, COPY command, or Python connector)
```

---

## Running the Project

### Parse the Project

```bash
dbt parse
```

### Run All Models

```bash
dbt run
```

### Run Specific Models

```bash
# Run a single model
dbt run --select stg_competitor_pricing

# Run a model and all downstream dependencies
dbt run --select +fct_competitor_pricing+

# Run with full refresh (drop and recreate)
dbt run --full-refresh
```

### Run Data Tests

```bash
# Run all tests
dbt test

# Run tests on a specific model
dbt test --select stg_competitor_pricing

# Fail fast on first error
dbt test --fail-fast
```

### Create Snapshots

```bash
# Run all snapshots
dbt snapshot

# Run specific snapshot
dbt snapshot --select snap_competitor_pricing
```

### Generate Documentation

```bash
dbt docs generate
dbt docs serve  # View at localhost:8000
```

---

## Model Layers

### Layer 1: Source Definition

Sources are defined in `models/staging/sources.yml` and represent external data contracts:

```yaml
version: 2

sources:
  - name: pricing_difference
    database: PRICING_DIFF
    schema: raw
    loaded_at_field: loaded_at

    freshness:
      warn_after: { count: 24, period: hour }
      error_after: { count: 48, period: hour }

    tables:
      - name: competitor_pricing
        columns:
          - name: comparison_id
            data_tests:
              - unique
              - not_null
          - name: competitor_price
            data_tests:
              - not_null
```

**Features:**

- Freshness checks ensure data is current
- Source tests validate data quality at ingestion
- Referenceable as `{{ source('pricing_difference', 'competitor_pricing') }}`

### Layer 2: Staging Models

`models/staging/stg_competitor_pricing.sql` cleans and types raw data:

```sql
-- standardize columns, cast data types properly
with source as (
    select * from {{ source('pricing_difference', 'competitor_pricing') }}
),

final as (
    select
        "comparison_id"::varchar as comparison_id,
        "competitor_name"::varchar as competitor_name,
        "competitor_price_ngn"::numeric(10,2) as competitor_price,
        "date_checked"::date as date_checked,
        "day_of_week"::varchar as weekdays,
        "in_stock_competitor"::boolean as in_stock_competitor,
        "is_weekend"::boolean as is_weekend,
        "loaded_at"::timestamp as loaded_at,
        "month"::int as month_num,
        "month_name"::varchar as month_name,
        "our_price_ngn"::numeric(10,2) as our_price,
        "price_difference_ngn"::numeric(10,2) as price_difference,
           case
            when "price_difference_percent" > 1 then "price_difference_percent" / 100.0
            else "price_difference_percent"
        end as percent_difference,
        "price_position"::varchar as price_position,
        "product_name"::varchar as product_name,
        "week_number"::int as week_number,
        "year"::int as year

    from source
)

select * from final
```

**Materialization:** `view`

**Purpose:**

- Standardize column names (lowercase, underscores)
- Type cast to Snowflake types
- Handle nulls and duplicates
- **Recalculate derived metrics** from source values
- Single source of truth for cleaning logic

**Configuration** (in `dbt_project.yml`):

```yaml
models:
  pricing_difference:
    staging:
      +materialized: view
      +schema: staging
```

### Layer 3: Dimension Models

Dimensions are slowly-changing entities referenced by facts.

#### dim_product

```sql
-- models/marts/dimensions/dim_product.sql
with distinct_competitors as (
    select distinct product_name
    from {{ ref('stg_competitor_pricing') }}
    where product_name is not null
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['product_name']) }} as product_key,
        product_name,
        current_timestamp() as dbt_created_at,
        current_timestamp() as dbt_updated_at
    from distinct_competitors
)

select * from final
```

#### dim_competitor

```sql
-- models/marts/dimensions/dim_competitor.sql
with distinct_competitors as (
    select distinct competitor_name
    from {{ ref('stg_competitor_pricing') }}
    where competitor_name is not null
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['competitor_name']) }} as competitor_key,
        competitor_name,
        current_timestamp() as dbt_created_at,
        current_timestamp() as dbt_updated_at
    from distinct_competitors
)

select * from final
```

#### dim_date

```sql
-- models/marts/dimensions/dim_date.sql
with date_spine as (
    select dateadd(day, row_number() over (order by 1) - 1, '2024-01-01'::date) as date_day
    from table(generator(rowcount => 366))
),

final as (
    select
        date_day,
        year(date_day)::int                              as year,
        month(date_day)::int                             as month,
        day(date_day)::int                               as day,
        quarter(date_day)::int                           as quarter,
        to_varchar(date_day, 'MMMM')                     as month_name,
        to_varchar(date_day, 'MMM')                      as month_short,
        dayname(date_day)                                as day_name,
        dayofweek(date_day)::int                         as day_of_week,
        weekofyear(date_day)::int                        as week_of_year,
        case when dayofweek(date_day) in (0, 6)
             then true else false end                    as is_weekend,
        date_trunc('month', date_day)                    as first_day_of_month,
        last_day(date_day, 'month')                      as last_day_of_month,
        date_trunc('year', date_day)                     as first_day_of_year,
        date_trunc('quarter', date_day)                  as first_day_of_quarter,
        to_varchar(date_day, 'YYYYMMDD')::int            as date_key
    from date_spine
)

select * from final
```

**Materialization:** `table`

**Purpose:**

- Decouple dimensions from facts
- Enable reuse across multiple fact tables
- Support dimension versioning (with snapshots)

### Layer 4: Fact Model

`models/marts/fct_competitor_pricing.sql` - the central analytics table:

```sql
select
    s.comparison_id,
    p.product_key,
    c.competitor_key,
    s.product_name,
    s.competitor_name,
    s.competitor_price,
    s.our_price,
    s.price_difference,
    s.percent_difference,
    s.price_position,
    s.in_stock_competitor,
    s.date_checked,
    s.loaded_at

from {{ ref('stg_competitor_pricing') }} s

left join {{ ref('dim_product') }} p
    on s.product_name = p.product_name

left join {{ ref('dim_competitor') }} c
    on s.competitor_name = c.competitor_name
```

**Materialization:** `table`

**Grain:** One row per product-competitor-date combination

**Purpose:**

- Central table for analytics
- Denormalized for query performance
- Foreign keys to all dimensions

---

## Snapshots: Historical Tracking

`snapshots/snap_competitor_pricing.sql` implements SCD Type 2:

```sql
{% snapshot snap_competitor_pricing %}

  {{
    config(
      target_schema='snapshots',
      unique_key='comparison_id',
      strategy='timestamp',
      updated_at='loaded_at',
    )
  }}

  select
    "COMPARISON_ID" as comparison_id,
    "PRODUCT_NAME" as product_name,
    "COMPETITOR_NAME" as competitor_name,
    "COMPETITOR_PRICE"::number(10, 2) as competitor_price,
    "OUR_PRICE"::number(10, 2) as our_price,
    (("OUR_PRICE"::number - "COMPETITOR_PRICE"::number) / "COMPETITOR_PRICE"::number * 100)::float as percent_difference,
    "DATE_CHECKED"::date as date_checked,
    "AVAILABLE_COMPETITOR"::boolean as is_available,
    "LOADED_AT"::timestamp_ntz as loaded_at
  from {{ source('pricing_difference', 'competitor_pricing') }}

{% endsnapshot %}
```

**Configuration:**

- `strategy: timestamp` - tracks changes by timestamp column
- `updated_at: loaded_at` - looks for changes in `loaded_at` field
- `unique_key: comparison_id` - identifies records across time

**Automatic Columns Added by dbt:**

- `dbt_scd_id` - unique surrogate key per version
- `dbt_valid_from` - when this version became active
- `dbt_valid_to` - when it expired (NULL if current)
- `dbt_is_deleted` - tracks deletes

**Run snapshots:**

```bash
dbt snapshot
```

**Query historical data:**

```sql
-- Current records only
select * from snap_competitor_pricing
where dbt_valid_to is null;

-- Prices on a specific date
select * from snap_competitor_pricing
where date_checked <= '2024-08-15'
  and (dbt_valid_to >= '2024-08-15' or dbt_valid_to is null);

-- Track competitor price changes
select
    comparison_id,
    competitor_price,
    dbt_valid_from,
    dbt_valid_to
from snap_competitor_pricing
where competitor_name = 'Amazon'
order by dbt_valid_from;
```

---

## Data Quality Tests

Tests are defined in YAML and run with `dbt test`:

```yaml
# models/staging/sources.yml
version: 2

models:
  - name: stg_competitor_pricing
    tests:
      - dbt_expectations.expect_table_row_count_to_be_between:
          min_value: 1000
          max_value: 1000000
    columns:
      - name: comparison_id
        tests:
          - unique
          - not_null
      - name: competitor_price
        tests:
          - not_null
          - dbt_expectations.expect_column_values_to_be_greater_than:
              min_value: 0
```

**Test Types:**

| Test               | Purpose                       |
| ------------------ | ----------------------------- |
| `unique`           | No duplicate values in column |
| `not_null`         | Column has no nulls           |
| `accepted_values`  | Column values in whitelist    |
| `relationships`    | Foreign key validation        |
| `dbt_expectations` | Custom assertions             |

**Run tests:**

```bash
dbt test
dbt test --select stg_competitor_pricing
dbt test --fail-fast
```

---

## Configuration

### dbt_project.yml

```yaml
name: "pricing_difference"
version: "1.0.0"
profile: "pricing_difference"

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
snapshot-paths: ["snapshots"]
macro-paths: ["macros"]
seed-paths: ["seeds"]

models:
  pricing_difference:
    staging:
      +materialized: view
      +schema: staging

    marts:
      +materialized: table
      +schema: marts
```

### Materialization Strategy

- **Staging**: Views (lightweight, can be referenced directly)
- **Dimensions**: Tables (referenced frequently, small)
- **Facts**: Tables (central analytics table, larger)
- **Snapshots**: Tables (immutable historical records)

---

## Advanced Features

### Macros

Use `dbt_utils` for common patterns:

```sql
-- Generate surrogate key from multiple columns
{{ dbt_utils.surrogate_key(['field1', 'field2']) }}
```

### Testing Framework

Test any custom logic:

```sql
-- tests/assert_price_difference_calculation.sql
select count(*) as unexpected_records
from {{ ref('fct_competitor_pricing') }}
where competitor_price <= 0  -- Invalid prices
  or our_price <= 0
having count(*) > 0
```

Run with:

```bash
dbt test --select assert_price_difference_calculation
```

### Documentation

dbt auto-generates documentation from YAML:

```yaml
columns:
  - name: price_difference
    description: "Our price minus competitor price (negative = we're cheaper)"
    tests:
      - not_null
```

Generate and serve docs:

```bash
dbt docs generate
dbt docs serve  # localhost:8000
```

---

```bash
dbt docs generate
dbt docs serve  # View DAG
```

---

## Workflow

### Local Development

```bash
# Make a change to a model
vim models/marts/fct_competitor_pricing.sql

# Test locally
dbt run --select fct_competitor_pricing
dbt test --select fct_competitor_pricing

# Commit and push
git add models/
git commit -m "Add new column to fact table"
git push origin feature-branch
```

### Code Review

Before merging to main, verify:

- All tests pass: `dbt test`
- All models run: `dbt run`
- Documentation updated in YAML
- Lineage doesn't have circular dependencies

### Production Deployment

```bash
# Update production target in profiles.yml
dbt run --target prod

# Create snapshot for historical baseline
dbt snapshot --target prod
```

---

## Performance Considerations

### Query Optimization

```sql
-- Good: Filter early
select * from {{ ref('fct_competitor_pricing') }}
where date_day >= current_date - 30;

-- Avoid: Heavy aggregations in staging
select * from {{ ref('stg_competitor_pricing') }}
where <expensive_calculation>
```

### Materialization Choices

- **Views:** Low cost, slow queries (references raw data)
- **Tables:** High cost, fast queries (pre-computed)
- **Incremental:** Hybrid (append-only with upsert on key)

### Snowflake-Specific

```yaml
# models/marts/fct_competitor_pricing.sql
{{
  config(
    pre_hook="alter session set use_cached_result = false",
    post_hook="alter table {{ this }} cluster by (product_key, date_day)"
  )
}}
```

---

## Resources & References

- [dbt Documentation](https://docs.getdbt.com/)
- [dbt + Snowflake Docs](https://docs.getdbt.com/reference/warehouse-setups/snowflake-setup)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [Kimball Dimensional Modeling](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Slowly Changing Dimensions](https://en.wikipedia.org/wiki/Slowly_changing_dimension#Type_2)

---
