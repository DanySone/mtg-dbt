# mtg-dbt

Magic: The Gathering card data pipeline — extracts card data from Scryfall
into BigQuery as a raw, date-partitioned table.

## Structure

- [`extractor/`](extractor/) — pulls Scryfall's `default_cards` bulk export
  and loads it into BigQuery. See [extractor/README.md](extractor/README.md)
  for how the pipeline works.

## Setup

1. Python 3.12+, managed via [uv](https://docs.astral.sh/uv/): `uv sync`
2. Copy `.env.example` to `.env` and fill in your GCP project/dataset.
3. A GCP project with the BigQuery API enabled, and local credentials via
   `gcloud auth application-default login`.

## Running the extractor

```bash
uv run python extractor/scryfall.py
```
