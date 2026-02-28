from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent


def transform():
    raw_file = BASE_DIR / "data" / "raw" / "competitor_pricing.csv"
    processed_file = BASE_DIR / "data" / "processed" / "sales_clean.csv"

    # drop empty rows and normalize column headers
    df = pd.read_csv(raw_file)
    df = df.dropna().drop_duplicates()
    df.columns = df.columns.str.lower()

    # drop source price_difference columns and recalculate from scratch
    df = df.drop(columns=["price_difference_ngn", "price_difference_percent"], inplace=False)

    # recalculate price difference (NGN)
    df["price_difference_ngn"] = (df["our_price_ngn"] - df["competitor_price_ngn"]).round(2)

    # recalculate price difference (%)
    df["percent_change"] = (
        (df["our_price_ngn"] - df["competitor_price_ngn"]) / df["competitor_price_ngn"] * 100
    ).round(2)

    # price position — all three cases covered
    df['price_position'] = np.where(df['our_price_ngn'] < df['competitor_price_ngn'],'Cheaper',
        np.where(df['our_price_ngn'] > df['competitor_price_ngn'],'Expensive','Matched') )
    
    # reorder columns
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
        "in_stock_competitor",
    ]

    df = df[cols]

    processed_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(processed_file, index=False)
    print(f"Saved {len(df)} cleaned rows to {processed_file}")

if __name__ == "__main__":
    transform()