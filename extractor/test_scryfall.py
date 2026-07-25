import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("BQ_PROJECT", "test-project")
os.environ.setdefault("BQ_DATASET", "test_dataset")

from extractor import scryfall  # noqa: E402


class ToNdjsonTest(unittest.TestCase):
    def test_adds_fetch_date_and_fetched_at_to_every_row(self):
        cards = [
            {"id": "card-1", "oracle_id": "oracle-1", "name": "Forest"},
            {"id": "card-2", "oracle_id": "oracle-2", "name": "Island"},
        ]
        fetch_date, fetched_at = "2026-07-25", "2026-07-25T12:00:00+00:00"

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bulk.json"
            source.write_text(
                "[\n" + "\n".join(json.dumps(c) + "," for c in cards[:-1])
                + "\n" + json.dumps(cards[-1]) + "\n]\n"
            )

            dest, count = scryfall.to_ndjson(source, fetch_date, fetched_at)

            self.assertEqual(count, len(cards))
            rows = [json.loads(line) for line in dest.read_text().splitlines()]

        self.assertEqual(len(rows), len(cards))
        for card, row in zip(cards, rows):
            self.assertEqual(row["id"], card["id"])
            self.assertEqual(row["oracle_id"], card["oracle_id"])
            self.assertEqual(row["fetch_date"], fetch_date)
            self.assertEqual(row["fetched_at"], fetched_at)
            self.assertEqual(row["payload"], card)


class GetDownloadUriTest(unittest.TestCase):
    def _mock_bulk_data_response(self, entries):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json.return_value = {"data": entries}
        return resp

    def test_returns_uri_for_matching_bulk_type(self):
        entries = [
            {"type": "rulings", "download_uri": "https://example.com/rulings.json"},
            {"type": "default_cards", "download_uri": "https://example.com/default_cards.json"},
        ]
        with patch.object(scryfall.requests, "get", return_value=self._mock_bulk_data_response(entries)):
            uri = scryfall.get_download_uri("default_cards")

        self.assertEqual(uri, "https://example.com/default_cards.json")

    def test_raises_when_bulk_type_missing(self):
        entries = [{"type": "rulings", "download_uri": "https://example.com/rulings.json"}]
        with patch.object(scryfall.requests, "get", return_value=self._mock_bulk_data_response(entries)):
            with self.assertRaises(ValueError):
                scryfall.get_download_uri("default_cards")


if __name__ == "__main__":
    unittest.main()
