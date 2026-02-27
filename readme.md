# Building Competitive Pricing Intelligence ETL Pipeline with Python

In this repository are the scripts and methodologies used in extracting competitive pricing data, transforming it, and loading it into a PostgreSQL database for advanced competitive analysis.

---

## Table of Contents

- [Overview](#overview)
- [Project Objective](#project-objective)
- [Project Structure](#project-structure)
- [Architecture Flow](#architecture-flow)
- [How it works](#how-it-works)
- [Technologies](#technologies)
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

## How it works

### Extract 
- Collects the data from hugging face.
- Saves the data to `data/raw/competitor_pricing.csv`. 

### Transform
- Define the function 'transform'
- Drops empty rows and normalizes the column headers.
- Drop price_difference_ngn, price_difference_percent columns. 
- Create price_difference_ngn and percent_change. 
- create a new column for price_difference_percent. 
- Compare prices for position rank. 
- Reorder columns. 
- Move cleaned and transformed data to `data/processed/sales_clean.csv`. 

### Load
- Connect to PSQL using envrionment variables. 
- Load data into a database called `competitor_pricing`.

## Dataset

The dataset used for this project can be accessed [here](https://huggingface.co/datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets/viewer).

Schema from the source:

| Field                      | Type    | Example       |
| -------------------------- | ------- | ------------- |
| `comparison_id`            | String  | `COMP0000000` |
| `product_id`               | String  | `PRD80182`    |
| `product_name`             | String  | `Option`      |
| `our_price_ngn`            | Float   | `298984.47`   |
| `competitor_name`          | String  | `Spar`        |
| `competitor_price_ngn`     | Float   | `333817.21`   |
| `price_difference_ngn`     | Float   | -`45159.28`   |
| `price_difference_percent` | Float   | `8.85`        |
| `date_checked`             | String  | `2024-08-06`  |
| `in_stock_competitor`      | Boolean | `False`       |

---

## Technologies

The technologies used in this project are:

- [Python](https://www.python.org/) - Python is one of the top programming languages in the world, widely used in fields such as AI, machine learning, data science, data engineering, analytics, and web development.
- [PostgreSQL](https://www.bing.com/ck/a?!&&p=922469d6d00c5be8c140c58da82682967e4adf2fdd68fbf1499019ca4d0b69a5JmltdHM9MTc3MjE1MDQwMA&ptn=3&ver=2&hsh=4&fclid=388b4c21-b235-6a9f-197f-5a9cb3b46b14&psq=POStgresql&u=a1aHR0cHM6Ly93d3cucG9zdGdyZXNxbC5vcmcvZG93bmxvYWQv) - PostgreSQL, often simply called "Postgres," is an advanced, open-source object-relational database management system (ORDBMS).
- [Power BI](https://learn.microsoft.com/en-us/power-bi/fundamentals/power-bi-overview) - Power BI is Microsoft's business analytics platform that helps you turn data into actionable insights.
- [VS Code](https://code.visualstudio.com/) - IDE for programming.

---

## Reproducibility

This section will guide you on how to recreate this project

## 1) Pre-requisites
1. Setup a hugging face account.
2. Download VS Code or any IDE you are convienet with.
3) Download PG Admin with this [link](https://www.postgresql.org/download/)

## 2) Setting up your work environment
1) Create your virtual environment 

```bash
python -m venv myenv
``` 
