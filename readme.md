# Building Competitive Pricing Intelligence ETL Pipeline with Python

In this repository are the scripts and methodologies used in extracting competitive pricing data, transforming it, and loading it into a PostgreSQL database for advanced competitive analysis.

---

## Table of Contents

- [Overview](#overview)
- [Project Objective](#project-objective)
- [Project Structure](#project-structure)
- [Architecture Flow](#architecture-flow)
- [Reproducibilty](#reproducibilty)
- [Dashboard](#dashboard)

---

## Overview

This project extracts, cleans, and moves the data from [Hugging Face](https://huggingface.co/datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets/viewer) to my database.

My inital aim for this project was only creating a simple pipeline that connects to the data source and dumps data into my database, but while I was doing this project I started asking more business questions, and this led me to explore other sides of the data. 

I moved from "how is the business performing?" to "how are we positioned in the market?", this made me create more columns that could answer this question and also led me to create a business intelligence report.

---

## Project Objective

- Extracts data using hugging face API. 
- Performs data validation and recalculates price difference
- Loads processed tables into PostgreSQL.
- Builds business intelligence report.

---

## Project Structure

```bash
competitive-pricing-etl/
│
├── src/
│   ├── extract.py
│   ├── transform.py
│   └── load.py
│
├── data/
│   ├── raw/
│   │    └── competitor_pricing.csv
│   └── processed/
│         └── sales_clean.csv  
├── requirements.txt
└── readme.md
```

---

## Architecture Flow



---

## Dataset

The dataset used for this project can be accessed [here](https://huggingface.co/datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets/viewer). 

Schema from the source:

| Field | Type | Example |
|-------|------|---------|
| `comparison_id` | String | `COMP0000000` |
| `product_id` | String | `PRD80182` |
| `product_name` | String | `Option` |
| `our_price_ngn` | Float | `298984.47` |
| `competitor_name` | String | `Spar` |
| `competitor_price_ngn` | Float | `333817.21` |
| `price_difference_ngn` | Float | `45159.28` |
| `price_difference_percent` | Float | `8.85` |
| `date_checked` | String | `2024-08-06` |
| `in_stock_competitor` | Boolean | `False` |