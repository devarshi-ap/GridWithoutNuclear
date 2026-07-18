import logging
import time
import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/ingest_demand.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER', 'airflow')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'airflow')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5433')}/"
    f"{os.getenv('POSTGRES_DB', 'ieso_grid')}"
)

BASE_URL = "https://reports-public.ieso.ca/public/Demand/"
YEARS = range(2015, 2026)


def download_csv(year: int) -> str | None:
    url = f"{BASE_URL}PUB_Demand_{year}.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    logger.info(f"Downloading {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"Downloaded {year} ({len(response.content) / 1_000:.0f} KB)")
        return response.text
    except requests.RequestException as e:
        logger.error(f"Failed for {year}: {e}")
        return None


def parse_csv(csv_text: str, year: int) -> pd.DataFrame:
    # Skip the 4 lines (3 comments + 1 tableheaders) at the top
    df = pd.read_csv(
        StringIO(csv_text),
        skiprows=4,
        names=["date", "hour", "market_demand_mw", "ontario_demand_mw"]
    )

    # Drop any rows where date is null (trailing empty lines)
    df = df.dropna(subset=["date"])

    # Convert date + hour to datetime (Hour 1 = 00:00, Hour 24 = 23:00)
    df["datetime"] = (
        pd.to_datetime(df["date"], format="%Y-%m-%d") +
        pd.to_timedelta(df["hour"].astype(int) - 1, unit="h")
    )

    df["source_year"] = year
    df["ontario_demand_mw"] = df["ontario_demand_mw"].astype(int)
    df["market_demand_mw"] = df["market_demand_mw"].astype(int)

    return df[["datetime", "ontario_demand_mw", "market_demand_mw", "source_year"]]


def weak_validate(df: pd.DataFrame, year: int) -> bool:
    # Expect at least 8352 rows (24 hours * 29 days [floor] * 12 months)
    if len(df) < 8352:
        logger.error(f"{year}: Expected atleast 8352 rows, got {len(df)}")
        return False

    if df["ontario_demand_mw"].any() <= 0:
        logger.error(f"{year}: ontario_demand_mw below (or equal) 0 — something is wrong")
        return False

    logger.info(
        f"{year}: Validation passed — {len(df)} rows, "
        f"ontario demand avg {df['ontario_demand_mw'].mean():.0f} MW, "
        f"min {df['ontario_demand_mw'].min()} MW, "
        f"max {df['ontario_demand_mw'].max()} MW"
    )
    return True


def load(df: pd.DataFrame, engine) -> int:
    insert_sql = text("""
        INSERT INTO raw.demand (
            datetime, ontario_demand_mw, market_demand_mw, source_year
        )
        VALUES (
            :datetime, :ontario_demand_mw, :market_demand_mw, :source_year
        )
        ON CONFLICT (datetime) DO NOTHING
    """)

    records = df.to_dict(orient="records")
    inserted = 0

    with engine.begin() as conn:
        for record in records:
            result = conn.execute(insert_sql, record)
            inserted += result.rowcount

    return inserted


def ingest_year(year: int, engine) -> None:
    csv_text = download_csv(year)
    if csv_text is None:
        return

    logger.info(f"{year}: Parsing CSV")
    df = parse_csv(csv_text, year)

    if not weak_validate(df, year):
        logger.error(f"{year}: Validation failed — skipping load")
        return

    logger.info(f"{year}: Loading {len(df)} rows into raw.demand")
    inserted = load(df, engine)
    logger.info(f"{year}: Done — {inserted} new rows inserted ({len(df) - inserted} skipped as duplicates)")


def main():
    logger.info("Starting demand ingest")
    engine = create_engine(DB_URL)

    for year in YEARS:
        ingest_year(year, engine)
        time.sleep(2)

    logger.info("Demand ingest complete")


if __name__ == "__main__":
    main()