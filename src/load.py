import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

connection_string = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USERNAME')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
)

engine = create_engine(connection_string)

BASE_DIR = Path(__file__).resolve().parent.parent

def load():
    df = pd.read_csv(BASE_DIR / "data" / "processed" / "sales_clean.csv")
    df.to_sql(                 
        name="competitor_pricing",
        con=engine,
        if_exists="replace",
        index=False
    )
    print("Successfully connected and loaded data")

load()                          