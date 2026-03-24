import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

BASE_DIR = Path(__file__).resolve().parent.parent


def load() -> None:
    """
    Loads the transformed competitor pricing dataset into a PostgreSQL database.
    """

    # Load environment variables
    load_dotenv()

    # Build database connection string
    connection_string: str = (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:"
        f"{os.getenv('DB_PORT')}/"
        f"{os.getenv('DB_NAME')}"
    )

    # Create database engine
    engine: Engine = create_engine(connection_string)

    # Read transformed data
    file_path: Path = BASE_DIR / "data" / "processed" / "sales_clean.csv"
    df: pd.DataFrame = pd.read_csv(file_path)

    # Load into PostgreSQL
    df.to_sql(
        name="competitor_pricing",
        schema="public",
        con=engine,
        if_exists="replace",
        index=False,
    )

    print(f"Loaded {len(df)} rows into competitor_pricing table.")
    

if __name__ == "__main__":
    load()