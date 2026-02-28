import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent


def load():
    load_dotenv()

    connection_string = (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER')}:"      
        f"{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:"
        f"{os.getenv('DB_PORT')}/"
        f"{os.getenv('DB_NAME')}"
    )
    engine = create_engine(connection_string)

    df = pd.read_csv(BASE_DIR / "data" / "processed" / "sales_clean.csv")
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