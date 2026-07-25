"""Extracteur Scryfall -> BigQuery (raw, partitionné par fetch_date)."""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("scryfall_extractor")

BULK_DATA_URL = "https://api.scryfall.com/bulk-data"
BULK_TYPE = "default_cards"
USER_AGENT = os.environ.get("SCRYFALL_USER_AGENT", "mtg-dbt-project/0.1 (github.com/DanySone/mtg-dbt)")
TEMP_DIR = Path(__file__).parent / "temp"

BQ_PROJECT = os.environ["BQ_PROJECT"]
BQ_DATASET = os.environ["BQ_DATASET"]
BQ_TABLE = os.environ.get("BQ_TABLE", "raw_scryfall_cards")
MIN_ROW_COUNT_RATIO = 0.95  # abort load if card_count drops below this fraction of the prior day

SCHEMA = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("oracle_id", "STRING"),
    bigquery.SchemaField("fetch_date", "DATE"),
    bigquery.SchemaField("fetched_at", "TIMESTAMP"),
    bigquery.SchemaField("payload", "JSON"),
]


def get_download_uri(bulk_type: str) -> tuple[str, str]:
    """Returns (download_uri, updated_at) for the matching bulk-data entry.
    updated_at is Scryfall's own snapshot timestamp, not our fetch time."""
    resp = requests.get(BULK_DATA_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    for entry in resp.json()["data"]:
        if entry["type"] == bulk_type:
            return entry["download_uri"], entry["updated_at"]
    raise ValueError(f"Aucune entrée de type '{bulk_type}' dans bulk-data")


def download(uri: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(uri, headers={"User-Agent": USER_AGENT}, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(1024 * 1024):
                f.write(chunk)
    return dest


def to_ndjson(source: Path, fetch_date: str, fetched_at: str) -> tuple[Path, int]:
    """Scryfall bulk files are one card object per line (`[`/`]` alone on
    their own lines), so this streams line-by-line instead of json.load-ing
    the whole array into memory. Verified 2026-07-25 against the live
    default_cards download (byte-range requests over the ~600MB file):
    line 1 is `[`, every card is one line ending in `},`, the last card has
    no trailing comma, and the final line is `]`."""
    dest = source.with_suffix(".ndjson")
    count = 0
    with open(source, encoding="utf-8") as f_in, open(dest, "w", encoding="utf-8") as f_out:
        for line in f_in:
            line = line.strip().rstrip(",")
            if line in ("[", "]", ""):
                continue
            card = json.loads(line)
            row = {
                "id": card.get("id"),
                "oracle_id": card.get("oracle_id"),
                "fetch_date": fetch_date,
                "fetched_at": fetched_at,
                "payload": card,
            }
            f_out.write(json.dumps(row) + "\n")
            count += 1
    return dest, count


def previous_card_count(client: bigquery.Client, fetch_date: str) -> int | None:
    """Row count of the most recent partition before fetch_date, or None if
    the table doesn't exist yet or has no earlier partition."""
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}`
        WHERE fetch_date = (
            SELECT MAX(fetch_date)
            FROM `{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}`
            WHERE fetch_date < @fetch_date
        )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("fetch_date", "DATE", fetch_date)]
    )
    try:
        row = next(iter(client.query(query, job_config=job_config).result()))
    except NotFound:
        return None
    return row["n"] or None


def load_to_bigquery(client: bigquery.Client, ndjson_path: Path, fetch_date: str) -> int:
    target = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}${fetch_date.replace('-', '')}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=SCHEMA,
        time_partitioning=bigquery.TimePartitioning(field="fetch_date"),
    )
    with open(ndjson_path, "rb") as f:
        job = client.load_table_from_file(f, target, job_config=job_config)
    job.result()
    return job.output_rows


def main() -> None:
    start = time.monotonic()
    now = datetime.now(timezone.utc)
    fetch_date, fetched_at = now.strftime("%Y-%m-%d"), now.isoformat()

    client = bigquery.Client(project=BQ_PROJECT)

    try:
        uri, updated_at = get_download_uri(BULK_TYPE)
        logger.info("Snapshot Scryfall (updated_at): %s", updated_at)

        raw_path = download(uri, TEMP_DIR / f"scryfall_{BULK_TYPE}_{fetch_date}.json")
        logger.info("Fichier téléchargé: %.1f MB", raw_path.stat().st_size / 1_000_000)

        ndjson_path, card_count = to_ndjson(raw_path, fetch_date, fetched_at)

        prev_count = previous_card_count(client, fetch_date)
        if prev_count and card_count < prev_count * MIN_ROW_COUNT_RATIO:
            raise ValueError(
                f"Nombre de cartes suspect: {card_count} contre {prev_count} la veille "
                f"(< {MIN_ROW_COUNT_RATIO:.0%}), partition non chargée"
            )

        loaded_rows = load_to_bigquery(client, ndjson_path, fetch_date)
    except Exception:
        logger.exception("Échec du run d'extraction Scryfall")
        sys.exit(1)
    else:
        raw_path.unlink(missing_ok=True)
        ndjson_path.unlink(missing_ok=True)

    logger.info(
        "%d cartes extraites, %d lignes chargées en %.1fs",
        card_count, loaded_rows, time.monotonic() - start,
    )


if __name__ == "__main__":
    main()