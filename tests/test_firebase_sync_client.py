import tempfile
import unittest
from pathlib import Path

from src.clients.firebase_sync_client import FirebaseSyncClient
from src.clients.http_client import HttpClient, HttpResponse


class FakeHttpClient(HttpClient):
    def __init__(self, response: HttpResponse):
        self.response = response
        self.requested_urls = []

    def get(self, url, headers=None, params=None, timeout=30):
        self.requested_urls.append(url)
        return self.response

    def post(self, url, headers=None, json=None, timeout=30):
        raise NotImplementedError


class TestFirebaseSyncClient(unittest.TestCase):
    def test_sync_reports_restores_from_shared_cache_before_downloading(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            local_reports_dir = temp_path / "public" / "reports"
            shared_reports_dir = temp_path / "shared"
            shared_reports_dir.mkdir(parents=True, exist_ok=True)

            cached_file = shared_reports_dir / "cached-report.html"
            cached_file.write_text("cached html", encoding="utf-8")

            http_client = FakeHttpClient(
                HttpResponse(status_code=200, content=b'{"reports_by_date":{}}')
            )
            client = FirebaseSyncClient(
                http_client=http_client,
                shared_reports_dir=shared_reports_dir,
            )
            client.fetch_manifest = lambda: {
                "reports_by_date": {
                    "2026-03-01": {"matches": [{"file": "cached-report.html"}]}
                }
            }

            downloaded = client.sync_reports(local_reports_dir)

            self.assertEqual(downloaded, 0)
            self.assertEqual(
                (local_reports_dir / "cached-report.html").read_text(encoding="utf-8"),
                "cached html",
            )
            self.assertEqual(http_client.requested_urls, [])

    def test_download_file_populates_shared_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            local_reports_dir = temp_path / "public" / "reports"
            shared_reports_dir = temp_path / "shared"
            response = HttpResponse(
                status_code=200,
                content=b"<html>remote</html>",
                headers={"Content-Type": "text/html"},
            )
            http_client = FakeHttpClient(response)
            client = FirebaseSyncClient(
                http_client=http_client,
                shared_reports_dir=shared_reports_dir,
            )

            ok = client.download_file(
                "reports/new-report.html",
                local_reports_dir / "new-report.html",
            )

            self.assertTrue(ok)
            self.assertEqual(
                (local_reports_dir / "new-report.html").read_text(encoding="utf-8"),
                "<html>remote</html>",
            )
            self.assertEqual(
                (shared_reports_dir / "new-report.html").read_text(encoding="utf-8"),
                "<html>remote</html>",
            )
            self.assertEqual(
                http_client.requested_urls,
                [
                    "https://football-delay-watching-a8830.web.app/reports/new-report.html"
                ],
            )


if __name__ == "__main__":
    unittest.main()
