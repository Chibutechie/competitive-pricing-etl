import os
from pathlib import Path
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent.parent


def load() -> None:
    """
    Loads the transformed competitor pricing dataset into a PostgreSQL database.
    """

    # Load environment variables
    load_dotenv()

    # Collect and validate required DB env vars
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")

    missing = [k for k, v in (
        ("DB_USER", db_user),
        ("DB_PASSWORD", db_password),
        ("DB_HOST", db_host),
        ("DB_PORT", db_port),
        ("DB_NAME", db_name),
    ) if not v]

    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # URL-encode password in case it has special characters
    safe_password = quote_plus(db_password)

    # Build database connection string
    connection_string: str = (
        f"postgresql+psycopg2://{db_user}:{safe_password}@{db_host}:{db_port}/{db_name}"
    )

    # Create database engine and test connection
    try:
        engine: Engine = create_engine(connection_string)
        # try a quick connection to catch auth/connection issues early
        with engine.connect() as conn:
            pass
    except OperationalError as exc:
        print("Failed to connect to PostgreSQL database.")
        print("Please verify that Postgres is running and your DB credentials in .env are correct.")
        print(f"DB host={db_host} port={db_port} user={db_user} db={db_name}")
        print("Underlying error:", str(exc).splitlines()[0])
        sys.exit(1)

    # Read transformed data
    file_path: Path = BASE_DIR / "data" / "processed" / "sales_clean.parquet"
    if not file_path.exists():
        print(f"Transformed data file not found: {file_path}")
        sys.exit(1)

    df: pd.DataFrame = pd.read_parquet(file_path)

    # Load into PostgreSQL
    try:
        df.to_sql(
            name="competitor_pricing",
            schema="public",
            con=engine,
            if_exists="replace",
            index=False,
        )
    except Exception as exc:  # broad catch to provide a helpful message
        print("Failed to write DataFrame to the database:")
        print(str(exc))
        sys.exit(1)

    print(f"Loaded {len(df)} rows into competitor_pricing table.")


if __name__ == "__main__":
    load()