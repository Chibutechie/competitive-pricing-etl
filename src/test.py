from pathlib import Path
import shutil
import pandas as pd
from huggingface_hub import hf_hub_download

BASE_DIR = Path(__file__).resolve().parent.parent
data_path = BASE_DIR / "data"
raw_path = data_path / "raw"

# Create directories if they don't exist
data_path.mkdir(parents=True, exist_ok=True)
raw_path.mkdir(parents=True, exist_ok=True)

PARQUET_FILENAME = "nigerian_retail_and_ecommerce_competitor_pricing_datasets.parquet"
PARQUET_FILE = raw_path / PARQUET_FILENAME

if PARQUET_FILE.exists():
    print("File exists, loading...")
else:
    print("File not found, downloading...")

    cached_path = hf_hub_download(
        repo_id="electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets",
        filename=f"data/{PARQUET_FILENAME}",
        repo_type="dataset",
        local_dir=data_path,
    )

    shutil.move(cached_path, PARQUET_FILE)
    print(f"Saved to: {PARQUET_FILE}")

df = pd.read_parquet(PARQUET_FILE)
print(df.head())