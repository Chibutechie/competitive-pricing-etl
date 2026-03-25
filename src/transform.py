from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent


def transform() -> pd.DataFrame:
    """
    Transforms data by cleaning, validating, and enriching it
    with additional analytical features.
    """

    raw_file: Path = (
        BASE_DIR
        / "data"
        / "raw"
        / "nigerian_retail_and_ecommerce_competitor_pricing_datasets.parquet"
    )
    processed_file: Path = BASE_DIR / "data" / "processed" / "sales_clean.parquet"

    # Load raw data                                                       
    df: pd.DataFrame = pd.read_parquet(raw_file)

     # Clean data
    df = df.dropna().drop_duplicates()
    df.columns = df.columns.str.lower()

    # Drop existing price difference columns
    df = df.drop(columns=["price_difference_ngn", "price_difference_percent"], errors="ignore")

    # Recalculate price difference (NGN)
    df["price_difference_ngn"] = (
        df["our_price_ngn"] - df["competitor_price_ngn"]
    ).round(2)

    # Recalculate price difference (%)
    df["percent_change"] = (
        (df["our_price_ngn"] - df["competitor_price_ngn"]) / df["competitor_price_ngn"]
    ).round(2)

    # Time-based feature engineering
    df["date_checked"] = pd.to_datetime(df["date_checked"])
    df["year"] = df["date_checked"].dt.year
    df["month"] = df["date_checked"].dt.month
    df["month_name"] = df["date_checked"].dt.strftime("%B")
    df["week_number"] = df["date_checked"].dt.isocalendar().week.astype(int)
    df["day_of_week"] = df["date_checked"].dt.strftime("%A")
    df["is_weekend"] = df["date_checked"].dt.dayofweek >= 5

    # Price position classification
    df["price_position"] = np.where(
        df["our_price_ngn"] < df["competitor_price_ngn"],
        "Cheaper",
        np.where(
            df["our_price_ngn"] > df["competitor_price_ngn"],
            "Expensive",
            "Matched",
        ),
    )

    # Reorder columns
    cols = [
        "comparison_id",
        "product_id",
        "product_name",
        "our_price_ngn",
        "competitor_name",
        "competitor_price_ngn",
        "price_difference_ngn",
        "percent_change",
        "price_position",
        "date_checked",
        "year",
        "month",
        "month_name",
        "week_number",
        "day_of_week",
        "is_weekend",
        "in_stock_competitor",
    ]

    df = df[cols]
    
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(processed_file, index=False)

    print(f"Saved {len(df)} cleaned rows to {processed_file}")

    return df


if __name__ == "__main__":
    transform()