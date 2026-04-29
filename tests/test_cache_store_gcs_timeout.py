import unittest
from unittest.mock import MagicMock, patch

from src.clients import cache_store
from src.clients.cache_store import GcsCacheStore


class TestGcsCacheStoreTimeout(unittest.TestCase):
    def setUp(self):
        cache_store._shared_gcs_client = None
        cache_store._shared_gcs_buckets = {}

    def tearDown(self):
        cache_store._shared_gcs_client = None
        cache_store._shared_gcs_buckets = {}

    def _store_with_blob(self, blob):
        bucket = MagicMock()
        bucket.blob.return_value = blob
        client = MagicMock()
        client.bucket.return_value = bucket

        storage_module = MagicMock()
        storage_module.Client.return_value = client

        return GcsCacheStore("test-bucket"), storage_module

    def test_read_passes_timeout_to_gcs_operations(self):
        blob = MagicMock()
        blob.exists.return_value = True
        blob.download_as_text.return_value = '{"ok": true}'
        store, storage_module = self._store_with_blob(blob)

        with patch.dict("sys.modules", {"google.cloud.storage": storage_module}):
            self.assertEqual(store.read("fixtures/id_1540841.json"), {"ok": True})

        blob.exists.assert_called_once_with(
            timeout=cache_store.GCS_OPERATION_TIMEOUT_SECONDS
        )
        blob.download_as_text.assert_called_once_with(
            timeout=cache_store.GCS_OPERATION_TIMEOUT_SECONDS
        )

    def test_write_passes_timeout_to_gcs_operation(self):
        blob = MagicMock()
        store, storage_module = self._store_with_blob(blob)

        with patch.dict("sys.modules", {"google.cloud.storage": storage_module}):
            store.write("fixtures/id_1540841.json", {"ok": True})

        self.assertEqual(
            blob.upload_from_string.call_args.kwargs["timeout"],
            cache_store.GCS_OPERATION_TIMEOUT_SECONDS,
        )


if __name__ == "__main__":
    unittest.main()
