# Competitive Pricing Intelligence ETL Pipeline

> An end-to-end dbt-powered data pipeline that extracts Nigerian retail competitor pricing data, transforms it into a dimensional star schema in Snowflake, and enables competitive market analysis with historical tracking via snapshots.

---

## Table of Contents

- [Overview](#overview)
- [Project Objective](#project-objective)
- [Project Structure](#project-structure)
- [Architecture Flow](#architecture-flow)
- [Data Model](#data-model)
- [How It Works](#how-it-works)
- [Dataset Schema](#dataset-schema)
- [Technologies](#technologies)
- [Setup Instructions](#setup-instructions)
- [dbt Commands](#dbt-commands)
- [Dashboard](#dashboard)

---

## Overview

This pipeline extracts, transforms, and loads competitor pricing data from the [Hugging Face Nigerian Retail & E-commerce Competitor Pricing Dataset](https://huggingface.co/datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets/viewer) into Snowflake using dbt for orchestration and transformation.

The core architecture has evolved from a Python-based ETL to a dbt-centric approach with a dimensional star schema, enabling sophisticated competitive intelligence analysis and historical data tracking.

---

## Project Objective

- Extract competitor pricing data from source systems
- Build a scalable, version-controlled transformation layer with dbt
- Create a dimensional star schema for efficient querying
- Implement data quality tests
- Track pricing changes over time using dbt snapshots
- Enable competitive market positioning analysis

---

## Project Structure

```
pricing_difference/
│
├── models/
│   ├── staging/
│   │   ├── stg_competitor_pricing.sql        # Staging model with cleaning & type casting
│   │   ├── sources.yml                        # Source definitions & freshness checks
│   │   └── schema.yml                         # Staging model tests & documentation
│   │
│   ├── marts/
│   │   ├── schema.yml                         # Marts model tests & documentation
│   │   ├── dimensions/
│   │   │   ├── dim_product.sql                # Product dimension
│   │   │   ├── dim_competitor.sql             # Competitor dimension
│   │   │   └── dim_date.sql                   # Date dimension (calendar table)
│   │   └── facts/
│   │       └── fct_price.sql                  # Fact table (star schema)
│   │
│   └── exposures.yml                          # Downstream consumer documentation
│
├── snapshots/
│   └── snap_competitor_pricing.sql            # Snapshot for historical price tracking (SCD Type 2)
│
├── macros/
│   └── generate_schema.sql                    # Custom schema name macro
│
├── tests/                                     # Singular tests (generic tests in schema.yml)
├── analyses/                                  # Ad-hoc analytical queries
├── seeds/                                     # Reference data CSV files
│
├── dbt_packages/
│   └── dbt_utils/                             # dbt utility package (v1.4.0)
│
├── packages.yml                               # dbt package dependencies
├── package-lock.yml                           # Package dependency lock file
├── dbt_project.yml                            # dbt project configuration
├── README.md
└── .gitignore
```

---

## Architecture Flow

```
Raw Data (Snowflake)
        ↓
    [sources.yml]
        ↓
[stg_competitor_pricing] ← Staging Layer (cleaning, casting)
        ↓
    ┌───┴──────────┬─────────────┐
    ↓              ↓              ↓
[dim_product] [dim_competitor] [dim_date] ← Dimensions
    ↓              ↓              ↓
    └───────┬──────┴──────────────┘
            ↓
[fct_price] ← Fact Table (Star Schema)
            ↓
[snap_competitor_pricing] ← Historical Snapshot (SCD Type 2)
            ↓
Power BI / Analytics Tools
```

### dbt Lineage Graph

![Lineage Graph](image/Screenshot%202026-06-29%20024944.png)

---

## Data Model

### Star Schema Structure

<img width="887" height="356" alt="image" src="https://github.com/user-attachments/assets/79635952-6c8c-42f2-b1d7-e631c6c0a963" />

#### **Dimensions**

**dim_product**

- `product_key` (PK)
- `product_name`
- `dbt_created_at`, `dbt_updated_at`

**dim_competitor**

- `competitor_key` (PK)
- `competitor_name`
- `dbt_created_at`, `dbt_updated_at`

**dim_date**

- `date_day` (PK)
- `day_of_week`, `day_of_week_num`, `day_of_month`
- `week_number`, `month_num`, `month_name`, `quarter`, `year_num`
- `is_weekend`, `season`
- `year_month` (for aggregations)
- `dbt_created_at`, `dbt_updated_at`

#### **Facts**

**fct_price**

- `comparison_id` (PK)
- `product_key` (FK → dim_product)
- `competitor_key` (FK → dim_competitor)
- `our_price`, `competitor_price`
- `price_difference`, `percent_difference`
- `price_position`
- `in_stock_competitor`
- `date_checked`, `loaded_at`

#### **Snapshots**

**snap_competitor_pricing** (Type 2 SCD)

- Original columns from staging
- `dbt_scd_id` (unique surrogate key)
- `dbt_valid_from` (when row became valid)
- `dbt_valid_to` (when row became invalid, NULL if current)
- `dbt_is_deleted` (tracks deleted records)

---

## How It Works

### 1. **Source Definition** (`sources.yml`)

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
        data_tests:
          - unique: [comparison_id]
          - not_null: [comparison_id]
```

### 2. **Staging** (`stg_competitor_pricing.sql`)

- Pulls from source tables
- Normalizes data types (VARCHAR, NUMBER, DATE, TIMESTAMP_NTZ, BOOLEAN)
- Removes nulls and duplicates
- Casts columns for downstream consistency
- Creates a clean, conformed dataset

### 3. **Dimensions** (`dim_*.sql`)

- **dim_product**: Unique products with row numbering
- **dim_competitor**: Unique competitors
- **dim_date**: Calendar table (2024 full year with enriched date attributes)

All dimensions include `dbt_created_at` and `dbt_updated_at` for audit trail.

### 4. **Fact Table** (`fct_competitor_pricing.sql`)

- Joins staging data with all three dimensions via left joins
- Creates surrogate key using `dbt_utils.surrogate_key()`
- Stores denormalized facts for efficient querying
- Materialized as a table for performance

### 5. **Snapshots** (`snap_competitor_pricing.sql`)

- Uses `strategy: timestamp` with `updated_at: loaded_at`
- Tracks every price change and records when it occurred
- Enables historical analysis: _"What was the competitor's price on X date?"_
- Implements Slowly Changing Dimension (SCD) Type 2

### 6. **Data Tests**

- Uniqueness tests on comparison_id and product_key
- Not-null tests on critical columns
- Custom expression tests (price > 0, valid date ranges)
- All tests run with `dbt test`

---

## Dataset Schema

Source: [Hugging Face Dataset](https://huggingface.co/datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets/viewer)

| Column                  | Type          | Loaded via |
| ----------------------- | ------------- | ---------- |
| comparison_id           | VARCHAR       | Source     |
| product_name            | VARCHAR       | Source     |
| competitor_name         | VARCHAR       | Source     |
| our_price               | NUMBER(10,2)  | Staging    |
| competitor_price        | NUMBER(10,2)  | Staging    |
| price_difference        | NUMBER(10,2)  | Staging    |
| percent_difference      | FLOAT         | Staging    |
| price_position          | VARCHAR       | Source     |
| date_checked            | DATE          | Staging    |
| is_available_competitor | BOOLEAN       | Source     |
| loaded_at               | TIMESTAMP_NTZ | Source     |

---

## Technologies

| Tool                                                                                    | Purpose                             |
| --------------------------------------------------------------------------------------- | ----------------------------------- |
| [dbt](https://www.getdbt.com/)                                                          | Data transformation & orchestration |
| [Snowflake](https://www.snowflake.com/)                                                 | Cloud data warehouse                |
| [Snowflake Adapter](https://docs.getdbt.com/reference/warehouse-setups/snowflake-setup) | dbt ↔ Snowflake integration         |
| [dbt Power User](https://www.getdbt.com/product/ide/)                                   | VS Code IDE for dbt                 |
| [Power BI](https://learn.microsoft.com/en-us/power-bi/)                                 | Business intelligence dashboard     |
| [VS Code](https://code.visualstudio.com/)                                               | Development environment             |
| [Python 3.13](https://www.python.org/)                                                  | dbt runtime & macro support         |

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Chibutechie/competitive-pricing-etl.git
cd competitive-pricing-etl/pricing_difference
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dbt & Snowflake Adapter

```bash
pip install dbt-snowflake
pip install dbt-utils
```

### 4. Configure Snowflake Connection

Create `profiles.yml` in `~/.dbt/`:

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

### 5. Test Connection

```bash
dbt debug
```

Expected output:

```
Connection test: [OK Connection ok]
```

### 6. Load Data into Snowflake

```sql
-- Load your raw data into PRICING_DIFF.RAW.COMPETITOR_PRICING
-- You can use Snowflake's COPY command, Python connector, or UI
```

---

## dbt Commands

### Parse Project

```bash
dbt parse
```

### Run Transformations

```bash
# Run all models
dbt run

# Run specific model
dbt run --select stg_competitor_pricing

# Run model and its downstream dependents
dbt run --select +dim_product+
```

### Run Data Tests

```bash
# Run all tests
dbt test

# Run tests on specific model
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
dbt docs serve
```

Opens interactive documentation at `localhost:8000`

### Clean Up

```bash
# Remove target/ and dbt_packages/
dbt clean

# Full refresh (drop and recreate tables)
dbt run --full-refresh
```

### Partial Parse (Recommended)

```bash
# Faster local development - only parses changed files
dbt --no-partial-parse run
```

---

## Project Configuration

### `dbt_project.yml`

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

- **Staging**: Views (lightweight, can be queried directly)
- **Dimensions**: Tables (small, frequently joined)
- **Facts**: Tables (larger, aggregation target)
- **Snapshots**: Tables (immutable historical records)

---

## Data Quality Tests

### Built-in Tests

```yaml
# In sources.yml or model blocks
tests:
  - unique: [comparison_id]
  - not_null: [comparison_id, product_name]
  - dbt_expectations.expect_table_row_count_to_be_between:
      min_value: 1000
      max_value: 1000000
```

### Custom SQL Tests

Create in `tests/`:

```sql
select count(*) as unexpected_records
from {{ ref('fct_competitor_pricing') }}
where competitor_price <= 0
having count(*) > 0
```

### Run Tests

```bash
dbt test --fail-fast
```

---

## Snapshot Strategy

### Why Snapshots?

- **Track pricing changes** over time (e.g., competitor price drops)
- **Answer historical questions**: _"What was the price on Aug 15?"_
- **Identify trends**: _"Which competitors consistently undercut us?"_
- **Audit trail**: See when data changed and why

### How to Query Snapshots

```sql
-- Get current prices
select * from snap_competitor_pricing
where dbt_valid_to is null;

-- Get price on specific date
select * from snap_competitor_pricing
where date_checked <= '2024-08-15'
  and (dbt_valid_to >= '2024-08-15' or dbt_valid_to is null);

-- Track price changes for one competitor
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

## Dashboard

The Power BI dashboard connects directly to Snowflake and visualizes:

- **Competitive positioning** by product and competitor
- **Price trends** over time
- **Market share analysis** based on pricing
- **Availability tracking** for competitors
- **Historical price changes** from snapshots

### Power BI Setup

1. Open Power BI Desktop → **Get Data** → **Snowflake**
2. Enter your Snowflake account, username, password
3. Select `PRICING_DIFF` database and `MARTS` schema
4. Import `dim_product`, `dim_competitor`, `dim_date`, `fct_competitor_pricing`
5. Create relationships:
   - `fct_competitor_pricing.product_key` → `dim_product.product_key`
   - `fct_competitor_pricing.competitor_key` → `dim_competitor.competitor_key`
   - `fct_competitor_pricing.date_day` → `dim_date.date_day`
6. Build visualizations using the star schema

---

## Deployment

### Development → Production

```bash
# Develop & test locally
dbt run --select stg_competitor_pricing
dbt test

# Push to Git (version control)
git add .
git commit -m "Add dim_date dimension"
git push origin main

# Deploy to production environment
dbt run --target prod --select state:modified+
```

### Production Profile (in `profiles.yml`)

```yaml
outputs:
  prod:
    type: snowflake
    account: [prod-account]
    user: [prod-user]
    password: [prod-password]
    role: [prod-role]
    database: PRICING_DIFF_PROD
    schema: analytics
    threads: 4
```

---

## Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [Snowflake dbt Adapter](https://docs.getdbt.com/reference/warehouse-setups/snowflake-setup)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [Dimensional Modeling](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)

---
