"""Loads the transformed competitor pricing dataset into Snowflake."""

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "processed" / "sales_clean.parquet"
TABLE_NAME = "COMPETITOR_PRICING"

REQUIRED_ENV_VARS = [
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
]


def get_snowflake_config() -> dict:
    """Reads and validates Snowflake credentials from the environment."""
    load_dotenv()

    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        sys.exit(f"Missing required environment variables: {', '.join(missing)}")

    # e.g. "SNOWFLAKE_WAREHOUSE" -> "warehouse", matching connect() kwarg names
    config = {var.split("_", 1)[1].lower(): os.getenv(var) for var in REQUIRED_ENV_VARS}
    config["role"] = os.getenv("SNOWFLAKE_ROLE")  # optional
    return config


def load() -> None:
    if not DATA_FILE.exists():
        sys.exit(f"Transformed data file not found: {DATA_FILE}")

    df = pd.read_parquet(DATA_FILE)
    config = get_snowflake_config()

    try:
        with snowflake.connector.connect(**config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT CURRENT_VERSION()")
                print(f"Connected to Snowflake version: {cursor.fetchone()[0]}")

            # auto_create_table handles table creation, no manual DDL needed
            success, _, rows, _ = write_pandas(
                conn, df, TABLE_NAME, auto_create_table=True, overwrite=True
            )
    except Exception as exc:
        sys.exit(
            f"Failed to load data into Snowflake "
            f"(account={config['account']}, warehouse={config['warehouse']}, "
            f"database={config['database']}): {exc}"
        )

    if not success:
        sys.exit("Snowflake load failed.")

    print(f"Loaded {rows} rows into {TABLE_NAME} table.")


if __name__ == "__main__":
    load()