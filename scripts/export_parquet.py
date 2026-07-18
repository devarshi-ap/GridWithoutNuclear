import pandas as pd
from sqlalchemy import create_engine
import os

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER', 'airflow')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'airflow')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5433')}/"
    f"{os.getenv('POSTGRES_DB', 'ieso_grid')}"
)

engine = create_engine(DB_URL)

print("Exporting fact_counterfactual...")
df = pd.read_sql("SELECT * FROM staging_marts.fact_counterfactual", engine)
print(f"Loaded {len(df)} rows")

os.makedirs("data", exist_ok=True)
df.to_parquet("data/fact_counterfactual.parquet", index=False)
print(f"Saved to data/fact_counterfactual.parquet ({os.path.getsize('data/fact_counterfactual.parquet') / 1_000_000:.1f} MB)")