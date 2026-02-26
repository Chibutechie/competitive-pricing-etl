from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent

def transform():
    raw_file = BASE_DIR / "data" / "raw" / "retail_and_ecommerce_competitor_pricing.csv"
    processed_file = BASE_DIR / "data" / "processed" / "sales_clean.csv"

# drop empty rows and normalize column headers
    df = pd.read_csv(raw_file)
    df = df.dropna().drop_duplicates()
    df.columns = df.columns.str.lower()

# drop price_difference_ngn, price_difference_percent
    df = df.drop(columns=['price_difference_ngn', 'price_difference_percent'],inplace=False)

# new column for price difference using arithemetic operators
    df['price_difference_ngn'] = df['our_price_ngn'] - df['competitor_price_ngn']
    df['price_difference_ngn'] = df['price_difference_ngn'].round(2)

# new column for price difference percent
    df['percent_change'] = (df['our_price_ngn'] - df['competitor_price_ngn']) / df['competitor_price_ngn'] * 100
    df['percent_change'] = df['percent_change'].round(2)

# compare prices for price position
    
    df['price_position'] = np.where(df['our_price_ngn']  < df['competitor_price_ngn'], 'Cheaper', 'Expensive')
    df['price_position'] = np.where(df['our_price_ngn']  > df['competitor_price_ngn'], 'Expensive', 'Cheaper')
    df['price_position'] = np.where(df['our_price_ngn']  == df['competitor_price_ngn'], 'Matched', 'Unmatch')

# Reorder columns
    cols = [
        'comparison_id',
        'product_id',
        'product_name',
        'our_price_ngn',
        'competitor_name',
        'competitor_price_ngn',
        'price_difference_ngn',
        'percent_change',
        'price_position',
        'date_checked',
        'in_stock_competitor'
    ]
    df = df[cols]

    processed_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(processed_file, index=False)

    print(f"Saved cleaned data to {processed_file}")

if __name__ == "__main__":
    transform()