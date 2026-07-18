import logging
import time
import requests
import pandas as pd
from io import StringIO
from sqlalchemy import create_engine, text
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/ingest_price.log"),
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

BASE_URL = "https://reports-public.ieso.ca/public/PriceHOEPPredispOR/"
YEARS = range(2015, 2026)


def download_csv(year: int) -> str | None:
    url = f"{BASE_URL}PUB_PriceHOEPPredispOR_{year}.csv"
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
    df = pd.read_csv(
        StringIO(csv_text),
        skiprows=4,
        names=["date", "hour", "hoep", "h1_predispatch", "h2_predispatch",
               "h3_predispatch", "or_10_sync", "or_10_nonsync", "or_30"],
        usecols=["date", "hour", "hoep"]
    )

    df = df.dropna(subset=["date"])

    df["datetime"] = (
        pd.to_datetime(df["date"], format="%Y-%m-%d") +
        pd.to_timedelta(df["hour"].astype(int) - 1, unit="h")
    )

    # Remove thousands separators before converting to numeric
    df["hoep"] = df["hoep"].astype(str).str.replace(',', '', regex=False)
    df["hoep"] = pd.to_numeric(df["hoep"], errors="coerce")
    df["hoep"] = df["hoep"].where(df["hoep"].notna(), None)
    df["source_year"] = year

    return df[["datetime", "hoep", "source_year"]]


def weak_validate(df: pd.DataFrame, year: int) -> bool:
    # 2025 is a partial year ending April 30 (otherwise, stick to 24*29*12=8352)
    min_rows = 2800 if year == 2025 else 8352

    if len(df) < min_rows:
        logger.error(f"{year}: Expected at least {min_rows} rows, got {len(df)}")
        return False

    # HOEP is occasionally negative (rare but real — happens during oversupply)
    # but should never be below -200 or above 2000 (virtually impossible but not impossible)
    if df["hoep"].max() > 2000:
        logger.warning(f"{year}: HOEP exceeds $2000/MWh — something is wrong")

    if df["hoep"].min() < -200:
        logger.warning(f"{year}: HOEP below -$200/MWh — something is wrong")

    null_count = df["hoep"].isna().sum()
    if null_count > 0:
        logger.warning(f"{year}: {null_count} null HOEP values — will be stored as NULL")

    logger.info(
        f"{year}: Validation passed — {len(df)} rows, "
        f"HOEP avg ${df['hoep'].mean():.2f}/MWh, "
        f"min ${df['hoep'].min():.2f}, "
        f"max ${df['hoep'].max():.2f}"
    )
    return True


def load(df: pd.DataFrame, engine) -> int:
    insert_sql = text("""
        INSERT INTO raw.hoep_price (datetime, hoep, source_year)
        VALUES (:datetime, :hoep, :source_year)
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

    logger.info(f"{year}: Loading {len(df)} rows into raw.hoep_price")
    inserted = load(df, engine)
    logger.info(f"{year}: Done — {inserted} new rows inserted ({len(df) - inserted} skipped as duplicates)")


def main():
    logger.info("Starting price ingest")
    engine = create_engine(DB_URL)

    for year in YEARS:
        ingest_year(year, engine)
        time.sleep(2)

    logger.info("Price ingest complete")


if __name__ == "__main__":
    main()