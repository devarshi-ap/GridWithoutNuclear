"""
Ingestion follows a simple flow:
1. Build URL for each file (2015-2025) + Extract the XML (request)
2. Parse XMLTree (hierarchy noted in /sample_data) and store as Pandas Dataframe
3. Validate Dataframe (expected range of rows)
4. Run INSERT-INTO SQL (sqlalchemy engine) to load dataframe content into Postgresql DB

Log the whole thang.
"""
import logging
from sqlalchemy import create_engine, text
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os

# LOGGER
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/ingest_generation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# POSTGRESQL DB URL (with default values)
DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER', 'airflow')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'airflow')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5433')}/"
    f"{os.getenv('POSTGRES_DB', 'ieso_grid')}"
)

# Other Constants
BASE_URL = "https://reports-public.ieso.ca/public/GenOutputbyFuelHourly/"
NS = {"ns": "http://www.ieso.ca/schema"}
FUELS = ["NUCLEAR", "GAS", "HYDRO", "WIND", "SOLAR", "BIOFUEL"]
YEARS = range(2015, 2026) # scope relevant to project 


def download_xml(year: int) -> str | None:
    url = f"{BASE_URL}PUB_GenOutputbyFuelHourly_{year}.xml"
    # add a User-Agent header so the request looks like a browser (and doesn't get cause IESO's server to rate limit requests)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }


    logger.info(f"Downloading {url}")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        logger.info(f"Downloaded {year} ({len(response.content) / 1_000_000:.1f} MB)") # xml will only have english chars, so assumption: 1 char = 1 Byte
        return response.text
    except requests.RequestException as e:
        logger.error(f"Failed to download {year}: {e}")
        return None


def parse_xml(xml_text: str, year: int) -> pd.DataFrame:
    root = ET.fromstring(xml_text)
    body = root.find("ns:DocBody", NS)
    rows = []
    skipped = 0

    for daily in body.findall("ns:DailyData", NS):
        day_str = daily.find("ns:Day", NS).text

        for hourly in daily.findall("ns:HourlyData", NS):
            hour_elem = hourly.find("ns:Hour", NS)
            if hour_elem is None:
                skipped += 1
                continue

            hour = int(hour_elem.text)
            dt = datetime.strptime(day_str, "%Y-%m-%d") + timedelta(hours=hour - 1)
            row = {"datetime": dt, "source_year": year}

            for fuel_total in hourly.findall("ns:FuelTotal", NS):
                fuel_elem = fuel_total.find("ns:Fuel", NS)
                if fuel_elem is None:
                    continue

                fuel = fuel_elem.text
                if fuel not in FUELS:
                    continue

                # Split nested path into two finds instead of one
                energy_value = fuel_total.find("ns:EnergyValue", NS)
                if energy_value is None:
                    continue

                output_elem = energy_value.find("ns:Output", NS)
                if output_elem is None:
                    continue

                row[f"{fuel.lower()}_mw"] = int(output_elem.text)

            # Fill any missing fuels with 0
            for fuel in FUELS:
                col = f"{fuel.lower()}_mw"
                if col not in row:
                    row[col] = 0

            rows.append(row)

    if skipped > 0:
        logger.warning(f"{year}: Skipped {skipped} malformed hourly records")

    df = pd.DataFrame(rows)
    return df


def weak_validate(df: pd.DataFrame, year: int) -> bool:
    # Expect at least 8352 rows (24 hours * 29 days [floor] * 12 months)
    if len(df) < 8352:
        logger.error(f"{year}: Expected ~8352 rows, got {len(df)}")
        return False

    # Nuclear should always be positive
    if (df["nuclear_mw"] <= 0).any():
        logger.warning(f"{year}: Some nuclear_mw values are zero or negative")

    logger.info(f"{year}: Validation passed — {len(df)} rows, "
                f"nuclear avg {df['nuclear_mw'].mean():.0f} MW, "
                f"hydro avg {df['hydro_mw'].mean():.0f} MW, "
                f"gas avg {df['gas_mw'].mean():.0f} MW")
    return True


def load_data(df: pd.DataFrame, engine) -> int:
    insert_sql = text("""
        INSERT INTO raw.generation (
            datetime, nuclear_mw, gas_mw, hydro_mw,
            wind_mw, solar_mw, biofuel_mw, source_year
        )
        VALUES (
            :datetime, :nuclear_mw, :gas_mw, :hydro_mw,
            :wind_mw, :solar_mw, :biofuel_mw, :source_year
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
    xml_text = download_xml(year)
    if xml_text is None: return

    logger.info(f"{year}: Parsing XML")
    df = parse_xml(xml_text, year)

    # run weak validation
    if not weak_validate(df, year):
        logger.error(f"{year}: Validation failed — skipping load")
        return
    
    logger.info(f"{year}: Loading {len(df)} rows into raw.generation")
    inserted = load_data(df, engine)
    logger.info(f"{year}: Done — {inserted} new rows inserted ({len(df) - inserted} skipped as duplicates)")


def main():
    logger.info("Starting generation ingest")
    sql_engine = create_engine(DB_URL)

    for year in YEARS:
        ingest_year(year, sql_engine)
    
    logger.info("Generation ingest complete")

if __name__ == "__main__":
    main()