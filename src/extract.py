from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent


def extract() -> pd.DataFrame:
    """
    Extracts competitor pricing data from a remote parquet dataset,
    saves it as a CSV file locally, and returns the DataFrame. 
    """

    # Define raw data path
    raw_path: Path = BASE_DIR / "data" / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)

    # Read dataset from Hugging Face
    df: pd.DataFrame = pd.read_parquet(
        "hf://datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets"
        "/data/nigerian_retail_and_ecommerce_competitor_pricing_datasets.parquet"
    )

    print(f"Extracted {len(df)} rows")

    return df


if __name__ == "__main__":
    extract()