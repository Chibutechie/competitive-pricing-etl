"""Cleans, validates, and enriches the raw competitor pricing dataset."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "nigerian_retail_and_ecommerce_competitor_pricing_datasets.parquet"
)
PROCESSED_FILE = BASE_DIR / "data" / "processed" / "sales_clean.parquet"

OUTPUT_COLUMNS = [
    "comparison_id",
    "product_id",
    "product_name",
    "our_price_ngn",
    "competitor_name",
    "competitor_price_ngn",
    "price_difference_ngn",
    "price_difference_percent",
    "price_position",
    "date_checked",
    "year",
    "month",
    "month_name",
    "week_number",
    "day_of_week",
    "is_weekend",
    "in_stock_competitor",
    "loaded_at",
]


def transform() -> pd.DataFrame:
    """Transforms raw competitor pricing data into an analysis-ready dataset."""
    df = pd.read_parquet(RAW_FILE)

    df.columns = df.columns.str.lower()
    df = df.dropna().drop_duplicates()

    # Time-based feature engineering
    df["date_checked"] = pd.to_datetime(df["date_checked"])
    df["year"] = df["date_checked"].dt.year
    df["month"] = df["date_checked"].dt.month
    df["month_name"] = df["date_checked"].dt.strftime("%B")
    df["week_number"] = df["date_checked"].dt.isocalendar().week.astype(int)
    df["day_of_week"] = df["date_checked"].dt.strftime("%A")
    df["is_weekend"] = df["date_checked"].dt.dayofweek >= 5

    # Strip the time component now that the dt-based features above are derived
    df["date_checked"] = df["date_checked"].dt.date

    # Price difference: positive means we're cheaper than the competitor
    price_gap = df["competitor_price_ngn"] - df["our_price_ngn"]
    df["price_difference_ngn"] = price_gap.round(2)
    df["price_difference_percent"] = (price_gap / df["competitor_price_ngn"] * 100).round(2)

    df["price_position"] = np.where(
        df["our_price_ngn"] < df["competitor_price_ngn"],
        "Cheaper",
        np.where(df["our_price_ngn"] > df["competitor_price_ngn"], "Expensive", "Matched"),
    )

    df["loaded_at"] = datetime.now(timezone.utc)

    df = df[OUTPUT_COLUMNS]

    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED_FILE, index=False)
    print(f"Saved {len(df)} cleaned rows to {PROCESSED_FILE}")

    return df


if __name__ == "__main__":
    transform()
