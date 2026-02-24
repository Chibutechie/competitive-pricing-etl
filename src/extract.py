from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

raw_path = BASE_DIR / "data" / "raw"
raw_path.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(
    "hf://datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets/data/nigerian_retail_and_ecommerce_competitor_pricing_datasets.parquet"
)

df.to_csv(raw_path / "retail_and_ecommerce_competitor_pricing.csv", index=False)

print(df.head())