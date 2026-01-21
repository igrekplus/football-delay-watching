import json
import unittest

from src.clients.http_client import CachedResponse, HttpResponse


class TestHttpResponse(unittest.TestCase):
    def test_http_response_basic(self):
        content = b'{"status": "ok"}'
        headers = {"Content-Type": "application/json"}
        response = HttpResponse(
            status_code=200,
            content=content,
            headers=headers,
            url="http://example.com",
            reason="OK",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, '{"status": "ok"}')
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertTrue(response.ok)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(response.url, "http://example.com")
        self.assertEqual(response.reason, "OK")

    def test_http_response_404(self):
        response = HttpResponse(status_code=404, reason="Not Found")
        self.assertFalse(response.ok)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, "")
        self.assertEqual(response.json(), {})

    def test_cached_response(self):
        data = {"key": "value"}
        response = CachedResponse(json_data=data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.ok)
        self.assertTrue(response.from_cache)
        self.assertEqual(response.json(), data)
        self.assertEqual(json.loads(response.text), data)


if __name__ == "__main__":
    unittest.main()
