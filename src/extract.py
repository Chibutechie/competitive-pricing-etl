from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent


def extract():
    raw_path = BASE_DIR / "data" / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(
        "hf://datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets"
        "/data/nigerian_retail_and_ecommerce_competitor_pricing_datasets.parquet"
    )

    output = raw_path / "competitor_pricing.csv"
    df.to_csv(output, index=False)
    print(f"extracted {len(df)} rows")


if __name__ == "__main__":
    extract()