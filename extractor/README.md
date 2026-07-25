# Scryfall extractor

Pulls the Scryfall `default_cards` bulk dataset and loads it into a
date-partitioned BigQuery table (`raw_scryfall_cards` by default), one
partition per day, as raw JSON. This is the bronze/raw layer: dbt models
downstream are expected to parse and flatten `payload`.

## Usage

```bash
uv run python extractor/scryfall.py
```

Requires `BQ_PROJECT` and `BQ_DATASET` env vars (see `.env.example`).

## Pipeline (`scryfall.py`)

1. **`get_download_uri`** — calls Scryfall's `bulk-data` API and returns the
   current download URL for the `default_cards` dataset (this URL rotates,
   so it can't be hardcoded).
2. **`download`** — streams that URL to `extractor/temp/*.json` in 1MB
   chunks, so the ~600MB response is never held fully in memory.
3. **`to_ndjson`** — converts the raw file to newline-delimited JSON, the
   format BigQuery's loader expects. Scryfall's bulk export happens to put
   one card object per line (`[`/`]` alone on their own lines), so this
   streams the conversion line-by-line rather than parsing the whole array
   into memory. Each output row is `{id, oracle_id, fetch_date, fetched_at,
   payload}`, where `payload` is the full card object.
4. **`previous_card_count`** — queries BigQuery for the row count of the
   prior day's partition (`None` on the very first run).
5. **`load_to_bigquery`** — loads the ndjson file into
   `raw_scryfall_cards$YYYYMMDD`, truncating and replacing just that
   partition. Reruns for the same day overwrite cleanly instead of
   duplicating.

`main` wires these together: download → convert → sanity-check the card
count against yesterday's (aborts if it dropped more than `MIN_ROW_COUNT_RATIO`,
5% by default, to avoid silently loading a partial/corrupted fetch) → load →
delete the temp files on success. On any failure it logs the traceback,
exits 1, and leaves the temp files in place for debugging.

## Design notes

- **Idempotent by partition**: `fetch_date$partition` + `WRITE_TRUNCATE`
  means re-running for today only ever replaces today's data.
- **Full snapshot, not incremental**: every run re-downloads and re-loads
  all ~116k cards. Simple and correct at this scale (~600MB/day); revisit
  if this needs to run much more frequently or the dataset grows an order
  of magnitude.
- **Raw JSON payload**: keeps the bronze layer schema-flexible — new
  Scryfall fields show up automatically without a migration, at the cost
  of downstream models needing to parse JSON.

## Attribution

Card data comes from [Scryfall's bulk data API](https://scryfall.com/docs/api/bulk-data).
This project is not affiliated with or endorsed by Scryfall.
