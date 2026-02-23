import pandas as pd

url="hf://datasets/electricsheepafrica/nigerian_retail_and_ecommerce_competitor_pricing_datasets/data/nigerian_retail_and_ecommerce_competitor_pricing_datasets.parquet"

df = pd.read_parquet(url)

print(df.head())